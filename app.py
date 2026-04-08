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
        font-family: Arial, Helvetica, sans-serif !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: #05070b !important;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 1.2rem;
        padding-bottom: 2.8rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .hero-logo-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0.25rem;
        margin-bottom: 0.65rem;
    }

    .hero-logo {
        width: 210px;
        max-width: 70vw;
        display: block;
        border-radius: 20px;
        box-shadow: 0 0 40px rgba(255, 122, 0, 0.14);
    }

    .hero-wrap {
        text-align: center;
        margin-bottom: 1.35rem;
    }

    .hero-title {
        color: #ffffff;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 2.9rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-top: 0.05rem;
        margin-bottom: 0.08rem;
        text-transform: uppercase;
    }

    .hero-subtitle {
        color: #b8c4d6;
        font-size: 1rem;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.10em;
    }

    .hero-accent {
        width: 72px;
        height: 3px;
        border-radius: 999px;
        margin: 0 auto;
        background: linear-gradient(90deg, #ff7a00, #ff9d3d);
        box-shadow: 0 0 14px rgba(255, 122, 0, 0.22);
    }

    .section-heading {
        color: #ffffff;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 1.65rem;
        font-weight: 600;
        margin-top: 1.6rem;
        margin-bottom: 0.9rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    .card {
        background: linear-gradient(180deg, #0f1720 0%, #0b1118 100%);
        border: 1px solid #1b2633;
        border-radius: 24px;
        padding: 1rem 1.05rem;
        box-shadow: 0 14px 36px rgba(0,0,0,0.34);
        min-height: 160px;
        position: relative;
        overflow: hidden;
    }

    .card::before {
        content: "";
        position: absolute;
        inset: 0 auto auto 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, rgba(255,122,0,0.55), rgba(255,157,61,0.08));
    }

    .label {
        color: #9fb0c7;
        font-size: 0.8rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.10em;
        margin-bottom: 0.75rem;
    }

    .value {
        color: #ffffff;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 2rem;
        font-weight: 600;
        line-height: 1.08;
        margin-bottom: 0.45rem;
        letter-spacing: 0.01em;
    }

    .sub {
        color: #b8c4d6;
        font-size: 0.98rem;
        line-height: 1.42;
        margin-top: 0.15rem;
    }

    .pill-win,
    .pill-loss {
        display: inline-block;
        padding: 0.38rem 0.82rem;
        border-radius: 999px;
        font-size: 0.87rem;
        font-weight: 800;
        margin-top: 0.15rem;
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
        background: linear-gradient(180deg, #0f1720 0%, #0b1118 100%);
        border: 1px solid #1b2633;
        border-radius: 28px;
        padding: 1rem;
        box-shadow: 0 14px 36px rgba(0,0,0,0.34);
        margin-top: 0.2rem;
    }

    .count-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }

    .count-box {
        background: linear-gradient(180deg, #070c13 0%, #0a1017 100%);
        border: 1px solid #182232;
        border-radius: 22px;
        padding: 1.35rem 0.8rem;
        text-align: center;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.01);
    }

    .count-num {
        color: #ff7a00;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 2.9rem;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 0.42rem;
        text-shadow: 0 0 12px rgba(255, 122, 0, 0.20);
    }

    .count-lbl {
        color: #d9e1ec;
        font-size: 0.93rem;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        font-weight: 700;
    }

    .countdown-note {
        color: #aebed2;
        text-align: center;
        font-size: 0.96rem;
        margin-top: 0.78rem;
        letter-spacing: 0.03em;
    }

    .results-grid {
        display: grid;
        gap: 0.95rem;
        margin-top: 0.2rem;
    }

    .result-card {
        background: linear-gradient(180deg, #0f1720 0%, #0b1118 100%);
        border: 1px solid #1b2633;
        border-radius: 22px;
        padding: 1rem 1rem;
        box-shadow: 0 10px 28px rgba(0,0,0,0.28);
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .result-card:hover {
        transform: translateY(-2px);
        border-color: #2a3747;
        box-shadow: 0 16px 34px rgba(0,0,0,0.34);
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
        font-size: 1.1rem;
        font-weight: 800;
    }

    .result-date {
        color: #a9b8ca;
        font-size: 0.93rem;
    }

    .result-bottom {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
        margin-top: 0.7rem;
    }

    .result-score {
        color: #ffffff;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .watch-wrap {
        margin-top: 0.9rem;
    }

    .watch-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.68rem 1.05rem;
        border-radius: 999px;
        background: linear-gradient(135deg, #ff7a00, #ff9d3d);
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: 0.92rem;
        border: none;
        box-shadow: 0 8px 20px rgba(255, 122, 0, 0.18);
        transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
    }

    .watch-link:hover {
        transform: translateY(-1px);
        filter: brightness(1.04);
        box-shadow: 0 12px 24px rgba(255, 122, 0, 0.24);
        color: #ffffff !important;
        text-decoration: none !important;
    }

    .roster-heading {
        color: #ffffff;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 2rem;
        font-weight: 600;
        text-align: center;
        margin-top: 2rem;
        margin-bottom: 1.25rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        position: relative;
    }

    .roster-heading::after {
        content: "";
        display: block;
        width: 72px;
        height: 3px;
        border-radius: 999px;
        margin: 0.55rem auto 0 auto;
        background: linear-gradient(90deg, #ff7a00, #ff9d3d);
        box-shadow: 0 0 14px rgba(255,122,0,0.18);
    }

    .players-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.7rem 1.2rem;
        margin-top: 0.45rem;
    }

    .player-card {
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0.2rem 0.4rem 0.95rem 0.4rem;
        text-align: center;
    }

    .player-photo-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 1.05rem;
    }

    .player-photo {
        width: 136px;
        height: 136px;
        object-fit: cover;
        border-radius: 24px;
        border: 1px solid #243244;
        display: block;
        box-shadow: 0 12px 28px rgba(0,0,0,0.28);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .player-photo:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 16px 30px rgba(0,0,0,0.34);
    }

    .player-photo-placeholder {
        width: 136px;
        height: 136px;
        border-radius: 24px;
        border: 1px solid #243244;
        background: linear-gradient(180deg, #0d141d 0%, #111a26 100%);
        color: #ff7a00;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 1.9rem;
        font-weight: 700;
        box-shadow: 0 12px 28px rgba(0,0,0,0.28);
    }

    .player-number {
        color: #ff7a00;
        font-family: Impact, Arial Black, Arial, sans-serif;
        font-size: 1.7rem;
        font-weight: 600;
        margin-bottom: 0.22rem;
        line-height: 1;
    }

    .player-name {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 0.24rem;
    }

    .player-position {
        color: #a9b8ca;
        font-size: 0.97rem;
    }

    .empty-box {
        background: linear-gradient(180deg, #0f1720 0%, #0b1118 100%);
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
            font-size: 2.45rem;
        }

        .value {
            font-size: 1.75rem;
        }

        .count-num {
            font-size: 2.35rem;
        }

        .players-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 1.45rem 1rem;
        }

        .player-photo,
        .player-photo-placeholder {
            width: 122px;
            height: 122px;
        }

        .roster-heading {
            font-size: 1.8rem;
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
            font-size: 2.05rem;
        }

        .hero-subtitle {
            font-size: 0.9rem;
        }

        .count-grid {
            grid-template-columns: 1fr;
        }

        .count-num {
            font-size: 2.05rem;
        }

        .value {
            font-size: 1.55rem;
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
            width: 110px;
            height: 110px;
        }

        .roster-heading {
            font-size: 1.6rem;
            margin-top: 1.6rem;
            margin-bottom: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
