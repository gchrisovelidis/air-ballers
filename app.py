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
ROSTER_FILE = "roster.csv"
LOGO_FILE = "logo.png"  # optional

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def load_csv_safe(path: str, columns: list[str]) -> pd.DataFrame:
    file_path = Path(path)
    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)


def parse_next_game(df: pd.DataFrame):
    """
    Expected columns:
    opponent,date,time,venue,home_away
    Example date: 2026-04-15
    Example time: 20:30
    """
    if df.empty:
        return None

    row = df.iloc[0].to_dict()

    try:
        game_dt = datetime.strptime(
            f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=TIMEZONE)
    except Exception:
        return None

    return {
        "opponent": row.get("opponent", "TBD"),
        "date": row.get("date", ""),
        "time": row.get("time", ""),
        "venue": row.get("venue", "TBD"),
        "home_away": row.get("home_away", "TBD"),
        "datetime": game_dt,
    }


def enrich_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected columns:
    date,opponent,team_score,opponent_score
    """
    if df.empty:
        return df

    df = df.copy()
    df["team_score"] = pd.to_numeric(df["team_score"], errors="coerce")
    df["opponent_score"] = pd.to_numeric(df["opponent_score"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "team_score", "opponent_score"])

    df["result"] = df.apply(
        lambda x: "W" if x["team_score"] > x["opponent_score"] else "L",
        axis=1
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
        return {
            "label": "Winning Streak",
            "value": str(streak_count),
            "type": "win",
        }
    else:
        return {
            "label": "Losing Streak",
            "value": str(streak_count),
            "type": "loss",
        }


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

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
    }


def format_game_datetime(game_dt: datetime):
    return game_dt.strftime("%A, %d %B %Y • %H:%M")


# -------------------------------------------------
# Load data
# -------------------------------------------------
next_game_df = load_csv_safe(
    NEXT_GAME_FILE, ["opponent", "date", "time", "venue", "home_away"]
)
results_df = load_csv_safe(
    RESULTS_FILE, ["date", "opponent", "team_score", "opponent_score"]
)
roster_df = load_csv_safe(
    ROSTER_FILE, ["number", "name", "position"]
)

next_game = parse_next_game(next_game_df)
results_df = enrich_results(results_df)
last_result = get_last_result(results_df)
streak = get_streak(results_df)

# -------------------------------------------------
# Optional auto refresh every 60 seconds
# -------------------------------------------------
st.markdown(
    """
    <meta http-equiv="refresh" content="60">
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1200px;
    }

    html, body, [class*="css"] {
        font-family: Arial, sans-serif;
    }

    .app-bg {
        background: linear-gradient(180deg, #0f1115 0%, #171b22 100%);
        border-radius: 24px;
        padding: 1.2rem;
    }

    .hero {
        text-align: center;
        padding: 0.8rem 0 1.2rem 0;
    }

    .hero-logo {
        max-width: 110px;
        width: 100%;
        margin: 0 auto 0.7rem auto;
        display: block;
    }

    .hero-title {
        color: white;
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0.3rem;
    }

    .hero-subtitle {
        color: #b9c0cc;
        font-size: 1rem;
        margin-bottom: 0.2rem;
    }

    .section-title {
        color: white;
        font-size: 1.25rem;
        font-weight: 800;
        margin: 1.2rem 0 0.9rem 0;
    }

    .stat-card {
        background: #1d232d;
        border: 1px solid #2a3340;
        border-radius: 20px;
        padding: 1rem;
        color: white;
        min-height: 140px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.18);
    }

    .stat-label {
        color: #aab4c3;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.7rem;
    }

    .stat-value {
        color: white;
        font-size: 1.5rem;
        font-weight: 800;
        line-height: 1.2;
    }

    .stat-sub {
        color: #c6ced8;
        font-size: 0.95rem;
        margin-top: 0.45rem;
        line-height: 1.4;
    }

    .countdown-wrap {
        background: #1d232d;
        border: 1px solid #2a3340;
        border-radius: 24px;
        padding: 1.2rem;
        margin-top: 0.4rem;
    }

    .countdown-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.8rem;
    }

    .countdown-box {
        background: #12171d;
        border-radius: 18px;
        padding: 1rem 0.7rem;
        text-align: center;
        border: 1px solid #242c36;
    }

    .countdown-number {
        color: #ff7a00;
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
    }

    .countdown-label {
        color: #b7c0cb;
        font-size: 0.9rem;
        margin-top: 0.35rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .results-list {
        display: grid;
        gap: 0.8rem;
    }

    .result-card {
        background: #1d232d;
        border: 1px solid #2a3340;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        color: white;
    }

    .result-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.8rem;
        flex-wrap: wrap;
    }

    .result-opponent {
        font-size: 1.05rem;
        font-weight: 800;
    }

    .result-date {
        color: #aeb8c5;
        font-size: 0.9rem;
    }

    .result-bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.5rem;
        flex-wrap: wrap;
        gap: 0.6rem;
    }

    .badge-win, .badge-loss {
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 800;
        display: inline-block;
    }

    .badge-win {
        background: rgba(34, 197, 94, 0.16);
        color: #4ade80;
    }

    .badge-loss {
        background: rgba(239, 68, 68, 0.16);
        color: #f87171;
    }

    .score {
        font-size: 1rem;
        font-weight: 800;
    }

    .roster-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.8rem;
    }

    .player-card {
        background: #1d232d;
        border: 1px solid #2a3340;
        border-radius: 18px;
        padding: 0.95rem;
        color: white;
    }

    .player-number {
        color: #ff7a00;
        font-size: 1.1rem;
        font-weight: 900;
        margin-bottom: 0.25rem;
    }

    .player-name {
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .player-pos {
        color: #b7c0cb;
        font-size: 0.92rem;
    }

    .empty-box {
        background: #1d232d;
        border: 1px dashed #3a4655;
        border-radius: 18px;
        padding: 1rem;
        color: #b7c0cb;
    }

    @media (max-width: 900px) {
        .hero-title {
            font-size: 1.75rem;
        }

        .countdown-number {
            font-size: 1.6rem;
        }

        .roster-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }

        .hero-title {
            font-size: 1.55rem;
        }

        .hero-subtitle {
            font-size: 0.92rem;
        }

        .countdown-grid {
            grid-template-columns: 1fr;
        }

        .roster-grid {
            grid-template-columns: 1fr;
        }

        .stat-value {
            font-size: 1.25rem;
        }

        .countdown-number {
            font-size: 1.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# Main wrapper
# -------------------------------------------------
st.markdown('<div class="app-bg">', unsafe_allow_html=True)

# -------------------------------------------------
# Hero
# -------------------------------------------------
logo_html = ""
if Path(LOGO_FILE).exists():
    logo_html = f'<img src="data:image/png;base64,{Path(LOGO_FILE).read_bytes().hex()}" class="hero-logo">'

# Safer alternative: use st.image for rendering logo
if Path(LOGO_FILE).exists():
    st.image(LOGO_FILE, width=110)

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">{TEAM_NAME}</div>
        <div class="hero-subtitle">{TEAM_SUBTITLE}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# Top cards
# -------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    if next_game:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Next Game</div>
                <div class="stat-value">vs {next_game['opponent']}</div>
                <div class="stat-sub">{format_game_datetime(next_game['datetime'])}</div>
                <div class="stat-sub">{next_game['home_away']} • {next_game['venue']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="stat-card">
                <div class="stat-label">Next Game</div>
                <div class="stat-value">Not set</div>
                <div class="stat-sub">Add one row in next_game.csv</div>
            </div>
            """,
            unsafe_allow_html=True
        )

with col2:
    streak_class = "white"
    streak_sub = ""
    if streak["type"] == "win":
        streak_sub = "Team is on a hot run"
    elif streak["type"] == "loss":
        streak_sub = "Time to bounce back"
    else:
        streak_sub = "No results available yet"

    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{streak['label']}</div>
            <div class="stat-value">{streak['value']}</div>
            <div class="stat-sub">{streak_sub}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    if last_result:
        badge_class = "badge-win" if last_result["result"] == "W" else "badge-loss"
        result_word = "Win" if last_result["result"] == "W" else "Loss"
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">Last Result</div>
                <div class="stat-value">vs {last_result['opponent']}</div>
                <div class="stat-sub">
                    <span class="{badge_class}">{result_word}</span>
                </div>
                <div class="stat-sub">{last_result['score']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="stat-card">
                <div class="stat-label">Last Result</div>
                <div class="stat-value">No games yet</div>
                <div class="stat-sub">Add rows in results.csv</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# -------------------------------------------------
# Countdown section
# -------------------------------------------------
st.markdown('<div class="section-title">Countdown to Next Game</div>', unsafe_allow_html=True)

if next_game:
    countdown = get_countdown(next_game["datetime"])
    if countdown:
        st.markdown(
            f"""
            <div class="countdown-wrap">
                <div class="countdown-grid">
                    <div class="countdown-box">
                        <div class="countdown-number">{countdown['days']}</div>
                        <div class="countdown-label">Days</div>
                    </div>
                    <div class="countdown-box">
                        <div class="countdown-number">{countdown['hours']}</div>
                        <div class="countdown-label">Hours</div>
                    </div>
                    <div class="countdown-box">
                        <div class="countdown-number">{countdown['minutes']}</div>
                        <div class="countdown-label">Minutes</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="empty-box">
                The scheduled game time has already passed. Update next_game.csv with the next fixture.
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.markdown(
        """
        <div class="empty-box">
            No next game found. Add one row to next_game.csv.
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------------------------
# Previous results
# -------------------------------------------------
st.markdown('<div class="section-title">Previous Results</div>', unsafe_allow_html=True)

if not results_df.empty:
    recent_results = results_df.head(8)

    results_html = '<div class="results-list">'
    for _, row in recent_results.iterrows():
        badge_class = "badge-win" if row["result"] == "W" else "badge-loss"
        result_word = "Win" if row["result"] == "W" else "Loss"
        date_str = row["date"].strftime("%d %b %Y")

        results_html += f"""
        <div class="result-card">
            <div class="result-top">
                <div class="result-opponent">vs {row['opponent']}</div>
                <div class="result-date">{date_str}</div>
            </div>
            <div class="result-bottom">
                <div><span class="{badge_class}">{result_word}</span></div>
                <div class="score">{row['score_display']}</div>
            </div>
        </div>
        """

    results_html += "</div>"
    st.markdown(results_html, unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="empty-box">
            No previous results found. Add rows to results.csv.
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------------------------
# Roster
# -------------------------------------------------
st.markdown('<div class="section-title">Roster</div>', unsafe_allow_html=True)

if not roster_df.empty:
    roster_html = '<div class="roster-grid">'
    for _, row in roster_df.iterrows():
        number = row.get("number", "")
        name = row.get("name", "Player")
        position = row.get("position", "")

        roster_html += f"""
        <div class="player-card">
            <div class="player-number">#{number}</div>
            <div class="player-name">{name}</div>
            <div class="player-pos">{position}</div>
        </div>
        """
    roster_html += "</div>"
    st.markdown(roster_html, unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="empty-box">
            No roster found. Add rows to roster.csv.
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("</div>", unsafe_allow_html=True)
