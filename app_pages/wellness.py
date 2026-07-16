import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Load & Wellness",
        "Daily monitoring: wellness questionnaire (Fatigue, Sleep, Doms, Stress, Mood, TQR), "
        "RPE/Training Load, jump count — for the team or an individual player.",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Work in progress</div>
            <div class="ph-line">📈 <b>Team view:</b> average TQR trend over time (already drafted in the first mockup)</div>
            <div class="ph-line">👤 <b>Player view:</b> same trend filtered + comparison with load (RPE × duration) and daily jumps</div>
            <div class="ph-line">⚙️ Configurable alert thresholds (e.g. TQR below a certain average)</div>
        </div>
    """, unsafe_allow_html=True)
