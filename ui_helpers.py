"""Small UI utilities shared across the app's sections."""


def close_polygon(r, theta):
    """Repeat the first point at the end so a go.Scatterpolar trace closes visually."""
    return list(r) + [r[0]], list(theta) + [theta[0]]


# Wellness questionnaire items shown as icons instead of text labels on radar
# charts. Same 1-5, high = worse items used team-wide (see wellness.py).
WELLNESS_ICONS = {"Fatica": "🔋", "Sonno": "😴", "Doms": "💪", "Stress": "😌", "Mood": "🙂"}

# Shared TQR readiness threshold and colors, used by every "TQR N.N" header
# (Players page overview, Wellness page radars, Home page's low-recovery
# banner) so the same cutoff and color always mean the same thing.
GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
WARN_COLOR = "#FFC107"
RECOVERY_THRESHOLD = 15


def tqr_yaxis_ticks(tickvals=(6, 8, 10, 12, 14, 15, 16, 18, 20)) -> dict:
    """Y-axis tick config for a TQR line chart: the recovery threshold
    itself in yellow, values below it in red, values above it in green --
    makes the threshold legible straight from the axis labels, since a
    dashed reference line alone is easy to lose among many player lines."""
    ticktext = []
    for v in tickvals:
        if v == RECOVERY_THRESHOLD:
            color = WARN_COLOR
        elif v < RECOVERY_THRESHOLD:
            color = LOW_COLOR
        else:
            color = GOOD_COLOR
        ticktext.append(f'<span style="color:{color}">{v}</span>')
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
