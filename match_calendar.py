"""Match calendar: the 2023/24 season's built-in history, plus whatever's
been entered for later seasons through the Data Entry page.

The 2023/24 list below is sourced from the public season record (Serie A1,
Coppa Italia, Supercoppa, CEV Champions League, playoffs) and cross-checked
date-by-date against the 45 match sheets in anonymized_matches_F.xlsx —
every date lines up exactly. Score is always written as Milano-Opponent
sets. A season with no built-in record of its own (2024/25 onward) starts
empty and is filled in entirely from file_store's matches.json, one match
at a time, as the staff add them -- see matches_for_season() below, which
is what every page actually reads instead of MATCHES/SEASON_MATCHES
directly.
"""

import file_store as fs

MATCHES = [
    {"date": "23-10-08", "competition": "Serie A1", "round": "andata", "opponent": "Busto Arsizio", "home": True, "score": "3-0"},
    {"date": "23-10-14", "competition": "Serie A1", "round": "andata", "opponent": "Trentino", "home": False, "score": "3-1"},
    {"date": "23-10-22", "competition": "Serie A1", "round": "andata", "opponent": "Scandicci", "home": True, "score": "3-2"},
    {"date": "23-10-28", "competition": "Supercoppa Italiana", "round": "finale", "opponent": "Conegliano", "home": False, "score": "1-3"},
    {"date": "23-11-01", "competition": "Serie A1", "round": "andata", "opponent": "Bergamo", "home": False, "score": "3-1"},
    {"date": "23-11-05", "competition": "Serie A1", "round": "andata", "opponent": "Conegliano", "home": True, "score": "1-3"},
    {"date": "23-11-09", "competition": "Champions League", "round": "girone", "opponent": "Jedinstvo Stara Pazova", "home": True, "score": "3-0"},
    {"date": "23-11-12", "competition": "Serie A1", "round": "andata", "opponent": "Novara", "home": False, "score": "3-1"},
    {"date": "23-11-14", "competition": "Champions League", "round": "girone", "opponent": "Mulhouse", "home": False, "score": "3-0"},
    {"date": "23-11-19", "competition": "Serie A1", "round": "andata", "opponent": "Pinerolo", "home": True, "score": "3-0"},
    {"date": "23-11-22", "competition": "Serie A1", "round": "andata", "opponent": "Chieri", "home": True, "score": "3-0"},
    {"date": "23-11-26", "competition": "Serie A1", "round": "andata", "opponent": "Roma", "home": False, "score": "3-0"},
    {"date": "23-11-29", "competition": "Champions League", "round": "girone", "opponent": "VakıfBank", "home": False, "score": "3-0"},
    {"date": "23-12-03", "competition": "Serie A1", "round": "andata", "opponent": "Casalmaggiore", "home": True, "score": "3-2"},
    {"date": "23-12-06", "competition": "Champions League", "round": "girone", "opponent": "Mulhouse", "home": True, "score": "3-1"},
    {"date": "23-12-10", "competition": "Serie A1", "round": "andata", "opponent": "Cuneo", "home": False, "score": "3-0"},
    {"date": "23-12-17", "competition": "Serie A1", "round": "andata", "opponent": "Firenze", "home": False, "score": "3-0"},
    {"date": "23-12-23", "competition": "Serie A1", "round": "andata", "opponent": "Megavolley", "home": True, "score": "3-0"},
    {"date": "23-12-26", "competition": "Serie A1", "round": "ritorno", "opponent": "Busto Arsizio", "home": False, "score": "3-1"},
    {"date": "24-01-07", "competition": "Serie A1", "round": "ritorno", "opponent": "Trentino", "home": True, "score": "3-0"},
    {"date": "24-01-10", "competition": "Champions League", "round": "girone", "opponent": "Jedinstvo Stara Pazova", "home": False, "score": "3-0"},
    {"date": "24-01-13", "competition": "Serie A1", "round": "ritorno", "opponent": "Scandicci", "home": False, "score": "3-0"},
    {"date": "24-01-16", "competition": "Champions League", "round": "girone", "opponent": "VakıfBank", "home": True, "score": "2-3"},
    {"date": "24-01-21", "competition": "Serie A1", "round": "ritorno", "opponent": "Chieri", "home": False, "score": "3-2"},
    {"date": "24-01-24", "competition": "Coppa Italia", "round": "quarti", "opponent": "Roma", "home": True, "score": "3-0"},
    {"date": "24-01-28", "competition": "Serie A1", "round": "ritorno", "opponent": "Bergamo", "home": True, "score": "3-1"},
    {"date": "24-02-04", "competition": "Serie A1", "round": "ritorno", "opponent": "Conegliano", "home": False, "score": "0-3"},
    {"date": "24-02-10", "competition": "Serie A1", "round": "ritorno", "opponent": "Novara", "home": True, "score": "2-3"},
    {"date": "24-02-17", "competition": "Coppa Italia", "round": "semifinale", "opponent": "Scandicci", "home": True, "score": "3-2"},
    {"date": "24-02-18", "competition": "Coppa Italia", "round": "finale", "opponent": "Conegliano", "home": False, "score": "2-3"},
    {"date": "24-02-20", "competition": "Champions League", "round": "quarti andata", "opponent": "ŁKS Łódź", "home": False, "score": "3-1"},
    {"date": "24-02-25", "competition": "Serie A1", "round": "ritorno", "opponent": "Pinerolo", "home": False, "score": "3-2"},
    {"date": "24-02-29", "competition": "Champions League", "round": "quarti ritorno", "opponent": "ŁKS Łódź", "home": True, "score": "3-0"},
    {"date": "24-03-03", "competition": "Serie A1", "round": "ritorno", "opponent": "Roma", "home": True, "score": "3-2"},
    {"date": "24-03-06", "competition": "Serie A1", "round": "ritorno", "opponent": "Casalmaggiore", "home": False, "score": "2-3"},
    {"date": "24-03-09", "competition": "Serie A1", "round": "ritorno", "opponent": "Cuneo", "home": True, "score": "3-0"},
    {"date": "24-03-12", "competition": "Champions League", "round": "semifinale andata", "opponent": "Fenerbahçe", "home": True, "score": "3-0"},
    {"date": "24-03-16", "competition": "Serie A1", "round": "ritorno", "opponent": "Firenze", "home": True, "score": "3-1"},
    {"date": "24-03-19", "competition": "Champions League", "round": "semifinale ritorno", "opponent": "Fenerbahçe", "home": False, "score": "1-3"},
    {"date": "24-03-24", "competition": "Serie A1", "round": "ritorno", "opponent": "Megavolley", "home": False, "score": "0-3"},
    {"date": "24-03-27", "competition": "Playoff scudetto", "round": "quarti gara 1", "opponent": "Pinerolo", "home": True, "score": "3-2"},
    {"date": "24-03-31", "competition": "Playoff scudetto", "round": "quarti gara 2", "opponent": "Pinerolo", "home": False, "score": "3-1"},
    {"date": "24-04-06", "competition": "Playoff scudetto", "round": "semifinale gara 1", "opponent": "Scandicci", "home": False, "score": "0-3"},
    {"date": "24-04-10", "competition": "Playoff scudetto", "round": "semifinale gara 2", "opponent": "Scandicci", "home": True, "score": "0-3"},
    {"date": "24-05-05", "competition": "Champions League", "round": "finale", "opponent": "Conegliano", "home": False, "score": "2-3"},
]

