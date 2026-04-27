import os
import json
import re
import sqlite3
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from http.cookiejar import MozillaCookieJar
from http.cookies import SimpleCookie
from urllib.parse import urlparse


import requests
from requests.cookies import create_cookie
from dotenv import load_dotenv


load_dotenv()

DB_PATH = os.getenv("DB_PATH", "naver_rank.db")
NAVER_STATS_URL = os.getenv("NAVER_STATS_URL", "")
NAVER_METHOD = os.getenv("NAVER_METHOD", "GET").upper()
NAVER_REFERER = os.getenv("NAVER_REFERER", "")
NAVER_COOKIE = os.getenv("NAVER_COOKIE", "")
NAVER_BODY = os.getenv("NAVER_BODY", "")
COOKIE_JAR_PATH = os.getenv("COOKIE_JAR_PATH", "naver_cookies.txt")

KST = ZoneInfo("Asia/Seoul")

def current_10min_slot_iso():
    now = datetime.now(KST)

    slot_minute = (now.minute // 10) * 10

    slot_time = now.replace(
        minute=slot_minute,
        second=0,
        microsecond=0
    )

    return slot_time.strftime("%Y-%m-%dT%H:%M:%S")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS naver_pv_rank_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sampled_at TEXT NOT NULL,
            stat_date TEXT,
            rank_no INTEGER,
            uri TEXT NOT NULL,
            title TEXT,
            reporter TEXT,
            cv INTEGER,
            cv_p REAL,
            create_date TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sampled_at, uri)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rank_sampled_at
        ON naver_pv_rank_snapshots(sampled_at)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rank_uri_sampled_at
        ON naver_pv_rank_snapshots(uri, sampled_at)
    """)


    conn.commit()
    conn.close()


def columnar_to_rows(data):
    """
    네이버 응답 형태:
    rows: {
      "date": [...],
      "uri": [...],
      "cv": [...]
    }

    이걸 아래 형태로 변환:
    [
      {"date": "...", "uri": "...", "cv": 123},
      ...
    ]
    """
    rows = data.get("rows", {})
    if not rows:
        return []

    keys = list(rows.keys())
    first_key = keys[0]
    length = len(rows[first_key])

    result = []

    for i in range(length):
        item = {}
        for key in keys:
            values = rows.get(key, [])
            item[key] = values[i] if i < len(values) else None
        result.append(item)

    return result


def build_cookie_session():
    session = requests.Session()

    cookie_jar = MozillaCookieJar(COOKIE_JAR_PATH)

    # 1. 기존 쿠키 파일이 있으면 우선 사용
    if os.path.exists(COOKIE_JAR_PATH):
        try:
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cookie_jar
            return session, cookie_jar
        except Exception as e:
            print(f"[WARN] 쿠키 파일 로드 실패. .env 쿠키를 사용합니다: {e}")

    # 2. 쿠키 파일이 없으면 .env의 NAVER_COOKIE로 초기화
    if not NAVER_COOKIE:
        raise RuntimeError(
            "쿠키 파일도 없고 NAVER_COOKIE도 없습니다. "
            ".env에 NAVER_COOKIE를 넣어주세요."
        )

    parsed_url = urlparse(NAVER_STATS_URL)
    host = parsed_url.hostname or ""

    if host.endswith("naver.com"):
        cookie_domain = ".naver.com"
    else:
        cookie_domain = host

    simple_cookie = SimpleCookie()
    simple_cookie.load(NAVER_COOKIE)

    for name, morsel in simple_cookie.items():
        cookie = create_cookie(
            name=name,
            value=morsel.value,
            domain=cookie_domain,
            path="/"
        )
        cookie_jar.set_cookie(cookie)

    session.cookies = cookie_jar

    cookie_jar.save(ignore_discard=True, ignore_expires=True)

    return session, cookie_jar



def load_stats_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_pv_rank(response_json):
    result = response_json.get("result", {})
    stat_data_list = result.get("statDataList", [])

    for stat in stat_data_list:
        if stat.get("dataId") == "pvRank":
            # 네이버 API utime을 그대로 쓰지 않고,
            # 우리가 수집한 시각을 10분 단위로 정렬해서 저장
            sampled_at = current_10min_slot_iso()

            data = stat.get("data", {})
            rows = columnar_to_rows(data)
            return sampled_at, rows

    raise RuntimeError("응답에서 dataId=pvRank를 찾지 못했습니다.")



def save_pv_rank(sampled_at, rows):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    saved_count = 0

    for idx, row in enumerate(rows, start=1):
        uri = row.get("uri")
        if not uri:
            continue

        cur.execute("""
            INSERT INTO naver_pv_rank_snapshots (
                sampled_at,
                stat_date,
                rank_no,
                uri,
                title,
                reporter,
                cv,
                cv_p,
                create_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sampled_at, uri)
            DO UPDATE SET
                stat_date = excluded.stat_date,
                rank_no = excluded.rank_no,
                title = excluded.title,
                reporter = excluded.reporter,
                cv = excluded.cv,
                cv_p = excluded.cv_p,
                create_date = excluded.create_date
        """, (
            sampled_at,
            row.get("date"),
            idx,
            uri,
            row.get("title"),
            row.get("reporter"),
            row.get("cv"),
            row.get("cv_p"),
            row.get("createDate"),
        ))

        saved_count += 1

    conn.commit()
    conn.close()

    return saved_count


KST = ZoneInfo("Asia/Seoul")


def today_kst_date():
    """
    한국 시간 기준 오늘 날짜를 YYYY-MM-DD 형식으로 반환합니다.
    예: 2026-04-27
    """
    return datetime.now(KST).strftime("%Y-%m-%d")


def apply_today_to_text(text):
    """
    문자열 안에 있는 YYYY-MM-DD 형식 날짜를 오늘 날짜로 바꿉니다.
    예: 2026-04-26 -> 2026-04-27
    """
    if not isinstance(text, str):
        return text

    today = today_kst_date()
    return re.sub(r"\d{4}-\d{2}-\d{2}", today, text)


def apply_today_to_body(value):
    """
    NAVER_BODY가 JSON일 때, 그 안에 들어 있는 날짜 문자열도 오늘 날짜로 바꿉니다.
    dict/list/string 모두 처리합니다.
    """
    if isinstance(value, dict):
        return {k: apply_today_to_body(v) for k, v in value.items()}

    if isinstance(value, list):
        return [apply_today_to_body(v) for v in value]

    if isinstance(value, str):
        return apply_today_to_text(value)

    return value

def fetch_stats_from_api():
    if not NAVER_STATS_URL:
        raise RuntimeError(".env에 NAVER_STATS_URL이 없습니다.")

    request_url = apply_today_to_text(NAVER_STATS_URL)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
    }

    if NAVER_REFERER:
        headers["Referer"] = NAVER_REFERER

    session, cookie_jar = build_cookie_session()

    method = (NAVER_METHOD or "GET").upper()

    print(f"[INFO] 요청 방식: {method}")
    print(f"[INFO] 요청 날짜: {today_kst_date()}")


    if NAVER_METHOD == "POST":
        body = None

        if NAVER_BODY.strip():
            try:
                body = json.loads(NAVER_BODY)
            except json.JSONDecodeError:
                raise RuntimeError("NAVER_BODY가 JSON 형식이 아닙니다.")

        body = apply_today_to_body(body)

        response = session.post(request_url, headers=headers, json=body, timeout=30)


    else:
        response = session.get(request_url, headers=headers, timeout=30)

    try:
        cookie_jar.save(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print(f"[WARN] 쿠키 저장 실패: {e}")

    if response.status_code in [401, 403]:
        raise RuntimeError(
            f"인증 실패로 보입니다. status={response.status_code}\n"
            "쿠키가 만료됐거나 재로그인이 필요할 수 있습니다."
        )

    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        print("JSON 파싱 실패. 응답 일부:")
        print(response.text[:1000])
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-file",
        help="API 대신 JSON 파일에서 읽어 테스트할 때 사용"
    )
    args = parser.parse_args()

    init_db()

    if args.from_file:
        response_json = load_stats_from_file(args.from_file)
    else:
        response_json = fetch_stats_from_api()

    sampled_at, rows = extract_pv_rank(response_json)
    saved_count = save_pv_rank(sampled_at, rows)

    print(f"[OK] sampled_at={sampled_at}, saved={saved_count}")


if __name__ == "__main__":
    main()
