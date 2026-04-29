import time
import csv
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

import collect

KST = ZoneInfo("Asia/Seoul")

# 30초 간격이면 70분 동안 약 140회 호출합니다.
INTERVAL_SECONDS = 30
DURATION_MINUTES = 70

OUTPUT_CSV = "naver_refresh_probe.csv"


def now_kst():
    return datetime.now(KST)


def now_str():
    return now_kst().strftime("%Y-%m-%d %H:%M:%S")


def to_int(value):
    if value is None:
        return 0

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if value == "":
            return 0
        try:
            return int(float(value))
        except ValueError:
            return 0

    return 0


def get_value(row, keys, default=None):
    for key in keys:
        if isinstance(row, dict) and key in row:
            return row[key]
    return default


def get_cv(row):
    return to_int(
        get_value(
            row,
            [
                "cv",
                "viewCount",
                "total_manager",
                "count",
                "views",
            ],
            0,
        )
    )


def get_uri(row):
    return str(
        get_value(
            row,
            [
                "uri",
                "url",
                "articleUrl",
                "link",
            ],
            "",
        )
    )


def get_title(row):
    return str(
        get_value(
            row,
            [
                "title",
                "articleTitle",
                "subject",
            ],
            "",
        )
    )


def make_signature(rows):
    """
    pvRank 전체 상태를 fingerprint로 만듭니다.
    조회수나 순위/기사 구성이 바뀌면 signature가 바뀝니다.
    """
    normalized = []

    for idx, row in enumerate(rows):
        uri = get_uri(row)
        title = get_title(row)
        cv = get_cv(row)
        normalized.append(f"{idx}|{uri}|{title}|{cv}")

    raw = "\n".join(normalized)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def summarize_rows(rows):
    cvs = [get_cv(row) for row in rows]

    article_count = len(rows)
    total_cv = sum(cvs)
    top_cv = max(cvs) if cvs else 0

    return article_count, total_cv, top_cv


def get_pv_rank_rows():
    """
    collect.py의 실제 수집 로직을 재사용합니다.
    이 함수는 DB에 저장하지 않고, API 응답에서 pvRank rows만 가져옵니다.
    """
    data = collect.fetch_stats_from_api()

    result = collect.extract_pv_rank(data)

    # collect.extract_pv_rank(data)가 (sampled_at, rows)를 반환하는 경우
    if isinstance(result, tuple) and len(result) == 2:
        sampled_at, rows = result
        return sampled_at, rows

    # 혹시 rows만 반환하는 구조일 경우 대비
    return None, result


def main():
    print("[INFO] 네이버 API 갱신 시각 탐지 시작")
    print(f"[INFO] 호출 간격: {INTERVAL_SECONDS}초")
    print(f"[INFO] 총 실행 시간: {DURATION_MINUTES}분")
    print(f"[INFO] 결과 파일: {OUTPUT_CSV}")
    print("[INFO] Ctrl+C로 중단할 수 있습니다.")
    print()

    end_time = time.time() + DURATION_MINUTES * 60

    last_signature = None
    last_total_cv = None
    last_top_cv = None

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            "checked_at",
            "api_sampled_at",
            "changed",
            "article_count",
            "total_cv",
            "delta_total_cv",
            "top_cv",
            "delta_top_cv",
            "signature",
        ])

        while time.time() < end_time:
            checked_at = now_str()

            try:
                api_sampled_at, rows = get_pv_rank_rows()

                if not rows:
                    print(f"[{checked_at}] ERROR: extract_pv_rank 결과 rows가 비어 있습니다.", flush=True)
                    writer.writerow([checked_at, api_sampled_at, "ERROR_EMPTY_ROWS", 0, 0, 0, 0, 0, ""])
                    f.flush()
                    time.sleep(INTERVAL_SECONDS)
                    continue

                signature = make_signature(rows)
                article_count, total_cv, top_cv = summarize_rows(rows)

                changed = signature != last_signature if last_signature is not None else True
                delta_total_cv = None if last_total_cv is None else total_cv - last_total_cv
                delta_top_cv = None if last_top_cv is None else top_cv - last_top_cv

                if changed:
                    print(
                        f"[{checked_at}] CHANGE "
                        f"api_sampled_at={api_sampled_at}, "
                        f"article_count={article_count}, "
                        f"total_cv={total_cv}, "
                        f"delta_total={delta_total_cv}, "
                        f"top_cv={top_cv}, "
                        f"delta_top={delta_top_cv}",
                        flush=True,
                    )
                else:
                    print(
                        f"[{checked_at}] same "
                        f"api_sampled_at={api_sampled_at}, "
                        f"total_cv={total_cv}, "
                        f"top_cv={top_cv}",
                        flush=True,
                    )

                writer.writerow([
                    checked_at,
                    api_sampled_at,
                    "Y" if changed else "N",
                    article_count,
                    total_cv,
                    delta_total_cv,
                    top_cv,
                    delta_top_cv,
                    signature,
                ])
                f.flush()

                last_signature = signature
                last_total_cv = total_cv
                last_top_cv = top_cv

            except KeyboardInterrupt:
                print()
                print("[INFO] 사용자 중단")
                break

            except Exception as e:
                print(f"[{checked_at}] ERROR: {e}", flush=True)
                writer.writerow([checked_at, "", "ERROR", "", "", "", "", "", str(e)])
                f.flush()

            time.sleep(INTERVAL_SECONDS)

    print()
    print("[INFO] 탐지 종료")


if __name__ == "__main__":
    main()



