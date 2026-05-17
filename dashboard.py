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
DB_TIMEOUT_SECONDS = 30
DB_BUSY_TIMEOUT_MS = 30_000
KST = ZoneInfo("Asia/Seoul")

st.set_page_config(
    page_title="네이버 실시간 조회수 순위",
    layout="wide"
)


def inject_custom_css():
    st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .hero-card {
        padding: 28px 32px;
        border-radius: 24px;
        background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.25), transparent 32%),
            linear-gradient(135deg, #0f172a 0%, #111827 50%, #020617 100%);
        border: 1px solid rgba(148, 163, 184, 0.18);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
        margin-bottom: 24px;
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 8px;
        letter-spacing: -0.04em;
    }

    .hero-subtitle {
        font-size: 15px;
        color: #94a3b8;
    }

    .kpi-card {
        padding: 22px 24px;
        border-radius: 22px;
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(15, 23, 42, 0.72));
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 14px 35px rgba(0, 0, 0, 0.22);
        min-height: 132px;
    }

    .kpi-label {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 10px;
    }

    .kpi-value {
        font-size: 30px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.04em;
    }

    .kpi-desc {
        margin-top: 8px;
        font-size: 13px;
        color: #38bdf8;
    }
    </style>
    """, unsafe_allow_html=True)


inject_custom_css()

refresh_count = st_autorefresh(interval=60 * 1000, key="dashboard_autorefresh")


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)
    conn.execute(f"PRAGMA busy_timeout = {DB_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


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
def load_previous_time(sampled_at):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT sampled_at
        FROM naver_pv_rank_snapshots
        WHERE sampled_at < ?
        GROUP BY sampled_at
        ORDER BY sampled_at DESC
        LIMIT 1
    """, conn, params=(sampled_at,))
    conn.close()

    if df.empty:
        return None

    return df.iloc[0]["sampled_at"]


@st.cache_data(ttl=30)
def load_snapshot(stat_date, sampled_at):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT
            sampled_at,
            stat_date,
            rank_no,
            uri,
            title,
            reporter,
            cv,
            cv_p,
            create_date
        FROM naver_pv_rank_snapshots
        WHERE sampled_at = ?
          AND (stat_date = ? OR stat_date IS NULL)
        ORDER BY rank_no ASC
    """, conn, params=(sampled_at, stat_date))
    conn.close()
    return df


@st.cache_data(ttl=30)
def load_snapshot_by_time(sampled_at):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT
            sampled_at,
            stat_date,
            rank_no,
            uri,
            title,
            reporter,
            cv,
            cv_p,
            create_date
        FROM naver_pv_rank_snapshots
        WHERE sampled_at = ?
        ORDER BY rank_no ASC
    """, conn, params=(sampled_at,))
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


def compare_gap_minutes(selected_time, compare_time):
    if not compare_time:
        return None

    selected_dt = pd.to_datetime(selected_time)
    compare_dt = pd.to_datetime(compare_time)
    return int((selected_dt - compare_dt).total_seconds() // 60)


def apply_plotly_style(fig, height=420):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.35)",
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            color="#E5E7EB",
            size=12
        ),
        margin=dict(l=10, r=20, t=40, b=20),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.12)",
            zerolinecolor="rgba(148, 163, 184, 0.2)"
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.08)"
        ),
        hoverlabel=dict(
            bgcolor="#020617",
            bordercolor="#38BDF8",
            font_size=13
        )
    )

    fig.update_traces(
        marker_line_width=0,
        opacity=0.92
    )

    return fig


def kpi_card(label, value, desc=None):
    desc_html = f'<div class="kpi-desc">{desc}</div>' if desc else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {desc_html}
    </div>
    """, unsafe_allow_html=True)


st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">네이버 실시간 조회수 순위</div>
    <div class="hero-subtitle">
        60초마다 자동 새로고침됩니다 · 새로고침 횟수 {refresh_count:,}회
    </div>
</div>
""", unsafe_allow_html=True)


today_str = datetime.now(KST).strftime("%Y-%m-%d")
dates_df = load_stat_dates()

if dates_df.empty:
    st.warning("아직 수집된 데이터가 없습니다. 먼저 `python collect.py`를 실행하세요.")
    st.stop()

available_dates = dates_df["stat_date"].tolist()
default_date_index = available_dates.index(today_str) if today_str in available_dates else 0

with st.sidebar:
    st.header("대시보드 설정")
    st.caption("조회할 날짜와 스냅샷 시각을 선택하세요.")

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
    always_latest = st.toggle("항상 최신 데이터 보기", value=True)

    if always_latest:
        selected_time = sampled_times[0]
        st.caption(f"최신 수집 시각: `{selected_time}`")
    else:
        selected_time = st.selectbox("조회 시각", sampled_times, index=0)

    top_n = st.slider("표시할 기사 수", min_value=5, max_value=100, value=20, step=5)

    st.divider()
    st.caption(f"자동 새로고침 횟수: {refresh_count:,}")


df = load_snapshot(selected_stat_date, selected_time)

if df.empty:
    st.warning("선택한 시각의 스냅샷 데이터가 없습니다.")
    st.stop()

