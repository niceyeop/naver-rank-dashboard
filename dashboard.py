import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh


load_dotenv()

DB_PATH = os.getenv("DB_PATH", "naver_rank.db")
KST = ZoneInfo("Asia/Seoul")

st.set_page_config(
    page_title="네이버 실시간 조회수 순위",
    layout="wide"
)

refresh_count = st_autorefresh(interval=60 * 1000, key="dashboard_autorefresh")
st.cache_data.clear()


def get_conn():
    return sqlite3.connect(DB_PATH)


@st.cache_data(ttl=30)
def load_stat_dates():
    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT DISTINCT stat_date
        FROM naver_pv_rank_snapshots
        WHERE stat_date IS NOT NULL
        ORDER BY stat_date DESC
    """, conn)

    conn.close()
    return df


@st.cache_data(ttl=30)
def load_snapshot_times(stat_date):
    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT DISTINCT sampled_at
        FROM naver_pv_rank_snapshots
        WHERE stat_date = ?
        ORDER BY sampled_at DESC
    """, conn, params=(stat_date,))

    conn.close()
    return df


@st.cache_data(ttl=30)
def load_snapshot(stat_date, sampled_at):
    conn = get_conn()

    # 직전 대비 증가량을 안정적으로 계산하기 위해
    # 1) 윈도우 함수의 PARTITION을 uri 기준으로만 잡고 (stat_date에 의존하지 않음)
    # 2) WHERE 절에서 stat_date 필터를 빼서, 자정 경계나 stat_date가 달라지는
    #    케이스에서도 같은 uri의 직전 수집 시점을 정상적으로 찾을 수 있도록 한다.
    # 3) 마지막에 현재 sampled_at 행만 추리고, 표시용 stat_date 필터는
    #    prev_cv 계산이 끝난 뒤에 적용한다.
    df = pd.read_sql_query("""
        WITH ranked AS (
            SELECT
                sampled_at,
                stat_date,
                rank_no,
                uri,
                title,
                reporter,
                cv,
                cv_p,
                create_date,
                LAG(cv) OVER (
                    PARTITION BY uri
                    ORDER BY sampled_at
                ) AS prev_cv,
                LAG(rank_no) OVER (
                    PARTITION BY uri
                    ORDER BY sampled_at
                ) AS prev_rank_no,
                LAG(sampled_at) OVER (
                    PARTITION BY uri
                    ORDER BY sampled_at
                ) AS prev_sampled_at
            FROM naver_pv_rank_snapshots
            WHERE sampled_at <= ?
        )
        SELECT
            sampled_at,
            stat_date,
            rank_no,
            uri,
            title,
            reporter,
            cv,
            cv_p,
            create_date,
            prev_cv,
            prev_rank_no,
            prev_sampled_at
        FROM ranked
        WHERE sampled_at = ?
          AND (stat_date = ? OR stat_date IS NULL)
        ORDER BY rank_no ASC
    """, conn, params=(sampled_at, sampled_at, stat_date))

    conn.close()
    return df