# ---------------------------------------------------------------------------
# Competition labels & colors, used by the calendar legend/chips and by the
# Matches page. "Jump session" isn't a real competition -- it's the calendar
# overlay for SALTI_F monitoring days -- kept here so all calendar event
# colors live in one place.
# ---------------------------------------------------------------------------
COMPETITIONS = {
    "Serie A1": {"label": "Championship match", "color": "#4C78A8"},
    "Playoff scudetto": {"label": "Championship playoffs", "color": "#E45756"},
    "Coppa Italia": {"label": "Cup match (Coppa Italia)", "color": "#F58518"},
    "Champions League": {"label": "Champions League", "color": "#54A24B"},
    "Supercoppa Italiana": {"label": "Supercoppa", "color": "#B279A2"},
    "Jump session": {"label": "Jump session", "color": "#9D9D9D"},
}

# Display order for the per-competition boxes: main league first, then the
# knockout competitions in roughly chronological/importance order.
COMPETITION_ORDER = ["Serie A1", "Playoff scudetto", "Coppa Italia", "Champions League", "Supercoppa Italiana"]

# Italian round tokens (as stored on each match) -> clean English box labels.
ROUND_LABELS = {
    "andata": "Round 1", "ritorno": "Round 2",
    "girone": "Group stage",
    "quarti": "Quarterfinal",
    "quarti andata": "QF · Leg 1", "quarti ritorno": "QF · Leg 2",
    "quarti gara 1": "QF · Game 1", "quarti gara 2": "QF · Game 2",
    "semifinale": "Semifinal",
    "semifinale andata": "SF · Leg 1", "semifinale ritorno": "SF · Leg 2",
    "semifinale gara 1": "SF · Game 1", "semifinale gara 2": "SF · Game 2",
    "finale": "Final",
}


