import time
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def next_10min_boundary():
    now = datetime.now(KST)

    # 다음 10분 단위 시각 계산
    next_minute = ((now.minute // 10) + 1) * 10

    if next_minute >= 60:
        next_time = now.replace(
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(hours=1)
    else:
        next_time = now.replace(
            minute=next_minute,
            second=0,
            microsecond=0
        )

    return next_time


def sleep_until(target_time):
    now = datetime.now(KST)
    seconds = (target_time - now).total_seconds()

    if seconds > 0:
        print(f"[WAIT] 다음 수집 시각: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[WAIT] {int(seconds)}초 대기합니다.")
        time.sleep(seconds)


def run_once(scheduled_time):
    print("=" * 80)
    print(f"[START] scheduled_at={scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[NOW] {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")

    result = subprocess.run(
        [sys.executable, "collect.py"],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("[ERROR]")
        print(result.stderr)

    print(f"[END] {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    print("10분 단위 정각에 네이버 실시간 조회수 순위를 수집합니다.")
    print("예: 00분, 10분, 20분, 30분, 40분, 50분")
    print("종료하려면 Ctrl + C를 누르세요.")

    while True:
        scheduled_time = next_10min_boundary()
        sleep_until(scheduled_time)
        run_once(scheduled_time)


if __name__ == "__main__":
    main()
