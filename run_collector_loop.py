import subprocess
import sys
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


def next_collect_schedule():
    """
    다음 수집 대상 슬롯과 실제 실행 예정 시각을 함께 계산합니다.

    핵심:
    - sampled_at에는 실행 시각이 아니라 수집 대상 10분 슬롯을 저장합니다.
    - 실행이 몇 초 늦어져도 같은 슬롯으로 저장되어 직전 대비 계산이 흔들리지 않습니다.
    """
    now = datetime.now(KST)

    slot = current_10min_slot(now)
    target = slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)

    if now >= target:
        slot = next_10min_slot(slot)
        target = slot + timedelta(seconds=COLLECTION_DELAY_SECONDS)

    return slot, target


def sleep_until(target):
    while True:
        now = datetime.now(KST)
        remaining = (target - now).total_seconds()

        if remaining <= 0:
            break

        time.sleep(min(remaining, 30))


def run_collect(sampled_at):
    started_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    sampled_at_text = sampled_at.strftime("%Y-%m-%dT%H:%M:%S")
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


def main():
    print("[INFO] 네이버 조회수 수집 루프 시작", flush=True)
    print("[INFO] 수집 방식: 10분 슬롯 시작 후 지연 수집", flush=True)
    print(f"[INFO] COLLECTION_DELAY_SECONDS={COLLECTION_DELAY_SECONDS}", flush=True)
    print(f"[INFO] 프로젝트 경로: {PROJECT_DIR}", flush=True)

    while True:
        slot, target = next_collect_schedule()
        print(
            f"[WAIT] 다음 수집 대상 슬롯: {slot.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"실행 예정 시각: {target.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True,
        )

        sleep_until(target)
        run_collect(slot)


if __name__ == "__main__":
    main()
