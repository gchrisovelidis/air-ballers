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
TEAM_SUBTITLE = "2025–26 Season"
LEAGUE_NAME = "Thessaloniki Amateur League"
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
        + "–"
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


def get_season_record(results_df: pd.DataFrame):
    if results_df.empty:
        return {"wins": 0, "losses": 0}
    wins = (results_df["result"] == "W").sum()
    losses = (results_df["result"] == "L").sum()
    return {"wins": int(wins), "losses": int(losses)}


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

next_game    = parse_next_game(next_game_df)
results_df   = enrich_results(results_df)
players_df   = enrich_players(players_df)
last_result  = get_last_result(results_df)
streak       = get_streak(results_df)
record       = get_season_record(results_df)

# -------------------------------------------------
# Global CSS
# -------------------------------------------------
st.markdown(
    """
    <style>
    /* ---- Google Fonts ---- */
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,400;0,600;0,700;0,800;0,900;1,700;1,800&family=Barlow:wght@400;500;600&display=swap');

    /* ---- Reset & base ---- */
    #MainMenu  { visibility: hidden; }
    header     { visibility: hidden; }
    footer     { visibility: hidden; }

    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {
        background: #000000 !important;
        color: #ffffff !important;
        font-family: 'Barlow', sans-serif !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: #000000 !important;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 1rem;
        padding-bottom: 3rem;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
    }

    /* ---- HERO ---- */
    .hero-wrap {
        text-align: center;
        padding: 2.5rem 0 1.5rem;
    }

    .hero-logo-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 1.3rem;
    }

    .hero-logo {
        width: 120px;
        max-width: 60vw;
        border-radius: 24px;
        display: block;
        box-shadow: 0 0 60px rgba(255,92,0,0.35), 0 0 120px rgba(255,92,0,0.12);
    }

    .hero-eyebrow {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #FF5C00;
        margin-bottom: 0.45rem;
    }

    .hero-title {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: clamp(3.2rem, 9vw, 6rem);
        font-weight: 900;
        line-height: 0.92;
        letter-spacing: -0.01em;
        text-transform: uppercase;
        color: #ffffff;
        margin-bottom: 0.6rem;
    }

    .hero-title em {
        color: #FF5C00;
        font-style: italic;
    }

    .hero-divider {
        width: 44px;
        height: 2px;
        background: #FF5C00;
        margin: 0 auto 0.7rem;
        border-radius: 2px;
    }

    .hero-sub {
        font-size: 0.85rem;
        font-weight: 500;
        color: #888888;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.9rem;
    }

    .record-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: #111111;
        border: 1px solid rgba(255,255,255,0.13);
        border-radius: 999px;
        padding: 0.28rem 1rem;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #bbbbbb;
    }

    .record-badge .rw { color: #22C55E; }
    .record-badge .rl { color: #EF4444; }

    /* ---- SECTION HEADING ---- */
    .section-head {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 2.8rem 0 1.1rem;
    }

    .section-head h2 {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.85rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #ffffff;
        line-height: 1;
        white-space: nowrap;
    }

    .section-head h2 em {
        color: #FF5C00;
        font-style: italic;
    }

    .section-line {
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.07);
    }

    /* ---- TOP CARDS ---- */
    .cards-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.9rem;
        margin-top: 2rem;
    }

    .card {
        background: #111111;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 1.25rem 1.15rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.22s, transform 0.22s;
    }

    .card:hover {
        border-color: rgba(255,255,255,0.13);
        transform: translateY(-3px);
    }

    .card::after {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at top left, rgba(255,92,0,0.06) 0%, transparent 65%);
        pointer-events: none;
    }

    .card-label {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #888888;
        margin-bottom: 0.65rem;
    }

    .card-value {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        line-height: 1.1;
        color: #ffffff;
        margin-bottom: 0.35rem;
    }

    .card-sub {
        font-size: 0.84rem;
        color: #bbbbbb;
        line-height: 1.5;
    }

    .pill {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-top: 0.45rem;
    }

    .pill-win  { background: rgba(34,197,94,0.12);  color: #22C55E; border: 1px solid rgba(34,197,94,0.22); }
    .pill-loss { background: rgba(239,68,68,0.12);  color: #EF4444; border: 1px solid rgba(239,68,68,0.22); }

    /* ---- COUNTDOWN ---- */
    .countdown-shell {
        background: #111111;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 1.7rem 1.2rem;
    }

    .count-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
        max-width: 480px;
        margin: 0 auto;
    }

    .count-box {
        background: #0a0a0a;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.4rem 0.5rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: border-color 0.22s;
    }

    .count-box:hover {
        border-color: rgba(255,92,0,0.3);
    }

    .count-box::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #FF5C00, transparent);
        opacity: 0.45;
    }

    .count-num {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 3.2rem;
        font-weight: 900;
        line-height: 1;
        color: #FF5C00;
        letter-spacing: -0.02em;
        text-shadow: 0 0 28px rgba(255,92,0,0.4);
    }

    .count-lbl {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #888888;
        margin-top: 0.3rem;
    }

    .count-tip {
        text-align: center;
        margin-top: 1rem;
        font-size: 0.85rem;
        color: #888888;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-family: 'Barlow Condensed', sans-serif;
    }

    /* ---- RESULTS ---- */
    .results-grid {
        display: grid;
        gap: 0.6rem;
    }

    .result-card {
        background: #111111;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 0.95rem 1.15rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: border-color 0.2s, transform 0.2s;
        position: relative;
        overflow: hidden;
    }

    .result-card:hover {
        border-color: rgba(255,255,255,0.13);
        transform: translateX(4px);
    }

    .result-card.rc-win  { border-left: 3px solid #22C55E; }
    .result-card.rc-loss { border-left: 3px solid #EF4444; }

    .result-badge {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.35rem;
        font-weight: 900;
        width: 2.4rem;
        text-align: center;
        flex-shrink: 0;
        letter-spacing: 0.02em;
    }

    .result-badge.rb-win  { color: #22C55E; }
    .result-badge.rb-loss { color: #EF4444; }

    .result-info { flex: 1; min-width: 0; }

    .result-opponent {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.08rem;
        font-weight: 700;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .result-date {
        font-size: 0.79rem;
        color: #888888;
        margin-top: 0.12rem;
    }

    .result-score {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.45rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.03em;
        flex-shrink: 0;
    }

    .watch-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.32rem 0.72rem;
        border-radius: 999px;
        background: #181818;
        border: 1px solid rgba(255,255,255,0.13);
        color: #bbbbbb;
        font-size: 0.76rem;
        font-weight: 700;
        text-decoration: none;
        transition: all 0.2s;
        flex-shrink: 0;
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .watch-btn:hover {
        background: rgba(255,92,0,0.1);
        border-color: rgba(255,92,0,0.35);
        color: #FF7A2B;
        text-decoration: none;
    }

    /* ---- ROSTER ---- */
    .players-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.9rem;
    }

    .player-card {
        background: #111111;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 1.2rem 0.7rem 1rem;
        text-align: center;
        transition: border-color 0.22s, transform 0.22s;
    }

    .player-card:hover {
        border-color: rgba(255,92,0,0.3);
        transform: translateY(-4px);
    }

    .player-photo-wrap {
        position: relative;
        display: inline-block;
        margin-bottom: 0.85rem;
    }

    .player-photo {
        width: 88px;
        height: 88px;
        border-radius: 50%;
        object-fit: cover;
        display: block;
        border: 2px solid rgba(255,255,255,0.13);
        background: #181818;
    }

    .player-initials {
        width: 88px;
        height: 88px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.13);
        background: #181818;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1.7rem;
        font-weight: 800;
        color: #FF5C00;
    }

    .player-num-badge {
        position: absolute;
        bottom: -3px;
        right: -3px;
        background: #000000;
        border: 1px solid rgba(255,255,255,0.13);
        color: #bbbbbb;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 0.74rem;
        font-weight: 800;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .player-card:hover .player-num-badge {
        color: #FF5C00;
        border-color: rgba(255,92,0,0.35);
    }

    .player-name {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 1rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #ffffff;
        margin-bottom: 0.18rem;
    }

    .player-pos {
        font-size: 0.76rem;
        color: #888888;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* ---- EMPTY STATE ---- */
    .empty-box {
        background: #111111;
        border: 1px dashed rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 1.2rem;
        color: #888888;
        font-size: 0.88rem;
    }

    /* ---- FOOTER ---- */
    .site-footer {
        margin-top: 4rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.07);
        text-align: center;
        font-size: 0.76rem;
        color: #555555;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 600;
    }

    /* ---- RESPONSIVE ---- */
    @media (max-width: 860px) {
        .cards-row {
            grid-template-columns: 1fr 1fr;
        }
        .players-grid {
            grid-template-columns: repeat(3, 1fr);
        }
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        .cards-row {
            grid-template-columns: 1fr;
        }
        .count-grid {
            grid-template-columns: repeat(3, 1fr);
        }
        .count-num {
            font-size: 2.4rem;
        }
        .players-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .result-score {
            font-size: 1.2rem;
        }
        .hero-title {
            font-size: 3rem;
        }
        .section-head h2 {
            font-size: 1.55rem;
        }
        .watch-btn {
            display: none;
        }
    }

    @media (max-width: 400px) {
        .players-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .count-num {
            font-size: 2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Hero
# -------------------------------------------------
logo_html = ""
if Path(LOGO_FILE).exists():
    logo_path = Path(LOGO_FILE)
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    logo_mime = get_mime_type(logo_path)
    logo_html = f'<div class="hero-logo-wrap"><img src="data:{logo_mime};base64,{logo_b64}" class="hero-logo"></div>'

record_html = ""
if record["wins"] + record["losses"] > 0:
    record_html = f"""
    <div style="margin-top:0.9rem;">
      <span class="record-badge">
        Season Record &nbsp;
        <span class="rw">{record['wins']}W</span>
        &nbsp;–&nbsp;
        <span class="rl">{record['losses']}L</span>
      </span>
    </div>
    """

st.markdown(
    f"""
    <div class="hero-wrap">
      {logo_html}
      <div class="hero-eyebrow">{esc(LEAGUE_NAME)}</div>
      <div class="hero-title">Air <em>Ballers</em></div>
      <div class="hero-divider"></div>
      <div class="hero-sub">{esc(TEAM_SUBTITLE)}</div>
      {record_html}
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
              <div class="card-label">Next Game</div>
              <div class="card-value">vs {esc(next_game['opponent'])}</div>
              <div class="card-sub">{esc(format_game_datetime(next_game['datetime']))}</div>
              <div class="card-sub" style="color:#888;margin-top:0.18rem">{esc(next_game['home_away'])} · {esc(next_game['venue'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="card">
              <div class="card-label">Next Game</div>
              <div class="card-value">Not set</div>
              <div class="card-sub">Update next_game.csv</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col2:
    if streak["type"] == "win":
        streak_sub  = "Team is on a hot run 🔥"
        streak_color = "#22C55E"
    elif streak["type"] == "loss":
        streak_sub  = "Time to bounce back"
        streak_color = "#EF4444"
    else:
        streak_sub  = "No results yet"
        streak_color = "#ffffff"

    st.markdown(
        f"""
        <div class="card">
          <div class="card-label">{esc(streak['label'])}</div>
          <div class="card-value" style="color:{streak_color}">{esc(streak['value'])}</div>
          <div class="card-sub">{esc(streak_sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    if last_result:
        pill_class = "pill-win" if last_result["result"] == "W" else "pill-loss"
        pill_text  = "Win" if last_result["result"] == "W" else "Loss"
        st.markdown(
            f"""
            <div class="card">
              <div class="card-label">Last Result</div>
              <div class="card-value">vs {esc(last_result['opponent'])}</div>
              <span class="pill {pill_class}">{pill_text}</span>
              <div class="card-sub" style="margin-top:0.45rem">{esc(last_result['score'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="card">
              <div class="card-label">Last Result</div>
              <div class="card-value">No games yet</div>
              <div class="card-sub">Update results.csv</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------------------------------
# Countdown
# -------------------------------------------------
st.markdown(
    '<div class="section-head"><h2>Tip-off <em>Countdown</em></h2><div class="section-line"></div></div>',
    unsafe_allow_html=True,
)

if next_game:
    countdown = get_countdown(next_game["datetime"])
    if countdown:
        st.markdown(
            f"""
            <div class="countdown-shell">
              <div class="count-grid">
                <div class="count-box">
                  <div class="count-num">{countdown['days']:02d}</div>
                  <div class="count-lbl">Days</div>
                </div>
                <div class="count-box">
                  <div class="count-num">{countdown['hours']:02d}</div>
                  <div class="count-lbl">Hours</div>
                </div>
                <div class="count-box">
                  <div class="count-num">{countdown['minutes']:02d}</div>
                  <div class="count-lbl">Minutes</div>
                </div>
              </div>
              <div class="count-tip">Until tip-off vs {esc(next_game['opponent'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="empty-box">Game time has passed. Update next_game.csv with the next fixture.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="empty-box">No next game found. Update next_game.csv.</div>',
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# Previous results
# -------------------------------------------------
st.markdown(
    '<div class="section-head"><h2>Previous <em>Results</em></h2><div class="section-line"></div></div>',
    unsafe_allow_html=True,
)

if not results_df.empty:
    html = '<div class="results-grid">'
    for _, row in results_df.iterrows():
        is_win      = row["result"] == "W"
        card_cls    = "rc-win" if is_win else "rc-loss"
        badge_cls   = "rb-win" if is_win else "rb-loss"
        badge_txt   = "W" if is_win else "L"
        date_str    = row["date"].strftime("%d %b %Y")
        youtube_url = str(row.get("youtube_url", "")).strip().rstrip("&")

        watch_html = ""
        if youtube_url:
            watch_html = f'<a href="{youtube_url}" target="_blank" rel="noopener noreferrer" class="watch-btn">▶ Watch</a>'

        html += f"""
        <div class="result-card {card_cls}">
          <div class="result-badge {badge_cls}">{badge_txt}</div>
          <div class="result-info">
            <div class="result-opponent">vs {esc(row['opponent'])}</div>
            <div class="result-date">{esc(date_str)}</div>
          </div>
          <div class="result-score">{esc(row['score_display'])}</div>
          {watch_html}
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="empty-box">No previous results found. Update results.csv.</div>',
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# Players / Roster
# -------------------------------------------------
st.markdown(
    '<div class="section-head"><h2>Team <em>Roster</em></h2><div class="section-line"></div></div>',
    unsafe_allow_html=True,
)

if not players_df.empty:
    html = '<div class="players-grid">'
    for _, row in players_df.iterrows():
        photo_name = str(row.get("photo", "")).strip()
        photo_html = ""

        if photo_name:
            photo_path = IMAGES_DIR / photo_name
            if photo_path.exists():
                img_b64   = base64.b64encode(photo_path.read_bytes()).decode()
                mime_type = get_mime_type(photo_path)
                photo_html = f'<img src="data:{mime_type};base64,{img_b64}" class="player-photo">'

        if not photo_html:
            initials   = "".join([part[0] for part in str(row["name"]).split()[:2]]).upper()
            photo_html = f'<div class="player-initials">{esc(initials)}</div>'

        html += f"""
        <div class="player-card">
          <div class="player-photo-wrap">
            {photo_html}
            <div class="player-num-badge">#{esc(row['number'])}</div>
          </div>
          <div class="player-name">{esc(row['name'])}</div>
          <div class="player-pos">{esc(row['position'])}</div>
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="empty-box">No players found. Update players.csv.</div>',
        unsafe_allow_html=True,
    )

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown(
    f'<div class="site-footer">Air Ballers &nbsp;·&nbsp; Thessaloniki &nbsp;·&nbsp; {TEAM_SUBTITLE}</div>',
    unsafe_allow_html=True,
)
