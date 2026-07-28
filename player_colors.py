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


def color_for(player_name: str) -> str:
    return PLAYER_COLORS.get(player_name, DEFAULT_COLOR)


def color_map(names) -> dict:
    """color_discrete_map-ready {name: color} dict for the given names."""
    return {n: color_for(n) for n in names}
