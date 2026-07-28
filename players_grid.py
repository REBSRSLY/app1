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
# filenames under PHOTO_DIR exactly.
GRID_ROWS = [
    [
        {"first": "Alessia", "last": "Orro", "surname": "Orro", "role": "Setter", "captain": True},
        {"first": "Vittoria", "last": "Prandi", "surname": "Prandi", "role": "Setter"},
        {"first": "Paola", "last": "Egonu", "surname": "Egonu", "role": "Opposite"},
        {"first": "Adhouljok", "last": "Malual", "surname": "Malual", "role": "Opposite"},
    ],
    [
        {"first": "Myriam", "last": "Sylla", "surname": "Sylla", "role": "Outside Hitter"},
        {"first": "Helena", "last": "Cazaute", "surname": "Cazaute", "role": "Outside Hitter"},
        {"first": "Nika", "last": "Daalderop", "surname": "Daalderop", "role": "Outside Hitter"},
        {"first": "Kara", "last": "Bajema", "surname": "Bajema", "role": "Outside Hitter"},
    ],
    [
        {"first": "Raphaela", "last": "Folie", "surname": "Folie", "role": "Middle Blocker"},
        {"first": "Laura", "last": "Heyrman", "surname": "Heyrman", "role": "Middle Blocker"},
        {"first": "Dana", "last": "Rettke", "surname": "Rettke", "role": "Middle Blocker"},
        {"first": "Sonia", "last": "Candi", "surname": "Candi", "role": "Middle Blocker"},
    ],
    [
        {"first": "Brenda", "last": "Castillo", "surname": "Castillo", "role": "Libero"},
        {"first": "Beatrice", "last": "Parrocchiale", "surname": "Parrocchiale", "role": "Libero"},
        {"first": "Teodora", "last": "Pusic", "surname": "Pusic", "role": "Libero"},
        None,  # club crest, not a player
    ],
]

PHOTO_DIR = "Volley graphic design/Team Photos"
CREST_PATH = "Volley graphic design/vero_volley_sym-removebg-preview.png"


def photo_path(player: dict) -> str:
    return f"{PHOTO_DIR}/{player['first']} {player['last']}.png"


ALL_PLAYERS = [p for row in GRID_ROWS for p in row if p is not None]
PLAYERS_BY_SURNAME = {p["surname"]: p for p in ALL_PLAYERS}
