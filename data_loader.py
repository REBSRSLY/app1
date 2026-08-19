"""Loading and parsing of raw scouting (Data Volley) and wellness data.

The sheets in ``anonymized_matches_F.xlsx`` replicate Data Volley's "by
fundamental" export: repeated blocks of rows (Fundamental -> Ball type ->
Player) separated by delimiter rows (-1 / 0). This module normalizes
everything into "long" DataFrames that are easy to filter and plot.
"""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

import file_store as fs

# Everything is read from the files/ repository (one file per match sheet,
# one per wellness day+kind) rather than the two monolithic workbooks, so
# uploading or archiving a single file on the Data Entry page changes what
# the app shows. See file_store.py for the layout and tools/seed_files.py
# for how the original workbooks were split into it.
CACHE_DIR = fs.FILES_DIR / "_cache"

SEASON_LABEL = "Season (Total)"

# Fixed categorical order for the set type: used everywhere for consistent colors/axes.
# NOTE: these are the literal values parsed from the source Excel files (Italian in
# the raw data) — do not rename them, they're used for filtering. See PALLA_LABELS
# below for the English display mapping.
PALLA_ORDER = ["Alta", "Media", "Veloce", "Tesa", "Other", "Totale"]

FONDAMENTALI_CON_PALLA = ["Attacco", "Att dopo Ricez", "Contrattacco", "Muro"]

# Block order of the original Data Volley "by fundamental" export (see
# SCOUT_COLS / _parse_scout_sheet below) -- the canonical row order for any
# chart/table that breaks a player's stats down by fundamental, so they
# always list in the same order instead of shuffling with the data (e.g.
# sorted by mean/median).
FONDAMENTALE_ORDER = [
    "Battuta", "Ricezione", "Attacco", "Att dopo Ricez", "Contrattacco",
    "Muro", "Difesa", "Free ball", "Alzata",
]

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

# Short acronyms for the same fundamentals -- used where full names (esp.
# "Attack after Reception") would crowd a tight axis, e.g. the Players
# page's per-fundamental Efficiency chart.
FONDAMENTALE_ABBR = {
    "Battuta": "SRV",
    "Ricezione": "REC",
    "Attacco": "ATT",
    "Att dopo Ricez": "AAR",
    "Contrattacco": "CTR",
    "Muro": "BLK",
    "Difesa": "DIG",
    "Free ball": "FB",
    "Alzata": "SET",
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
            ("/", "Slash", "Serve that clips the net cord before landing in bounds -- a marginal, awkward action, distinct from a clean net/out fault."),
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
            ("/", "Slash", "Very poor reception that goes straight back into the opposing court along the net."),
            ("-", "Poor", "Reception far from the net or imprecise."),
            ("!", "Fair", "Average reception: the setter has to run but the ball is playable."),
            ("+", "Good", "Positive reception that allows multiple attack choices."),
            ("#", "Perfect", 'Reception perfect "on target" to the setter.'),
        ],
    },
    "Attacco": {
        "perfetto": "Point",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Attack sent straight out or into the net."),
            ("/", "Slash", "Attack blocked straight back for the opponent's point (a stuffed block, as opposed to a hitting error)."),
            ("-", "Poor", "Attack blocked or dug by the opponent, who keeps a clear advantage."),
            ("!", "Neutral", "Attack dug by the opposing defense (ball dug and replayed)."),
            ("+", "Good", "Attack that puts the opposing defense in trouble without scoring outright."),
            ("#", "Point", "Winning attack that lands the ball or forces a hitting error."),
        ],
    },
    "Muro": {
        "perfetto": "Block point",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Blocking error (e.g. net touch or invasion)."),
            ("/", "Slash", "Block touch that fails to stop the attack -- the ball still lands for the opponent's point."),
            ("-", "Invasion / negative touch", "Block that touches the ball but deflects it in the opponent's favor."),
            ("!", "Neutral", "Containment touch: the block slows the ball down and the team can dig it."),
            ("+", "Good", "Block touch that puts the ball in an easy position for the defense, without scoring outright."),
            ("#", "Block point", "Winning block that sends the ball straight down into the opposing court."),
        ],
    },
    "Difesa": {
        "perfetto": "Perfect dig",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Failed dig (the ball hits the floor or flies off with no control)."),
            ("/", "Slash", "Dig that deflects awkwardly off an unexpected touch, landing just out of bounds."),
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
            ("/", "Slash", "Free ball that clips the net before crossing over -- awkward, but still in play."),
            ("-", "Poor", "Free ball played with an imprecise pass."),
            ("!", "Neutral", "Free ball kept in play, but with no real advantage gained."),
            ("+", "Good", "Free ball delivered cleanly to the setter."),
            ("#", "Perfect", "Free ball delivered perfectly to the setter."),
        ],
    },
    "Alzata": {
        "perfetto": "Perfect set",
        "errore": "Error",
        "legenda": [
            ("=", "Error", "Setting fault (e.g. double contact, held ball) or set completely off target."),
            ("/", "Slash", "Set that grazes the net on its way to the hitter -- awkward, but the point continues."),
            ("-", "Poor", "Imprecise set that puts the hitter in real trouble."),
            ("!", "Neutral", "Average set, playable but not in an ideal position."),
            ("+", "Good", "Good set that gives the hitter a clear advantage without being perfect."),
            ("#", "Perfect", "Perfect set."),
        ],
    },
}
GLOSSARIO["Att dopo Ricez"] = GLOSSARIO["Attacco"]
GLOSSARIO["Contrattacco"] = GLOSSARIO["Attacco"]