compare_time = load_previous_time(selected_time)

if compare_time:
    prev_df = load_snapshot_by_time(compare_time)
    prev_df = prev_df[["uri", "cv", "rank_no"]].copy()
    prev_df = prev_df.rename(columns={
        "cv": "prev_cv",
        "rank_no": "prev_rank_no",
    })

    df = df.merge(prev_df, on="uri", how="left")
else:
    df["prev_cv"] = pd.NA
    df["prev_rank_no"] = pd.NA

df["cv"] = pd.to_numeric(df["cv"], errors="coerce")
df["prev_cv"] = pd.to_numeric(df["prev_cv"], errors="coerce")
df["delta_cv"] = df["cv"] - df["prev_cv"]

df["rank_no"] = pd.to_numeric(df["rank_no"], errors="coerce")
df["prev_rank_no"] = pd.to_numeric(df["prev_rank_no"], errors="coerce")
df["rank_change"] = df["prev_rank_no"] - df["rank_no"]

st.caption(f"조회 날짜: {selected_stat_date}")
st.caption(f"현재 선택 시각: {selected_time}")

if compare_time:
    gap_minutes = compare_gap_minutes(selected_time, compare_time)
    st.caption(f"비교 기준 시각: {compare_time}")

    if gap_minutes and gap_minutes > 10:
        st.warning(
            f"직전 저장 스냅샷과 {gap_minutes}분 차이가 납니다. "
            "중간 수집분이 누락되었을 수 있어 증가량은 해당 간격 전체 기준입니다."
        )
else:
    st.caption("비교 기준 시각: 없음")

col1, col2, col3, col4 = st.columns(4)

with col1:
    kpi_card("수집 기사 수", f"{len(df):,}", "현재 스냅샷 기준")

with col2:
    kpi_card("1위 조회수", format_int(df.iloc[0]["cv"]), "최상위 기사")

with col3:
    kpi_card("TOP 10 조회수 합계", format_int(df.head(10)["cv"].sum()), "상위 10개 기사")

with col4:
    kpi_card("TOP 20 조회수 합계", format_int(df.head(20)["cv"].sum()), "상위 20개 기사")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader(f"현재 조회수 TOP {top_n}")

    chart_df = df.head(top_n).copy()
    chart_df["short_title"] = chart_df["title"].fillna("(제목 없음)").apply(
        lambda x: x if len(str(x)) <= 34 else str(x)[:34] + "..."
    )
    chart_df = chart_df.sort_values("cv", ascending=True)

    fig = px.bar(
        chart_df,
        x="cv",
        y="short_title",
        orientation="h",
        text="cv",
        hover_data={
            "title": True,
            "cv": ":,"
        },
        labels={
            "cv": "조회수",
            "short_title": "기사"
        }
    )

    fig.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
        marker_color="#38BDF8"
    )

    fig = apply_plotly_style(fig, height=max(420, top_n * 30))
    st.plotly_chart(fig, width="stretch", key="current_top_chart")

with right:
    st.subheader(f"직전 대비 증가 TOP {top_n}")

    delta_df = df.dropna(subset=["delta_cv"]).copy()
    delta_df = delta_df[delta_df["delta_cv"] > 0]
    delta_df = delta_df.sort_values("delta_cv", ascending=False).head(top_n)
    delta_df["short_title"] = delta_df["title"].fillna("(제목 없음)").apply(
        lambda x: x if len(str(x)) <= 34 else str(x)[:34] + "..."
    )
    delta_df = delta_df.sort_values("delta_cv", ascending=True)

    if delta_df.empty:
       st.info(
           "아직 직전 수집 데이터와 비교할 수 있는 증가분이 없습니다. "
           "현재 선택 시각보다 이전 수집 데이터가 없거나, 증가한 기사가 없습니다."
       )
       st.caption(f"현재 선택 시각: {selected_time}")
       st.caption(f"비교 기준 시각: {compare_time}")
    else:
        fig = px.bar(
            delta_df,
            x="delta_cv",
            y="short_title",
            orientation="h",
            text="delta_cv",
            hover_data={
                "title": True,
                "delta_cv": ":,"
            },
            labels={
                "delta_cv": "직전 대비 증가 조회수",
                "short_title": "기사"
            }
        )

        fig.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            marker_color="#22C55E"
        )

        fig = apply_plotly_style(fig, height=max(420, len(delta_df) * 30))
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
article_options["title"] = article_options["title"].fillna("(제목 없음)")
article_options["uri"] = article_options["uri"].fillna("")
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

    fig1.update_traces(
        line=dict(color="#38BDF8", width=3),
        marker=dict(size=7, color="#38BDF8")
    )

    fig1 = apply_plotly_style(fig1, height=430)
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

    fig2.update_traces(
        marker_color="#A78BFA"
    )

    fig2 = apply_plotly_style(fig2, height=380)
    st.plotly_chart(fig2, width="stretch", key="article_history_delta_chart")
else:
    st.info("이 기사는 아직 추이를 그릴 만큼 데이터가 충분하지 않습니다.")
