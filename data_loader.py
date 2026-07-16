"""Loading and parsing of raw scouting (Data Volley) and wellness data.

The sheets in ``anonymized_matches_F.xlsx`` replicate Data Volley's "by
fundamental" export: repeated blocks of rows (Fundamental -> Ball type ->
Player) separated by delimiter rows (-1 / 0). This module normalizes
everything into "long" DataFrames that are easy to filter and plot.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

MATCHES_FILE = "anonymized_matches_F.xlsx"
WELLNESS_FILE = "anonymized_wellness_file.xlsx"

SEASON_LABEL = "Season (Total)"

# Fixed categorical order for the set type: used everywhere for consistent colors/axes.
# NOTE: these are the literal values parsed from the source Excel files (Italian in
# the raw data) — do not rename them, they're used for filtering. See PALLA_LABELS
# below for the English display mapping.
PALLA_ORDER = ["Alta", "Media", "Veloce", "Tesa", "Other", "Totale"]

FONDAMENTALI_CON_PALLA = ["Attacco", "Att dopo Ricez", "Contrattacco", "Muro"]

# Display-only English labels for the raw (Italian) categorical values above.
# Keep the raw values untouched anywhere they're used for filtering/matching;
# apply these mappings only when rendering text, chart axes, or legends.
FONDAMENTALE_LABELS = {
    "Battuta": "Serve",
    "Ricezione": "Reception",
    "Attacco": "Attack",
    "Att dopo Ricez": "Attack after Reception",
    "Contrattacco": "Counter-attack",
    "Muro": "Block",
    "Difesa": "Dig",
    "Free ball": "Free Ball",
    "Alzata": "Set",
}

PALLA_LABELS = {
    "Alta": "High",
    "Media": "Medium",
    "Veloce": "Quick",
    "Tesa": "Shoot",
    "Other": "Other",
    "Totale": "Total",
}

# Excel column (0-indexed) -> field name, replicating the header at row 2 of
# every scout sheet ('Fondam.', 'Palla', 'Giocatore', 'P', 'Set', Ind, *E%, Tot,
# =, %, BP, pC, /, %, BP, pC, -, %, !, %, +, %, #, %, BP, pC).
# Field names follow the Data Volley SYMBOL (not its meaning, which is specific
# to each fundamental — see GLOSSARY below and "istruzioni simbologia.txt").
SCOUT_COLS = {
    3: "P",
    4: "Set",
    6: "Ind",
    7: "E_pct",
    9: "Tot",
    11: "Err",  # "="
    12: "Err_pct",
    13: "Err_BP",
    14: "Err_pC",
    16: "Slash",  # "/"
    17: "Slash_pct",
    18: "Slash_BP",
    19: "Slash_pC",
    21: "Neg",  # "-"
    22: "Neg_pct",
    24: "Neutral",  # "!"
    25: "Neutral_pct",
    27: "Pos",  # "+"
    28: "Pos_pct",
    30: "Perfect",  # "#"
    31: "Perfect_pct",
    32: "Perfect_BP",
    33: "Perfect_pC",
}

NUMERIC_COLS = list(SCOUT_COLS.values())

# ---------------------------------------------------------------------------
# Scouting symbol glossary, from "istruzioni simbologia.txt".
# The same symbols (=, -, !, +, #, /) mean different things per fundamental:
# this maps each fundamental to the correct name for its two "headline" grades
# (# = best outcome, = = error) plus the full legend for tooltips/captions.
# Dict KEYS stay Italian (they must match the raw `fondamentale` values parsed
# from Excel); dict VALUES are pure display text and are in English.
# "Att dopo Ricez" and "Contrattacco" are attack variants and share Attacco's
# grading table.
# ---------------------------------------------------------------------------
GLOSSARIO = {
    "Battuta": {
        "perfetto": "Ace",
        "errore": "Error (net/out)",
        "legenda": [
            ("=", "Error", "Serve into the net or out."),
            ("-", "Poor", "Easy serve that allows a perfect reception."),
            ("!", "Neutral", "Normal serve (e.g. float) that keeps play balanced."),
            ("+", "Good", "Tricky serve that puts the opposing reception in trouble."),
            ("#", "Ace", "Direct point on serve."),
        ],
    },
    "Ricezione": {
        "perfetto": "Perfect reception",
        "errore": "Error / Ace conceded",
        "legenda": [
            ("=", "Error / Ace conceded", "The reception fails and the opponent scores."),
            ("-", "Poor", "Reception far from the net or imprecise."),
            ("!", "Fair", "Average reception: the setter has to run but the ball is playable."),
            ("+", "Good", "Positive reception that allows multiple attack choices."),
            ("#", "Perfect", 'Reception perfect "on target" to the setter.'),
            ("/", "Slash", "Very poor reception that goes straight back into the opposing court along the net."),
        ],
    },
    "Attacco": {
        "perfetto": "Point",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Attack sent straight out or into the net."),
            ("!", "Neutral", "Attack dug by the opposing defense (ball dug and replayed)."),
            ("#", "Point", "Winning attack that lands the ball or forces a hitting error."),
        ],
    },
    "Muro": {
        "perfetto": "Block point",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Blocking error (e.g. net touch or invasion)."),
            ("-", "Invasion / negative touch", "Block that touches the ball but deflects it in the opponent's favor."),
            ("!", "Neutral", "Containment touch: the block slows the ball down and the team can dig it."),
            ("#", "Block point", "Winning block that sends the ball straight down into the opposing court."),
        ],
    },
    "Difesa": {
        "perfetto": "Perfect dig",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Failed dig (the ball hits the floor or flies off with no control)."),
            ("-", "Poor", "Flawed dig that doesn't allow a clean rebuild."),
            ("!", "Neutral", "Dig that keeps the ball high and playable, even if off-target."),
            ("+", "Good", "Great dig that lets the setter build a counter-attack."),
            ("#", "Perfect", "Perfect dig placed directly in the setter's zone."),
        ],
    },
    "Free ball": {
        "perfetto": "Perfect",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Blatant error on an easy ball (e.g. ball dropped due to miscommunication)."),
            ("+ / #", "Good / Perfect", "Free ball delivered perfectly to the setter."),
        ],
    },
    "Alzata": {
        "perfetto": "Perfect set",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Setting fault (e.g. double contact, held ball) or set completely off target."),
            ("-", "Poor", "Imprecise set that puts the hitter in real trouble."),
            ("#", "Perfect", "Perfect set."),
        ],
    },
}
GLOSSARIO["Att dopo Ricez"] = GLOSSARIO["Attacco"]
GLOSSARIO["Contrattacco"] = GLOSSARIO["Attacco"]


def perfetto_label(fondamentale: str) -> str:
    """Name of the best outcome (symbol '#') for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("perfetto", "Perfect")


