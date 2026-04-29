import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

# 네이버 API 실제 조회수 반영 지연 대응값
# 관찰 결과: 각 10분 슬롯 시작 후 약 8~9분 뒤 조회수 값이 갱신됨
# 550초 = 9분 10초
COLLECTION_DELAY_SECONDS = 550

PROJECT_DIR = Path(__file__).resolve().parent


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


def next_collect_time():
    """
    다음 수집 예정 시각을 계산합니다.

    핵심:
    - 각 10분 슬롯 시작 후 COLLECTION_DELAY_SECONDS 초 뒤에 수집합니다.
    - 예: 17:40 슬롯은 17:49:10에 수집
    - 만약 현재 시간이 아직 17:49:10 전이면 17:49:10을 목표로 합니다.
    - 이미 지났으면 다음 슬롯의 수집 시각으로 넘어갑니다.
    """
    now = datetime.now(KST)

    slot = current_10min_slot(now)
    target = slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)

    if now < target:
        return target

    next_slot = next_10min_slot(slot)
    return next_slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)


def sleep_until(target):
    while True:
        now = datetime.now(KST)
        remaining = (target - now).total_seconds()

        if remaining <= 0:
            break

        time.sleep(min(remaining, 30))


def run_collect():
    started_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[START] collect.py 실행: {started_at}", flush=True)

    result = subprocess.run(
        ["python3", "collect.py"],
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


def main():
    print("[INFO] 네이버 조회수 수집 루프 시작", flush=True)
    print("[INFO] 수집 방식: 10분 슬롯 시작 후 지연 수집", flush=True)
    print(f"[INFO] COLLECTION_DELAY_SECONDS={COLLECTION_DELAY_SECONDS}", flush=True)
    print(f"[INFO] 프로젝트 경로: {PROJECT_DIR}", flush=True)

    while True:
        target = next_collect_time()
        print(
            f"[WAIT] 다음 수집 예정 시각: {target.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True,
        )

        sleep_until(target)
        run_collect()


if __name__ == "__main__":
    main()
