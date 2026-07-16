import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Data Entry",
        "Upload new data: daily wellness/RPE/jumps per player, or scouting for a new match.",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Work in progress</div>
            <div class="ph-line">📝 <b>Daily wellness form:</b> select player + date → Fatigue, Sleep, Doms, Stress, Mood (automatic TQR calculation)</div>
            <div class="ph-line">⏱️ <b>RPE/jumps form:</b> select session (AM/PM) → RPE, duration, jump count</div>
            <div class="ph-line">📥 <b>Match scouting import:</b> upload from an external file (format TBD) or manual entry per fundamental</div>
        </div>
    """, unsafe_allow_html=True)