# ---------------------------------------------------------------------------
# E% and Ind formulas, reverse-engineered from a season's worth of real scout
# rows (regression + exhaustive small-integer weight search against the
# actual Ind/E_pct columns -- these aren't computed by this app, they come
# straight from the Data Volley export, see SCOUT_COLS above). Verified to
# within rounding noise (E%: max 0.005 on a value stored to 2 decimals;
# Ind: exact or off-by-1 on a small share of very-low-Tot rows).
#
# "weighted": Ind is a 0-100 weighted average across all 6 grades (higher
# weight = better outcome) -- fundamentals with a genuine quality spectrum.
# "rate": Ind is just round(10 * # / Tot), a 0-10 "how often is it a
# perfect" rate -- fundamentals where only the best outcome is tracked.
# ---------------------------------------------------------------------------
FORMULE = {
    "Battuta": {
        "e_pct": "(# − =) / Tot",
        "ind": "(100·# + 71·/ + 46·+ + 39·! + 33·−) / Tot",
        "ind_kind": "weighted",
    },
    "Ricezione": {
        "e_pct": "(# + + − / − =) / Tot",
        "ind": "(71·# + 67·+ + 61·! + 54·− + 29·/) / Tot",
        "ind_kind": "weighted",
    },
    "Attacco": {
        "e_pct": "(# − / − =) / Tot",
        "ind": "(100·# + 71·+ + 58·! + 48·−) / Tot",
        "ind_kind": "weighted",
    },
    "Muro": {
        "e_pct": "(# + + + ! − / − =) / Tot",
        "ind": "round(10 × # / Tot)",
        "ind_kind": "rate",
    },
    "Difesa": {
        "e_pct": "(# + + + !) / Tot",
        "ind": "round(10 × # / Tot)",
        "ind_kind": "rate",
    },
    "Free ball": {
        "e_pct": "(# + + − / − =) / Tot",
        "ind": "round(10 × # / Tot)",
        "ind_kind": "rate",
    },
    "Alzata": {
        "e_pct": "(# + + − / − =) / Tot",
        "ind": "round(10 × # / Tot)",
        "ind_kind": "rate",
    },
}
FORMULE["Att dopo Ricez"] = FORMULE["Attacco"]
FORMULE["Contrattacco"] = FORMULE["Attacco"]


def formula_fondamentale(fondamentale: str) -> dict:
    """E%/Ind formula info for the given fundamental (see FORMULE above)."""
    return FORMULE.get(fondamentale, {})


def perfetto_label(fondamentale: str) -> str:
    """Name of the best outcome (symbol '#') for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("perfetto", "Perfect")


def errore_label(fondamentale: str) -> str:
    """Name of the error (symbol '=') for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("errore", "Error")


def legenda_fondamentale(fondamentale: str) -> list[tuple[str, str, str]]:
    """Full legend (symbol, name, description) for the given fundamental."""
    return GLOSSARIO.get(fondamentale, {}).get("legenda", [])


# ---------------------------------------------------------------------------
# Not every player/fundamental/match has enough actions (Tot) for a rate
# built on top of it (E%, Ind, an outcome share) to mean much -- 2 attacks
# with 1 error is a 50% error rate on paper, but it isn't telling you
# anything the way 20/200 would. Every chart that turns Tot rows into a
# percentage or an average should make that visible rather than presenting
# an n=2 and an n=200 bar/dot/slice with equal visual weight.
#
# MIN_RELIABLE_N is a soft threshold, not a cutoff: nothing here hides or
# drops low-sample data (an outlier match is still real and worth seeing),
# it only fades it down so a reader's eye is drawn to the numbers backed by
# enough actions to trust, with a caption nearby spelling out why. 15 is a
# practical rule of thumb for a 6-outcome breakdown (Data Volley's own
# =/-/!/+/#//), not a statistical derivation -- low enough that a full
# match's worth of a starter's main fundamental always clears it, low
# enough that a specialist's occasional fundamental doesn't always fail it.
# ---------------------------------------------------------------------------
MIN_RELIABLE_N = 15


