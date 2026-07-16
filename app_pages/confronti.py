import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Comparisons",
        "Compare two or more players, or two periods of the season, on the same metrics (wellness or scouting).",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Work in progress</div>
            <div class="ph-line">🎛️ <b>Selector:</b> 2+ players, or 2 date ranges</div>
            <div class="ph-line">📊 <b>Available metrics:</b> any scouting fundamental, TQR, RPE, jumps</div>
            <div class="ph-line">💡 <b>Example use:</b> Folie vs Heyrman during the injury rotation period</div>
        </div>
    """, unsafe_allow_html=True)
