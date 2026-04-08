import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Air Ballers",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------
# Config
# -------------------------------------------------
TEAM_NAME = "Air Ballers"
TEAM_SUBTITLE = "Official Team Page"
TIMEZONE = ZoneInfo("Europe/Athens")

NEXT_GAME_FILE = "next_game.csv"
RESULTS_FILE = "results.csv"
LOGO_FILE = "logo.png"

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def load_csv_safe(path: str, columns: list[str]) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig", sep=None, engine="python")
        df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


def parse_next_game(df: pd.DataFrame):
    if df.empty:
        return None

    row = df.iloc[0].to_dict()

    date_value = str(row.get("date", "")).strip()
    time_value = str(row.get("time", "")).strip()

    game_dt = None
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H.%M",
        "%d/%m/%y %H.%M",
    ):
        try:
            game_dt = datetime.strptime(f"{date_value} {time_value}", fmt).replace(tzinfo=TIMEZONE)
            break
        except Exception:
            continue

    if game_dt is None:
        return None

    return {
        "opponent": str(row.get("opponent", "TBD")),
        "date": date_value,
        "time": time_value,
        "venue": str(row.get("venue", "TBD")),
        "home_away": str(row.get("home_away", "TBD")),
        "datetime": game_dt,
    }


def enrich_results(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    required_cols = ["date", "opponent", "team_score", "opponent_score"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return pd.DataFrame(columns=required_cols + ["result", "score_display"])

    df["team_score"] = pd.to_numeric(df["team_score"], errors="coerce")
    df["opponent_score"] = pd.to_numeric(df["opponent_score"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)

    df = df.dropna(subset=["date", "team_score", "opponent_score"])

    df["result"] = df.apply(
        lambda x: "W" if x["team_score"] > x["opponent_score"] else "L",
        axis=1,
    )
    df["score_display"] = (
        df["team_score"].astype(int).astype(str)
        + "-"
        + df["opponent_score"].astype(int).astype(str)
    )

    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df


def get_last_result(results_df: pd.DataFrame):
    if results_df.empty:
        return None

    row = results_df.iloc[0]
    return {
        "opponent": row["opponent"],
        "result": row["result"],
        "score": row["score_display"],
        "date": row["date"],
    }


def get_streak(results_df: pd.DataFrame):
    if results_df.empty:
        return {"label": "No games yet", "value": "—", "type": "neutral"}

    latest = results_df.iloc[0]["result"]
    streak_count = 0

    for _, row in results_df.iterrows():
        if row["result"] == latest:
            streak_count += 1
        else:
            break

    if latest == "W":
        return {"label": "Winning Streak", "value": str(streak_count), "type": "win"}

    return {"label": "Losing Streak", "value": str(streak_count), "type": "loss"}


def get_countdown(game_dt: datetime):
    now = datetime.now(TIMEZONE)
    diff = game_dt - now

    if diff.total_seconds() <= 0:
        return None

    total_seconds = int(diff.total_seconds())
    days = total_seconds // (24 * 3600)
    remainder = total_seconds % (24 * 3600)
    hours = remainder // 3600
    minutes = (remainder % 3600) // 60

    return {"days": days, "hours": hours, "minutes": minutes}


def format_game_datetime(game_dt: datetime):
    return game_dt.strftime("%A, %d %B %Y • %H:%M")


def esc(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# -------------------------------------------------
# Load data
# -------------------------------------------------
next_game_df = load_csv_safe(
    NEXT_GAME_FILE, ["opponent", "date", "time", "venue", "home_away"]
)
results_df = load_csv_safe(
    RESULTS_FILE, ["date", "opponent", "team_score", "opponent_score"]
)

next_game = parse_next_game(next_game_df)
results_df = enrich_results(results_df)
last_result = get_last_result(results_df)
streak = get_streak(results_df)

# -------------------------------------------------
# Auto refresh every 60 seconds
# -------------------------------------------------
st.markdown(
    """
    <meta http-equiv="refresh" content="60">
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Global styling
# -------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #05070b !important;
        color: white !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: #05070b !important;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .hero-wrap {
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .hero-title {
        color: #ffffff;
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: 0.02em;
        margin-top: 0.6rem;
        margin-bottom: 0.2rem;
    }

    .hero-subtitle {
        color: #98a2b3;
        font-size: 1rem;
        margin-bottom: 0.2rem;
    }

    .section-heading {
        color: #ffffff;
        font-size: 1.25rem;
        font-weight: 800;
        margin-top: 1.4rem;
        margin-bottom: 0.8rem;
    }

    .card {
        background: linear-gradient(180deg, #101722 0%, #0c1119 100%);
        border: 1px solid #1e2937;
        border-radius: 24px;
        padding: 1.15rem 1.15rem;
        box-shadow: 0 14px 36px rgba(0,0,0,0.35);
        min-height: 170px;
    }

    .label {
        color: #9fb0c7;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.9rem;
    }

    .value {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 900;
        line-height: 1.15;
        margin-bottom: 0.5rem;
    }

    .sub {
        color: #c7d1dd;
        font-size: 1rem;
        line-height: 1.45;
        margin-top: 0.15rem;
    }

    .pill-win,
    .pill-loss {
        display: inline-block;
        padding: 0.38rem 0.8rem;
        border-radius: 999px;
        font-size: 0.88rem;
        font-weight: 800;
        margin-top: 0.2rem;
    }

    .pill-win {
        background: rgba(34, 197, 94, 0.16);
        color: #4ade80;
    }

    .pill-loss {
        background: rgba(239, 68, 68, 0.16);
        color: #f87171;
    }

    .countdown-shell {
        background: linear-gradient(180deg, #101722 0%, #0c1119 100%);
        border: 1px solid #1e2937;
        border-radius: 28px;
        padding: 1rem;
        box-shadow: 0 14px 36px rgba(0,0,0,0.35);
    }

    .count-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }

    .count-box {
        background: #060b13;
        border: 1px solid #182232;
        border-radius: 22px;
        padding: 1.25rem 0.8rem;
        text-align: center;
    }

    .count-num {
        color: #ff7a00;
        font-size: 2.4rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.35rem;
    }

    .count-lbl {
        color: #d8dee7;
        font-size: 0.95rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .results-grid {
        display: grid;
        gap: 0.9rem;
        margin-top: 0.2rem;
    }

    .result-card {
        background: linear-gradient(180deg, #101722 0%, #0c1119 100%);
        border: 1px solid #1e2937;
        border-radius: 22px;
        padding: 1rem 1rem;
        box-shadow: 0 10px 28px rgba(0,0,0,0.28);
    }

    .result-top {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
    }

    .result-opponent {
        color: #ffffff;
        font-size: 1.08rem;
        font-weight: 800;
    }

    .result-date {
        color: #94a3b8;
        font-size: 0.92rem;
    }

    .result-bottom {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
        margin-top: 0.65rem;
    }

    .result-score {
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 900;
    }

    .empty-box {
        background: linear-gradient(180deg, #101722 0%, #0c1119 100%);
        border: 1px dashed #334155;
        border-radius: 22px;
        padding: 1rem;
        color: #cbd5e1;
    }

    .stImage {
        text-align: center;
    }

    .stImage img {
        border-radius: 16px;
    }

    @media (max-width: 900px) {
        .hero-title {
            font-size: 2rem;
        }

        .value {
            font-size: 1.5rem;
        }

        .count-num {
            font-size: 2rem;
        }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        .hero-title {
            font-size: 1.7rem;
        }

        .hero-subtitle {
            font-size: 0.92rem;
        }

        .count-grid {
            grid-template-columns: 1fr;
        }

        .count-num {
            font-size: 1.9rem;
        }

        .value {
            font-size: 1.35rem;
        }

        .card {
            min-height: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Hero
# -------------------------------------------------
if Path(LOGO_FILE).exists():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.image(LOGO_FILE, width=140)

st.markdown(
    f"""
    <div class="hero-wrap">
        <div class="hero-title">{TEAM_NAME}</div>
        <div class="hero-subtitle">{TEAM_SUBTITLE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Top cards
# -------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    if next_game:
        st.markdown(
            f"""
            <div class="card">
                <div class="label">Next Game</div>
                <div class="value">vs {esc(next_game['opponent'])}</div>
                <div class="sub">{esc(format_game_datetime(next_game['datetime']))}</div>
                <div class="sub">{esc(next_game['home_away'])} • {esc(next_game['venue'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="card">
                <div class="label">Next Game</div>
                <div class="value">Not set</div>
                <div class="sub">Update next_game.csv</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col2:
    if streak["type"] == "win":
        streak_sub = "Team is on a hot run"
    elif streak["type"] == "loss":
        streak_sub = "Time to bounce back"
    else:
        streak_sub = "No results available yet"

    st.markdown(
        f"""
        <div class="card">
            <div class="label">{esc(streak['label'])}</div>
            <div class="value">{esc(streak['value'])}</div>
            <div class="sub">{esc(streak_sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    if last_result:
        pill_class = "pill-win" if last_result["result"] == "W" else "pill-loss"
        pill_text = "Win" if last_result["result"] == "W" else "Loss"

        st.markdown(
            f"""
            <div class="card">
                <div class="label">Last Result</div>
                <div class="value">vs {esc(last_result['opponent'])}</div>
                <div class="{pill_class}">{pill_text}</div>
                <div class="sub">{esc(last_result['score'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="card">
                <div class="label">Last Result</div>
                <div class="value">No games yet</div>
                <div class="sub">Update results.csv</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------------------------------
# Countdown
# -------------------------------------------------
st.markdown('<div class="section-heading">Countdown to Next Game</div>', unsafe_allow_html=True)

if next_game:
    countdown = get_countdown(next_game["datetime"])
    if countdown:
        st.markdown(
            f"""
            <div class="countdown-shell">
                <div class="count-grid">
                    <div class="count-box">
                        <div class="count-num">{countdown['days']}</div>
                        <div class="count-lbl">Days</div>
                    </div>
                    <div class="count-box">
                        <div class="count-num">{countdown['hours']}</div>
                        <div class="count-lbl">Hours</div>
                    </div>
                    <div class="count-box">
                        <div class="count-num">{countdown['minutes']}</div>
                        <div class="count-lbl">Minutes</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="empty-box">
                The scheduled game time has already passed. Update next_game.csv with the next fixture.
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        """
        <div class="empty-box">
            No next game found. Update next_game.csv.
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# Previous results
# -------------------------------------------------
st.markdown('<div class="section-heading">Previous Results</div>', unsafe_allow_html=True)

if not results_df.empty:
    results_html = '<div class="results-grid">'
    for _, row in results_df.head(8).iterrows():
        result_class = "pill-win" if row["result"] == "W" else "pill-loss"
        result_word = "Win" if row["result"] == "W" else "Loss"
        date_str = row["date"].strftime("%d %b %Y")

        results_html += f"""
        <div class="result-card">
            <div class="result-top">
                <div class="result-opponent">vs {esc(row['opponent'])}</div>
                <div class="result-date">{esc(date_str)}</div>
            </div>
            <div class="result-bottom">
                <div class="{result_class}">{result_word}</div>
                <div class="result-score">{esc(row['score_display'])}</div>
            </div>
        </div>
        """

    results_html += "</div>"
    st.markdown(results_html, unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="empty-box">
            No previous results found. Update results.csv.
        </div>
        """,
        unsafe_allow_html=True,
    )
