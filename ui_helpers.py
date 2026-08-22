"""Small UI utilities shared across the app's sections."""


def close_polygon(r, theta):
    """Repeat the first point at the end so a go.Scatterpolar trace closes visually."""
    return list(r) + [r[0]], list(theta) + [theta[0]]


# Wellness questionnaire items shown as icons instead of text labels on radar
# charts. Same 1-5, high = worse items used team-wide (see wellness.py).
WELLNESS_ICONS = {"Fatica": "🔋", "Sonno": "😴", "Doms": "💪", "Stress": "😌", "Mood": "🙂"}

# Shared TQR colors, used by every "TQR N.N" header (Players page gauge,
# Wellness page radars/trends/cards) so the same color always means the
# same thing. Same shared green/yellow/red family as scout_statistiche's
# OUTCOME_COLORS/SCORE_TREND_COLORS and calendar_view's RESULT_COLORS.
GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
WARN_COLOR = "#FDD835"

TQR_MIN, TQR_MAX = 6.0, 20.0

# CoreBo's own published TQR scale (corebosport.com): 8 bands covering
# 6-20 with no gaps, each with its own recovery-quality label. The single
# source of truth for what a TQR number actually means in words, used by
# the Players page gauge, the Wellness page's own explanation, and every
# per-player TQR header/card -- so the wording can't drift between screens.
TQR_BANDS = [
    (7, "No recovery"),
    (8, "Extremely poor recovery"),
    (10, "Very poor recovery"),
    (12, "Poor recovery"),
    (14, "Reasonable recovery"),
    (16, "Good recovery"),
    (18, "Very good recovery"),
    (20, "Max recovery"),
]

# The same scale collapsed to 3 colors for zone-style displays (gauges,
# axis ticks, header numbers): red below TQR_AMBER_MIN, amber through the
# "reasonable recovery" band, green from TQR_GREEN_MIN (CoreBo's first
# "good recovery" value) up.
TQR_AMBER_MIN = 13
TQR_GREEN_MIN = 15


def tqr_recovery_label(tqr: float) -> str:
    """CoreBo's own wording for whichever of the 8 TQR_BANDS `tqr`
    (rounded to the nearest whole point, the scale's own granularity)
    falls into."""
    v = round(tqr)
    for upper, label in TQR_BANDS:
        if v <= upper:
            return label
    return TQR_BANDS[-1][1]


def tqr_zone_color(tqr: float) -> str:
    """GOOD/WARN/LOW_COLOR for whichever CoreBo band `tqr` (rounded) is
    in -- the same reading as tqr_recovery_label, collapsed to 3 colors."""
    v = round(tqr)
    if v < TQR_AMBER_MIN:
        return LOW_COLOR
    if v < TQR_GREEN_MIN:
        return WARN_COLOR
    return GOOD_COLOR


def tqr_yaxis_ticks(tickvals=(6, 8, 10, 12, 13, 15, 16, 18, 20)) -> dict:
    """Y-axis tick config for a TQR line chart: each tick colored red/
    amber/green by tqr_zone_color, so the CoreBo scale's meaning is
    legible straight from the axis labels without a separate reference
    line."""
    ticktext = [f'<span style="color:{tqr_zone_color(v)}">{v}</span>' for v in tickvals]
    return dict(tickvals=list(tickvals), ticktext=ticktext)


def rgba_from_hex(hex_color: str, alpha: float) -> str:
    """'#64B5F6' -> 'rgba(100,181,246,0.3)' (plotly rejects 8-digit hex+alpha)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def dark_polar_layout(radial_range):
    """Shared dark-themed go.Figure layout for radar/polar charts."""
    return dict(
        template="plotly_dark",
        polar=dict(
            # Matches --surface (styles.py), same as the card the chart
            # sits in -- keeps the radar's inner circle from mismatching
            # its own card's fill.
            bgcolor="#000000",
            radialaxis=dict(range=radial_range, gridcolor="#333", linecolor="#333"),
            angularaxis=dict(gridcolor="#333", linecolor="#333"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f2f2f2",
        showlegend=False,
        margin=dict(t=20, b=20),
    )
