"""Fixed 4x4 roster grid for the Players page (photo + role + season stats).

Layout is by role, not starter/bench (unlike roster.py, which the Lineups
page still uses): row 1 = Setters + Opposites, row 2 = Outside Hitters,
row 3 = Middle Blockers, row 4 = Liberos + the club crest. Role assignment
for all 15 players (including Heyrman and Daalderop, who only exist as
another player's "alt" in roster.py) comes from data_loader.load_player_roles(),
which reads the real Anagrafica sheet.
"""

ROLE_COLORS = {
    "Setter": "#4C78A8",
    "Opposite": "#B279A2",
    "Outside Hitter": "#54A24B",
    "Middle Blocker": "#E45756",
    "Libero": "#F58518",
}

# "surname" must match the values from data_loader.load_player_names() (used
# to look up season stats); "first"/"last" must match the "First Last.png"
# filenames under PHOTO_DIR exactly. "number" is the real jersey number, read
# directly off each player's photo (Parrocchiale's photo is a mismatched
# non-Vero-Volley kit with no number visible, hence None).
GRID_ROWS = [
    [
        {"first": "Alessia", "last": "Orro", "surname": "Orro", "role": "Setter", "captain": True, "number": 8},
        {"first": "Vittoria", "last": "Prandi", "surname": "Prandi", "role": "Setter", "number": 11},
        {"first": "Paola", "last": "Egonu", "surname": "Egonu", "role": "Opposite", "number": 18},
        {"first": "Adhouljok", "last": "Malual", "surname": "Malual", "role": "Opposite", "number": 3},
    ],
    [
        {"first": "Myriam", "last": "Sylla", "surname": "Sylla", "role": "Outside Hitter", "number": 17},
        {"first": "Helena", "last": "Cazaute", "surname": "Cazaute", "role": "Outside Hitter", "number": 1},
        {"first": "Nika", "last": "Daalderop", "surname": "Daalderop", "role": "Outside Hitter", "number": 19},
        {"first": "Kara", "last": "Bajema", "surname": "Bajema", "role": "Outside Hitter", "number": 15},
    ],
    [
        {"first": "Raphaela", "last": "Folie", "surname": "Folie", "role": "Middle Blocker", "number": 7},
        {"first": "Laura", "last": "Heyrman", "surname": "Heyrman", "role": "Middle Blocker", "number": 5},
        {"first": "Dana", "last": "Rettke", "surname": "Rettke", "role": "Middle Blocker", "number": 14},
        {"first": "Sonia", "last": "Candi", "surname": "Candi", "role": "Middle Blocker", "number": 28},
    ],
    [
        {"first": "Brenda", "last": "Castillo", "surname": "Castillo", "role": "Libero", "number": 55},
        {"first": "Beatrice", "last": "Parrocchiale", "surname": "Parrocchiale", "role": "Libero", "number": None},
        {"first": "Teodora", "last": "Pusic", "surname": "Pusic", "role": "Libero", "number": 12},
        None,  # club crest, not a player
    ],
]

PHOTO_DIR = "Volley graphic design/Team Photos"
CREST_PATH = "Volley graphic design/vero_volley_sym-removebg-preview.png"


def photo_path(player: dict) -> str:
    return f"{PHOTO_DIR}/{player['first']} {player['last']}.png"


ALL_PLAYERS = [p for row in GRID_ROWS for p in row if p is not None]
PLAYERS_BY_SURNAME = {p["surname"]: p for p in ALL_PLAYERS}