def reliability_alpha(n, floor: float = 0.35, min_n: int = MIN_RELIABLE_N):
    """Opacity for a bar/marker/slice built on `n` actions: ramps linearly
    from `floor` at n=0 up to fully opaque at min_n and stays there past
    it, so a chart's most-trustworthy numbers read as its most visually
    prominent ones. `n` a plain number returns a float; a pandas Series
    returns a Series on the same index, ready for direct column/marker
    assignment."""
    if isinstance(n, pd.Series):
        alpha = (floor + (1.0 - floor) * (n.astype(float) / min_n)).clip(lower=floor, upper=1.0)
        return alpha.fillna(floor)
    alpha = floor + (1.0 - floor) * (float(n) / min_n) if pd.notna(n) else floor
    return max(floor, min(1.0, alpha))


def is_low_sample(n) -> bool:
    """True when `n` actions are too few for a rate built on them to be
    read with confidence -- see MIN_RELIABLE_N."""
    return pd.notna(n) and n < MIN_RELIABLE_N


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


def parse_scout_sheet(df: pd.DataFrame, match_label: str) -> list[dict]:
    """Public entry point to _parse_scout_sheet, for external callers (the
    Data Entry upload flow) that need to parse an uploaded sheet with the
    exact same logic used for the app's own bundled matches file."""
    return _parse_scout_sheet(df, match_label)


def source_signature() -> str:
    """Fingerprint of every source file (path + mtime + size).

    Used as the cache key for all loaders below, so adding or archiving a
    single file on the Data Entry page invalidates exactly what it should
    -- without it, st.cache_data would happily keep serving data from
    files that are no longer there.
    """
    parts: list[str] = []
    if fs.FILES_DIR.exists():
        for path in sorted(fs.FILES_DIR.rglob("*.xlsx")):
            if fs.ARCHIVE_DIR in path.parents or CACHE_DIR in path.parents:
                continue
            stat = path.stat()
            parts.append(f"{path.as_posix()}:{stat.st_mtime_ns}:{stat.st_size}")
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()


def _disk_cached(name: str, signature: str, build) -> pd.DataFrame:
    """Reading ~600 small .xlsx files takes ~40s; a parquet round-trip of
    the combined result takes well under a second. st.cache_data alone
    only helps within a running process, so the same work would be repaid
    on every cold start -- this keeps the combined frame on disk too,
    rebuilt only when the signature says the files actually changed.

    Cache problems are never fatal: on any failure it just rebuilds.
    """
    frame_path = CACHE_DIR / f"{name}.parquet"
    sig_path = CACHE_DIR / f"{name}.sig"
    try:
        if frame_path.exists() and sig_path.exists() and sig_path.read_text() == signature:
            return pd.read_parquet(frame_path)
    except Exception:
        pass

    df = build()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(frame_path, index=False)
        sig_path.write_text(signature)
    except Exception:
        pass
    return df


@st.cache_data(show_spinner="Loading roster...")
def _load_anagrafica(signature: str) -> pd.DataFrame:
    if not fs.ANAGRAFICA_FILE.exists():
        return pd.DataFrame(columns=["Atleta", "Ruolo", "Squadra", "Unnamed: 3"])
    return pd.read_excel(fs.ANAGRAFICA_FILE)


@st.cache_data(show_spinner="Loading scouting data...")
def load_player_names() -> dict[str, str]:
    """Map player code -> real name, women's A1 team only."""
    an = _load_anagrafica(source_signature())
    f = an[an["Squadra"] == "A1F"].copy()
    f["code"] = f["Atleta"].str.replace("player ", "", regex=False).str.strip()
    names = dict(zip(f["code"], f["Unnamed: 3"]))
    names["UNKNOWN"] = "Unknown"
    return names


# Display-only English labels for the raw (Italian) role values below.
ROLE_LABELS = {
    "Palleggio": "Setter",
    "Opposto": "Opposite",
    "Centro": "Middle Blocker",
    "Banda": "Outside Hitter",
    "Libero": "Libero",
}


@st.cache_data(show_spinner="Loading scouting data...")
def load_player_roles() -> dict[str, str]:
    """Map player code -> role (Italian, from Anagrafica), women's A1 team only.

    Covers all 15 players (unlike roster.py, which only has standalone
    entries for 13 — Heyrman and Daalderop appear there only as another
    player's "alt", with no role of their own).
    """
    an = _load_anagrafica(source_signature())
    f = an[an["Squadra"] == "A1F"].copy()
    f["code"] = f["Atleta"].str.replace("player ", "", regex=False).str.strip()
    return dict(zip(f["code"], f["Ruolo"]))


# Fundamentals whose "Perfect" (#) outcome is an actual scored point (serve
# ace, every attack variant, block point) -- as opposed to e.g. a perfect
# reception or dig, which don't put a point on the board by themselves.
POINT_FONDAMENTALI = ["Battuta", "Attacco", "Att dopo Ricez", "Contrattacco", "Muro"]