def errore_label(fondamentale: str) -> str:
    """Name of the error (symbol '=') for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("errore", "Error")


def legenda_fondamentale(fondamentale: str) -> list[tuple[str, str, str]]:
    """Full legend (symbol, name, description) for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("legenda", [])


def _parse_scout_sheet(df: pd.DataFrame, match_label: str) -> list[dict]:
    """Turn a raw scout sheet (header=None) into 'long' rows."""
    rows = []
    fondamentale = None
    palla = None

    for i in range(len(df)):
        c0 = df.iat[i, 0]
        c1 = df.iat[i, 1]
        c2 = df.iat[i, 2]

        if isinstance(c0, str) and c0 != "Fondam.":
            fondamentale = c0
            palla = None  # new fundamental -> restart from the 'Total' block
        elif c0 in (-1, 0) and pd.isna(c2):
            continue  # delimiter row between blocks

        if fondamentale is None or pd.isna(c2):
            continue

        if pd.notna(c1):
            palla = c1

        if c2 == "Squadra":
            player_code = None
            is_team = True
        elif isinstance(c2, str) and c2.startswith("player "):
            player_code = c2.replace("player ", "").strip()
            is_team = False
        elif c2 == "UNKNOWN":
            player_code = "UNKNOWN"
            is_team = False
        else:
            continue

        row = {
            "match": match_label,
            "fondamentale": fondamentale,
            "palla": palla if palla is not None else "Totale",
            "is_team": is_team,
            "player_code": player_code,
        }
        for col_idx, name in SCOUT_COLS.items():
            row[name] = df.iat[i, col_idx]
        rows.append(row)
    return rows


@st.cache_data(show_spinner="Loading scouting data...")
def load_player_names() -> dict[str, str]:
    """Map player code -> real name, women's A1 team only."""
    an = pd.read_excel(WELLNESS_FILE, sheet_name="Anagrafica")
    f = an[an["Squadra"] == "A1F"].copy()
    f["code"] = f["Atleta"].str.replace("player ", "", regex=False).str.strip()
    names = dict(zip(f["code"], f["Unnamed: 3"]))
    names["UNKNOWN"] = "Unknown"
    return names


@st.cache_data(show_spinner="Loading scouting data...")
def load_scout_data() -> pd.DataFrame:
    """Load and normalize all scout sheets (season total + every match)."""
    xl = pd.ExcelFile(MATCHES_FILE)
    all_rows: list[dict] = []

    for sheet in xl.sheet_names:
        label = SEASON_LABEL if sheet == "TOTALE 23-24" else sheet
        raw = xl.parse(sheet, header=None)
        all_rows.extend(_parse_scout_sheet(raw, label))

    data = pd.DataFrame(all_rows)
    data[NUMERIC_COLS] = data[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")

    names = load_player_names()
    data["player_name"] = data["player_code"].map(names)
    data.loc[data["is_team"], "player_name"] = "Team"

    data["palla"] = pd.Categorical(data["palla"], categories=PALLA_ORDER, ordered=True)
    return data


@st.cache_data(show_spinner="Loading match calendar...")
def load_match_list() -> list[str]:
    """List of match dates (season total excluded), reverse chronological order."""
    xl = pd.ExcelFile(MATCHES_FILE)
    dates = [s for s in xl.sheet_names if s != "TOTALE 23-24"]
    return sorted(dates, reverse=True)


@st.cache_data(show_spinner="Loading wellness data...")
def load_wellness_data() -> dict[str, pd.DataFrame]:
    """Load the women's team wellness/RPE/jump sheets with real names."""
    names = load_player_names()

    rpe = pd.read_excel(WELLNESS_FILE, sheet_name="Rpe TL F")
    wellness = pd.read_excel(WELLNESS_FILE, sheet_name="Wellness F")
    salti = pd.read_excel(WELLNESS_FILE, sheet_name="SALTI_F")

    for d in (rpe, wellness, salti):
        d["player_code"] = d["Atleta"].str.replace("player ", "", regex=False).str.strip()
        d["player_name"] = d["player_code"].map(names)

    return {"rpe": rpe, "wellness": wellness, "salti": salti}