@st.cache_data(ttl=30)
def load_history(stat_date, uri):
    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT
            sampled_at,
            stat_date,
            rank_no,
            title,
            reporter,
            cv,
            cv_p,
            create_date,
            uri
        FROM naver_pv_rank_snapshots
        WHERE stat_date = ?
          AND uri = ?
        ORDER BY sampled_at ASC
    """, conn, params=(stat_date, uri))

    conn.close()
    return df


def format_int(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):,}"


def format_signed_int(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):+,}"


st.title("네이버 실시간 조회수 순위")
st.caption(f"대시보드는 60초마다 자동 새로고침됩니다. 새로고침 횟수: {refresh_count}")

today_str = datetime.now(KST).strftime("%Y-%m-%d")

dates_df = load_stat_dates()

if dates_df.empty:
    st.warning("아직 수집된 데이터가 없습니다. 먼저 `python collect.py`를 실행하세요.")
    st.stop()

available_dates = dates_df["stat_date"].tolist()

# 오늘 데이터가 있으면 오늘을 기본 선택, 없으면 가장 최근 날짜 선택
default_date_index = available_dates.index(today_str) if today_str in available_dates else 0


with st.sidebar:
    st.header("설정")

    selected_stat_date = st.selectbox(
        "조회 날짜",
        available_dates,
        index=default_date_index
    )

    times_df = load_snapshot_times(selected_stat_date)

    if times_df.empty:
        st.warning(f"{selected_stat_date} 데이터가 아직 없습니다.")
        st.stop()

    sampled_times = times_df["sampled_at"].tolist()

    always_latest = st.checkbox("항상 최신 데이터 보기", value=True)

    if always_latest:
        selected_time = sampled_times[0]
        st.caption(f"현재 최신 시각: {selected_time}")
    else:
        selected_time = st.selectbox("조회 시각", sampled_times, index=0)

    top_n = st.slider("TOP N", min_value=5, max_value=100, value=20, step=5)

    st.caption(f"자동 새로고침 횟수: {refresh_count}")


df = load_snapshot(selected_stat_date, selected_time)

if df.empty:
    st.warning("선택한 시각의 데이터가 없습니다.")
    st.stop()

# prev_cv가 없으면(첫 등장 기사 등) delta_cv는 NaN으로 두고,
# 차트에서는 dropna로 걸러낸다. 단 cv 자체가 NULL인 비정상 행도 함께 걸러낸다.
df["delta_cv"] = pd.to_numeric(df["cv"], errors="coerce") - pd.to_numeric(df["prev_cv"], errors="coerce")
df["rank_change"] = pd.to_numeric(df["prev_rank_no"], errors="coerce") - pd.to_numeric(df["rank_no"], errors="coerce")

available_prev_times = df["prev_sampled_at"].dropna().unique().tolist()
compare_time = available_prev_times[0] if len(available_prev_times) == 1 else None

st.caption(f"조회 날짜: {selected_stat_date}")
st.caption(f"현재 선택 시각: {selected_time}")

if compare_time:
    st.caption(f"대표 비교 기준 시각: {compare_time}")
else:
    st.caption("기사별로 가장 최근의 이전 수집 시점과 비교합니다. 이전 데이터가 없는 기사는 '-'로 표시됩니다.")


col1, col2, col3, col4 = st.columns(4)

col1.metric("수집 기사 수", f"{len(df):,}")
col2.metric("1위 조회수", format_int(df.iloc[0]["cv"]))
col3.metric("TOP 10 조회수 합계", format_int(df.head(10)["cv"].sum()))
col4.metric("TOP 20 조회수 합계", format_int(df.head(20)["cv"].sum()))

st.divider()

left, right = st.columns(2)

with left:
    st.subheader(f"현재 조회수 TOP {top_n}")

    chart_df = df.head(top_n).copy()
    chart_df = chart_df.sort_values("cv", ascending=True)

    fig = px.bar(
        chart_df,
        x="cv",
        y="title",
        orientation="h",
        text="cv",
        labels={
            "cv": "조회수",
            "title": "기사"
        }
    )

    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(height=max(400, top_n * 28), margin=dict(l=10, r=10, t=30, b=10))

    st.plotly_chart(fig, width="stretch", key="current_top_chart")


with right:
    st.subheader(f"직전 대비 증가 TOP {top_n}")

    # delta_cv가 NaN이거나 0 이하인 행은 제외하고, 양의 증가분만 표시한다.
    # 직전 수집 데이터가 아직 없는 첫 스냅샷에서는 이 차트가 비어 있을 수 있다.
    delta_df = df.dropna(subset=["delta_cv"]).copy()
    delta_df = delta_df[delta_df["delta_cv"] > 0]
    delta_df = delta_df.sort_values("delta_cv", ascending=False).head(top_n)
    delta_df = delta_df.sort_values("delta_cv", ascending=True)

    if delta_df.empty:
        st.info(
            "아직 직전 수집 데이터와 비교할 수 있는 증가분이 없습니다. "
            "다음 10분 단위 수집이 끝나면 표시됩니다."
        )
    else:
        fig = px.bar(
            delta_df,
            x="delta_cv",
            y="title",
            orientation="h",
            text="delta_cv",
            labels={
                "delta_cv": "직전 대비 증가 조회수",
                "title": "기사"
            }
        )

        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(height=max(400, len(delta_df) * 28), margin=dict(l=10, r=10, t=30, b=10))

        st.plotly_chart(fig, width="stretch", key="delta_top_chart")


st.divider()

st.subheader("실시간 순위표")

display_df = df.copy()

display_df["조회수"] = display_df["cv"].apply(format_int)
display_df["직전 대비"] = display_df["delta_cv"].apply(format_signed_int)
display_df["순위 변동"] = display_df["rank_change"].apply(format_signed_int)
display_df["점유율"] = display_df["cv_p"].apply(lambda x: "-" if pd.isna(x) else f"{float(x):.2f}%")

display_df = display_df[[
    "rank_no",
    "순위 변동",
    "title",
    "reporter",
    "조회수",
    "직전 대비",
    "점유율",
    "create_date",
    "uri"
]]

display_df = display_df.rename(columns={
    "rank_no": "순위",
    "title": "제목",
    "reporter": "기자",
    "create_date": "발행시각",
    "uri": "URL"
})


st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn("URL")
    }
)


st.divider()

st.subheader("기사별 조회수 추이")

article_options = df[["title", "uri"]].copy()
article_options["label"] = article_options["title"] + " | " + article_options["uri"]

selected_article_label = st.selectbox(
    "추이를 볼 기사 선택",
    article_options["label"].tolist()
)

selected_uri = article_options.loc[
    article_options["label"] == selected_article_label,
    "uri"
].iloc[0]

history_df = load_history(selected_stat_date, selected_uri)

if len(history_df) >= 2:
    history_df["delta_cv"] = history_df["cv"].diff()

    fig1 = px.line(
        history_df,
        x="sampled_at",
        y="cv",
        markers=True,
        labels={
            "sampled_at": "수집 시각",
            "cv": "누적 조회수"
        },
        title="누적 조회수 추이"
    )

    st.plotly_chart(fig1, width="stretch", key="article_history_line_chart")

    fig2 = px.bar(
        history_df.dropna(subset=["delta_cv"]),
        x="sampled_at",
        y="delta_cv",
        labels={
            "sampled_at": "수집 시각",
            "delta_cv": "직전 대비 증가"
        },
        title="직전 대비 증가량"
    )

    st.plotly_chart(fig2, width="stretch", key="article_history_delta_chart")
else:
    st.info("이 기사는 아직 추이를 그릴 만큼 데이터가 충분하지 않습니다.")