@st.cache_data(show_spinner="Loading scouting data...")
def load_player_stats() -> pd.DataFrame:
    """Per-player season totals: points scored and matches played.

    Indexed by player_name (the same short name used everywhere else, e.g.
    "Egonu"). Points come from the season-aggregate sheet (summed once, not
    re-derived from every match sheet, to avoid double-counting). Matches
    played = number of distinct match sheets the player appears in at all
    (any fundamental), excluding the season-aggregate sheet itself.
    """
    scout = load_scout_data()

    season = scout[(scout["match"] == SEASON_LABEL) & (scout["palla"] == "Totale") & (~scout["is_team"])]
    points = (
        season[season["fondamentale"].isin(POINT_FONDAMENTALI)]
        .groupby("player_code")["Perfect"].sum()
    )

    per_match = scout[(scout["match"] != SEASON_LABEL) & (scout["palla"] == "Totale") & (~scout["is_team"])]
    appearances = per_match.groupby("player_code")["match"].nunique()

    df = pd.DataFrame({"points": points, "appearances": appearances}).fillna(0)
    df["points"] = df["points"].astype(int)
    df["appearances"] = df["appearances"].astype(int)
    df["player_name"] = df.index.map(load_player_names())
    return df.set_index("player_name")


def _build_scout_frame() -> pd.DataFrame:
    """Parse every scout file across every season into one long frame.

    A match file's label is derived from its filename rather than stored
    inside it, so it stays the "23-10-08" key the calendar and every
    filter already match on.
    """
    all_rows: list[dict] = []
    for season in fs.seasons_on_disk():
        for entry in fs.list_scout(season):
            label = SEASON_LABEL if entry["kind"] == "season_total" else fs.date_to_sheet_label(entry["date"])
            raw = pd.read_excel(entry["path"], header=None)
            all_rows.extend(_parse_scout_sheet(raw, label))

    if not all_rows:
        return pd.DataFrame(columns=["fondamentale", "palla", "player_code", "is_team", "match", *NUMERIC_COLS])

    data = pd.DataFrame(all_rows)
    data[NUMERIC_COLS] = data[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    return data


@st.cache_data(show_spinner="Loading scouting data...")
def _load_scout_cached(signature: str) -> pd.DataFrame:
    return _disk_cached("scout", signature, _build_scout_frame)


def load_scout_data() -> pd.DataFrame:
    """Load and normalize all scout files (season totals + every match)."""
    data = _load_scout_cached(source_signature()).copy()
    if data.empty:
        return data

    names = load_player_names()
    data["player_name"] = data["player_code"].map(names)
    data.loc[data["is_team"], "player_name"] = "Team"

    # Applied here rather than before the parquet round-trip: the category
    # order is display metadata, not data worth persisting.
    data["palla"] = pd.Categorical(data["palla"], categories=PALLA_ORDER, ordered=True)
    return data


@st.cache_data(show_spinner="Loading match calendar...")
def load_match_list() -> list[str]:
    """Match dates across every season, most recent first."""
    dates = [
        fs.date_to_sheet_label(entry["date"])
        for season in fs.seasons_on_disk()
        for entry in fs.list_scout(season)
        if entry["kind"] == "match"
    ]
    return sorted(dates, reverse=True)


def _build_wellness_frame(kind: str) -> pd.DataFrame:
    """One day-file per row-set: concatenated back into the single frame
    the rest of the app expects."""
    frames = [
        pd.read_excel(entry["path"])
        for season in fs.seasons_on_disk()
        for entry in fs.list_wellness(season)
        if entry["kind"] == kind
    ]
    if not frames:
        return pd.DataFrame(columns=["Atleta", "Data"])
    out = pd.concat(frames, ignore_index=True)
    out["Data"] = pd.to_datetime(out["Data"], errors="coerce")
    return out.sort_values("Data").reset_index(drop=True)


@st.cache_data(show_spinner="Loading wellness data...")
def _load_wellness_cached(signature: str, kind: str) -> pd.DataFrame:
    return _disk_cached(f"wellness_{kind}", signature, lambda: _build_wellness_frame(kind))


def load_wellness_data() -> dict[str, pd.DataFrame]:
    """The women's team wellness/RPE/jump data, with real player names."""
    names = load_player_names()
    signature = source_signature()

    out = {}
    for key, kind in (("rpe", "rpe"), ("wellness", "tqr"), ("salti", "jumps")):
        d = _load_wellness_cached(signature, kind).copy()
        if "Atleta" in d.columns:
            d["player_code"] = d["Atleta"].astype(str).str.replace("player ", "", regex=False).str.strip()
            d["player_name"] = d["player_code"].map(names)
        out[key] = d
    return out
