"""Small UI utilities shared across the app's sections."""

import streamlit as st


def section_header(title, purpose):
    st.markdown(
        f'<div class="section-header">'
        f'<span class="section-title">{title}</span>'
        f'<span class="section-purpose">{purpose}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def close_polygon(r, theta):
    """Repeat the first point at the end so a go.Scatterpolar trace closes visually."""
    return list(r) + [r[0]], list(theta) + [theta[0]]


# Wellness questionnaire items shown as icons instead of text labels on radar
# charts. Same 1-5, high = worse items used team-wide (see wellness.py).
WELLNESS_ICONS = {"Fatica": "🔋", "Sonno": "😴", "Doms": "💪", "Stress": "😌", "Mood": "🙂"}


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
            bgcolor="#0d0d0f",
            radialaxis=dict(range=radial_range, gridcolor="#333", linecolor="#333"),
            angularaxis=dict(gridcolor="#333", linecolor="#333"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f2f2f2",
        showlegend=False,
        margin=dict(t=20, b=20),
    )
