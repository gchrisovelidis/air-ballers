import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

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
PLAYERS_FILE = "players.csv"
LOGO_FILE = "logo.png"
IMAGES_DIR = Path("images")

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
            game_dt = datetime.strptime(
                f"{date_value} {time_value}", fmt
            ).replace(tzinfo=TIMEZONE)
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
        return pd.DataFrame(columns=required_cols + ["result", "score_display", "youtube_url"])

    if "youtube_url" not in df.columns:
        df["youtube_url"] = ""

    df["team_score"] = pd.to_numeric(df["team_score"], errors="coerce")
    df["opponent_score"] = pd.to_numeric(df["opponent_score"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df["youtube_url"] = (
        df["youtube_url"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("nan", "")
    )

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


def enrich_players(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    required_cols = ["number", "name", "position"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return pd.DataFrame(columns=["number", "name", "position", "photo"])

    if "photo" not in df.columns:
        df["photo"] = ""

    df["number"] = df["number"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["position"] = df["position"].astype(str).str.strip()
    df["photo"] = df["photo"].fillna("").astype(str).str.strip()

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


def get_mime_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".png":
        return "image/png"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


# -------------------------------------------------
# Load data
# -------------------------------------------------
next_game_df = load_csv_safe(
    NEXT_GAME_FILE, ["opponent", "date", "time", "venue", "home_away"]
)
results_df = load_csv_safe(
    RESULTS_FILE, ["date", "opponent", "team_score", "opponent_score", "youtube_url"]
)
players_df = load_csv_safe(
    PLAYERS_FILE, ["number", "name", "position", "photo"]
)

next_game = parse_next_game(next_game_df)
results_df = enrich_results(results_df)
players_df = enrich_players(players_df)
last_result = get_last_result(results_df)
streak = get_streak(results_df)

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

    .hero-logo-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0.2rem;
        margin-bottom: 0.55rem;
    }

    .hero-logo {
        width: 210px;
        max-width: 70vw;
        display: block;
        border-radius: 18px;
    }

    .hero-wrap {
        text-align: center;
        margin-bottom: 1.2rem;
    }

    .hero-title {
        color: #ffffff;
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: 0.02em;
        margin-top: 0.1rem;
        margin-bottom: 0.15rem;
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
        margin-top: 0.2rem;
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
        padding: 1.35rem 0.8rem;
        text-align: center;
    }

    .count-num {
        color: #ff7a00;
        font-size: 2.6rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.45rem;
    }

    .count-lbl {
        color: #d8dee7;
        font-size: 0.95rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .countdown-note {
        color: #9fb0c7;
        text-align: center;
        font-size: 0.95rem;
        margin-top: 0.75rem;
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

    .watch-wrap {
        margin-top: 0.85rem;
    }

    .watch-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.62rem 1rem;
        border-radius: 12px;
        background: #ff7a00;
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: 0.92rem;
        border: 1px solid #ff8f26;
        transition: all 0.2s ease;
    }

    .watch-link:hover {
        background: #ff8f26;
        color: #ffffff !important;
        text-decoration: none !important;
    }

    .roster-heading {
        color: #ffffff;
        font-size: 1.9rem;
        font-weight: 900;
        text-align: center;
        margin-top: 1.8rem;
        margin-bottom: 1.2rem;
        letter-spacing: 0.02em;
    }

    .players-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.6rem 1.2rem;
        margin-top: 0.4rem;
    }

    .player-card {
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0.2rem 0.4rem 0.8rem 0.4rem;
        text-align: center;
    }

    .player-photo-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }

    .player-photo {
        width: 132px;
        height: 132px;
        object-fit: cover;
        border-radius: 22px;
        border: 1px solid #243244;
        display: block;
        box-shadow: 0 10px 24px rgba(0,0,0,0.28);
    }

    .player-photo-placeholder {
        width: 132px;
        height: 132px;
        border-radius: 22px;
        border: 1px solid #243244;
        background: linear-gradient(180deg, #0d141d 0%, #111a26 100%);
        color: #ff7a00;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7rem;
        font-weight: 900;
        box-shadow: 0 10px 24px rgba(0,0,0,0.28);
    }

    .player-number {
        color: #ff7a00;
        font-size: 1.55rem;
        font-weight: 900;
        margin-bottom: 0.28rem;
    }

    .player-name {
        color: #ffffff;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 0.22rem;
    }

    .player-position {
        color: #94a3b8;
        font-size: 0.96rem;
    }

    .empty-box {
        background: linear-gradient(180deg, #101722 0%, #0c1119 100%);
        border: 1px dashed #334155;
        border-radius: 22px;
        padding: 1rem;
        color: #cbd5e1;
    }

    @media (max-width: 900px) {
        .hero-logo {
            width: 180px;
        }

        .hero-title {
            font-size: 2rem;
        }

        .value {
            font-size: 1.5rem;
        }

        .count-num {
            font-size: 2.1rem;
        }

        .players-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 1.4rem 1rem;
        }

        .player-photo,
        .player-photo-placeholder {
            width: 120px;
            height: 120px;
        }

        .roster-heading {
            font-size: 1.7rem;
        }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }

        .hero-logo {
            width: 150px;
        }

        .hero-title {
            font-size: 1.75rem;
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

        .players-grid {
            grid-template-columns: 1fr;
            gap: 1.25rem;
        }

        .player-photo,
        .player-photo-placeholder {
            width: 108px;
            height: 108px;
        }

        .roster-heading {
            font-size: 1.5rem;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
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
    logo_path = Path(LOGO_FILE)
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    logo_mime = get_mime_type(logo_path)

    st.markdown(
        f"""
<div class="hero-logo-wrap">
<img src="data:{logo_mime};base64,{logo_b64}" class="hero-logo">
</div>
        """,
        unsafe_allow_html=True,
    )

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
<div class="countdown-note">Until tip-off</div>
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

        watch_html = ""
        youtube_url = str(row.get("youtube_url", "")).strip()

        if youtube_url:
            watch_html = f"""<div class="watch-wrap">
<a href="{youtube_url}" target="_blank" rel="noopener noreferrer" class="watch-link">Watch Game</a>
</div>"""

        results_html += f"""<div class="result-card">
<div class="result-top">
<div class="result-opponent">vs {esc(row['opponent'])}</div>
<div class="result-date">{esc(date_str)}</div>
</div>
<div class="result-bottom">
<div class="{result_class}">{result_word}</div>
<div class="result-score">{esc(row['score_display'])}</div>
</div>
{watch_html}
</div>"""

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

# -------------------------------------------------
# Players
# -------------------------------------------------
st.markdown('<div class="roster-heading">Team Roster</div>', unsafe_allow_html=True)

if not players_df.empty:
    players_html = '<div class="players-grid">'

    for _, row in players_df.iterrows():
        photo_name = str(row.get("photo", "")).strip()
        photo_html = ""

        if photo_name:
            photo_path = IMAGES_DIR / photo_name
            if photo_path.exists():
                img_b64 = base64.b64encode(photo_path.read_bytes()).decode()
                mime_type = get_mime_type(photo_path)

                photo_html = f"""<div class="player-photo-wrap">
<img src="data:{mime_type};base64,{img_b64}" class="player-photo">
</div>"""

        if not photo_html:
            initials = "".join([part[0] for part in str(row["name"]).split()[:2]]).upper()
            photo_html = f"""<div class="player-photo-wrap">
<div class="player-photo-placeholder">{esc(initials)}</div>
</div>"""

        players_html += f"""<div class="player-card">
{photo_html}
<div class="player-number">#{esc(row['number'])}</div>
<div class="player-name">{esc(row['name'])}</div>
<div class="player-position">{esc(row['position'])}</div>
</div>"""

    players_html += "</div>"
    st.markdown(players_html, unsafe_allow_html=True)
else:
    st.markdown(
        """
<div class="empty-box">
No players found. Update players.csv.
</div>
        """,
        unsafe_allow_html=True,
    )
