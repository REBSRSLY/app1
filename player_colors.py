"""Per-player color assignment, kept consistent across every chart in the app.

Colors are grouped by role, each role its own hue family, so a player's
color also signals her position at a glance:
  Setters (Palleggio)        -> 2 shades of light blue
  Opposites (Opposto)        -> 2 shades of green
  Outside Hitters (Banda)    -> 4 shades of yellow
  Middle Blockers (Centro)   -> 4 shades of pink
  Liberos (Libero)           -> white / grey

Keyed by the short player name used everywhere else in the app (e.g.
"Egonu"), same as data_loader.load_player_names() values / players_grid.py
"surname" fields.
"""

PLAYER_COLORS = {
    # Setters -- light blue
    "Orro": "#64B5F6",
    "Prandi": "#1565C0",
    # Opposites -- green
    "Egonu": "#66BB6A",
    "Malual": "#2E7D32",
    # Outside Hitters -- yellow
    "Sylla": "#FFF176",
    "Cazaute": "#FDD835",
    "Daalderop": "#F9A825",
    "Bajema": "#F57F17",
    # Middle Blockers -- pink
    "Folie": "#F8BBD0",
    "Heyrman": "#F06292",
    "Rettke": "#EC407A",
    "Candi": "#AD1457",
    # Liberos -- white / grey
    "Castillo": "#FFFFFF",
    "Parrocchiale": "#BDBDBD",
    "Pusic": "#757575",
}

DEFAULT_COLOR = "#9E9E9E"

# PLAYER_COLORS is already declared role-by-role (Setters, Opposites,
# Outside Hitters, Middle Blockers, Liberos) -- its own key order doubles
# as the canonical role order, so every list/legend of players in the app
# can share one definition of "in role order" instead of each page
# re-deriving its own.
ROLE_ORDERED_NAMES = list(PLAYER_COLORS.keys())


def color_for(player_name: str) -> str:
    return PLAYER_COLORS.get(player_name, DEFAULT_COLOR)


def color_map(names) -> dict:
    """color_discrete_map-ready {name: color} dict for the given names."""
    return {n: color_for(n) for n in names}


def sort_by_role(names) -> list[str]:
    """`names` (any iterable, duplicates or not) as a de-duplicated list in
    role order -- Setters, Opposites, Outside Hitters, Middle Blockers,
    Liberos, matching each player's own color family. A name outside
    PLAYER_COLORS (shouldn't happen for the 15-player roster, but not
    assumed) keeps its relative input order, appended at the end rather
    than dropped."""
    present = set(names)
    known = [n for n in ROLE_ORDERED_NAMES if n in present]
    unknown = [n for n in dict.fromkeys(names) if n not in PLAYER_COLORS]
    return known + unknown
