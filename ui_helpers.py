"""Small UI utilities shared across the app's sections."""

from datetime import timedelta

import streamlit as st


def section_header(title, purpose):
    st.title(title)
    st.caption(purpose)
    st.write("---")


def date_range_picker(label, series, default_days, key):
    """A st.date_input range picker defaulting to the last N days of the given date series."""
    min_d = series.min().date()
    max_d = series.max().date()
    default_start = max(min_d, max_d - timedelta(days=default_days - 1))
    value = st.date_input(label, value=(default_start, max_d), min_value=min_d, max_value=max_d, key=key)
    if isinstance(value, tuple) and len(value) == 2:
        return value
    return default_start, max_d


def close_polygon(r, theta):
    """Repeat the first point at the end so a go.Scatterpolar trace closes visually."""
    return list(r) + [r[0]], list(theta) + [theta[0]]


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