def round_label(round_raw: str) -> str:
    return ROUND_LABELS.get(round_raw, round_raw.title())


def is_win(m: dict) -> bool:
    my, opp = (int(x) for x in m["score"].split("-"))
    return my > opp


def result_points(m: dict) -> int:
    """3/2/1/0 points for the match result, same scale as the standings rule."""
    my, opp = (int(x) for x in m["score"].split("-"))
    if (my, opp) in ((3, 0), (3, 1)):
        return 3
    if (my, opp) == (3, 2):
        return 2
    if (my, opp) == (2, 3):
        return 1
    return 0


def parsed_date(sheet_date: str):
    """'24-03-31' -> date(2024, 3, 31)."""
    from datetime import date as _date

    yy, mm, dd = (int(p) for p in sheet_date.split("-"))
    return _date(2000 + yy, mm, dd)


def match_by_date(sheet_date: str) -> dict | None:
    """Full match dict -- built-in history or entered via Data Entry --
    for one date, regardless of which season it falls in. Every page reads
    a match this way (or via matches_for_season() for a whole season)
    rather than the flat MATCHES global above, which only ever holds the
    2023/24 built-in record and doesn't see entered matches."""
    day = parsed_date(sheet_date)
    for m in matches_for_season(fs.season_of(day)):
        if m["date"] == sheet_date:
            return m
    return None


def match_label(sheet_date: str) -> str:
    """'date - Opponent (round)' label for selectboxes and chips."""
    m = match_by_date(sheet_date)
    if m is None:
        return sheet_date
    round_part = f" ({m['round']})" if m.get("round") else ""
    return f"{sheet_date} · {m['opponent']}{round_part}"


