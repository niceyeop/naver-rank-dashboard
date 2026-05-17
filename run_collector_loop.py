import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")

# 네이버 API 실제 조회수 반영 지연 대응값
# 관찰 결과: 각 10분 슬롯 시작 후 약 8~9분 뒤 조회수 값이 갱신됨
# 550초 = 9분 10초
COLLECTION_DELAY_SECONDS = 550
FAILED_RETRY_DELAY_SECONDS = 60

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", "naver_rank.db"))
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_DIR / DB_PATH

DB_TIMEOUT_SECONDS = 30
DB_BUSY_TIMEOUT_MS = 30_000


def current_10min_slot(now):
    """
    현재 시각을 10분 단위 슬롯 시작 시각으로 내립니다.
    예:
    17:42:31 -> 17:40:00
    17:59:10 -> 17:50:00
    """
    minute = (now.minute // 10) * 10
    return now.replace(minute=minute, second=0, microsecond=0)


def next_10min_slot(slot):
    """
    다음 10분 슬롯 시작 시각을 반환합니다.
    예:
    17:40:00 -> 17:50:00
    17:50:00 -> 18:00:00
    """
    return slot + timedelta(minutes=10)


def format_sampled_at(slot):
    return slot.strftime("%Y-%m-%dT%H:%M:%S")


def connect_db_readonly():
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)
    conn.execute(f"PRAGMA busy_timeout = {DB_BUSY_TIMEOUT_MS}")
    return conn


def sampled_at_exists(slot):
    if not DB_PATH.exists():
        return False

    sampled_at = format_sampled_at(slot)

    try:
        conn = connect_db_readonly()
        cur = conn.execute(
            """
            SELECT 1
            FROM naver_pv_rank_snapshots
            WHERE sampled_at = ?
            LIMIT 1
            """,
            (sampled_at,)
        )
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except sqlite3.Error as e:
        print(f"[WARN] 기존 수집 여부 확인 실패. 미수집으로 간주합니다: {e}", flush=True)
        return False


def next_collect_schedule():
    """
    다음 수집 대상 슬롯과 실제 실행 예정 시각을 함께 계산합니다.

    핵심:
    - sampled_at에는 실행 시각이 아니라 수집 대상 10분 슬롯을 저장합니다.
    - 서비스 재시작이 수집 지연 시각 이후에 일어나도, 아직 저장되지 않은 현재 슬롯은 즉시 수집합니다.
    """
    now = datetime.now(KST)

    slot = current_10min_slot(now)
    target = slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)

    if now >= target:
        if not sampled_at_exists(slot):
            return slot, now, True

        slot = next_10min_slot(slot)
        target = slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)

    return slot, target, False


def sleep_until(target):
    while True:
        now = datetime.now(KST)
        remaining = (target - now).total_seconds()

        if remaining <= 0:
            break

        time.sleep(min(remaining, 30))


def run_collect(sampled_at):
    started_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    sampled_at_text = format_sampled_at(sampled_at)
    print(f"[START] collect.py 실행: {started_at}, sampled_at={sampled_at_text}", flush=True)

    result = subprocess.run(
        [sys.executable, "collect.py", "--sampled-at", sampled_at_text],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout, flush=True)

    if result.stderr:
        print(result.stderr, flush=True)

    ended_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[END] collect.py 종료: {ended_at}, returncode={result.returncode}",
        flush=True,
    )

    if result.returncode != 0:
        print("[WARN] collect.py가 비정상 종료되었습니다.", flush=True)
        return False

    return True


def main():
    print("[INFO] 네이버 조회수 수집 루프 시작", flush=True)
    print("[INFO] 수집 방식: 10분 슬롯 시작 후 지연 수집", flush=True)
    print(f"[INFO] COLLECTION_DELAY_SECONDS={COLLECTION_DELAY_SECONDS}", flush=True)
    print(f"[INFO] 프로젝트 경로: {PROJECT_DIR}", flush=True)
    print(f"[INFO] DB 경로: {DB_PATH}", flush=True)

    while True:
        slot, target, run_immediately = next_collect_schedule()

        if run_immediately:
            print(
                f"[CATCHUP] 미수집 슬롯 즉시 수집: {slot.strftime('%Y-%m-%d %H:%M:%S')}",
                flush=True,
            )
        else:
            print(
                f"[WAIT] 다음 수집 대상 슬롯: {slot.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"실행 예정 시각: {target.strftime('%Y-%m-%d %H:%M:%S')}",
                flush=True,
            )

        sleep_until(target)
        succeeded = run_collect(slot)

        if not succeeded:
            time.sleep(FAILED_RETRY_DELAY_SECONDS)


if __name__ == "__main__":
    main()