# ---------------------------------------------------------------------------
# Serie A1 2023/24 final standings (regular season, 26 rounds), recomputed
# from the real results of all 182 matches (14 teams, single round-robin
# played twice) with the rule: 3-0/3-1 win = 3pt, 3-2 win = 2pt, 2-3 loss =
# 1pt, 0-3/1-3 loss = 0pt. "last5" = points earned in the last 5 rounds.
# Cross-checked against Conegliano's undefeated 26-0 regular season.
# ---------------------------------------------------------------------------
STANDINGS_2023_24 = [
    {"pos": 1, "team": "Conegliano", "pts": 75, "p": 26, "w": 26, "l": 0, "sf": 78, "sa": 14, "last5": [3, 3, 3, 3, 3], "is_us": False},
    {"pos": 2, "team": "Scandicci", "pts": 63, "p": 26, "w": 22, "l": 4, "sf": 69, "sa": 26, "last5": [3, 3, 3, 3, 2], "is_us": False},
    {"pos": 3, "team": "Milano", "pts": 60, "p": 26, "w": 21, "l": 5, "sf": 68, "sa": 31, "last5": [2, 1, 3, 3, 0], "is_us": True},
    {"pos": 4, "team": "Novara", "pts": 56, "p": 26, "w": 19, "l": 7, "sf": 62, "sa": 33, "last5": [3, 0, 0, 3, 0], "is_us": False},
    {"pos": 5, "team": "Chieri", "pts": 48, "p": 26, "w": 15, "l": 11, "sf": 57, "sa": 40, "last5": [0, 3, 0, 3, 3], "is_us": False},
    {"pos": 6, "team": "Pinerolo", "pts": 37, "p": 26, "w": 12, "l": 14, "sf": 50, "sa": 54, "last5": [3, 0, 0, 0, 3], "is_us": False},
    {"pos": 7, "team": "Megavolley", "pts": 37, "p": 26, "w": 12, "l": 14, "sf": 45, "sa": 49, "last5": [3, 3, 0, 0, 3], "is_us": False},
    {"pos": 8, "team": "Roma", "pts": 37, "p": 26, "w": 12, "l": 14, "sf": 48, "sa": 57, "last5": [1, 1, 2, 0, 3], "is_us": False},
    {"pos": 9, "team": "Casalmaggiore", "pts": 31, "p": 26, "w": 10, "l": 16, "sf": 43, "sa": 57, "last5": [0, 2, 3, 3, 0], "is_us": False},
    {"pos": 10, "team": "Firenze", "pts": 30, "p": 26, "w": 11, "l": 15, "sf": 42, "sa": 56, "last5": [0, 0, 3, 0, 3], "is_us": False},
    {"pos": 11, "team": "Busto Arsizio", "pts": 24, "p": 26, "w": 7, "l": 19, "sf": 36, "sa": 61, "last5": [0, 0, 3, 0, 0], "is_us": False},
    {"pos": 12, "team": "Bergamo", "pts": 19, "p": 26, "w": 5, "l": 21, "sf": 33, "sa": 68, "last5": [0, 0, 0, 3, 1], "is_us": False},
    {"pos": 13, "team": "Cuneo", "pts": 18, "p": 26, "w": 7, "l": 19, "sf": 35, "sa": 68, "last5": [3, 2, 0, 0, 0], "is_us": False},
    {"pos": 14, "team": "Trentino", "pts": 11, "p": 26, "w": 3, "l": 23, "sf": 21, "sa": 73, "last5": [0, 1, 3, 0, 0], "is_us": False},
]

# One real season so far (2023/24); 2024/25 is a placeholder with no data
# yet, kept selectable so the season picker doesn't have to change shape
# once results start coming in.
SEASONS = ["2023-24", "2024-25"]
SEASON_MATCHES = {
    "2023-24": MATCHES,
    "2024-25": [],
}
SEASON_STANDINGS = {
    "2023-24": STANDINGS_2023_24,
    "2024-25": [],
}


def matches_for_season(season: str) -> list[dict]:
    """All match dicts for the given season -- the built-in history above,
    overlaid with whatever's been entered through Data Entry (an entry on
    a date the built-in record already has replaces that row, so filling
    in/correcting a match is an edit in place, not a duplicate) -- each
    with a parsed `pdate`, sorted chronologically."""
    by_date = {m["date"]: m for m in SEASON_MATCHES.get(season, [])}
    for entry in fs.list_match_entries(season):
        by_date[entry["date"]] = entry
    return sorted(
        ({**m, "pdate": parsed_date(m["date"])} for m in by_date.values()),
        key=lambda m: m["pdate"],
    )


