import streamlit as st

from roster import partite
from ui_helpers import section_header


def render():
    section_header("Matches", "Season match list (45 recorded). Each match opens per-fundamental scouting.")

    st.text_input("🔍 Filter by date...", placeholder="E.g. 24-03")

    # Render match date chips as HTML
    chips_html = "".join([f'<span class="date-chip">{d}</span>' for d in partite])
    st.markdown(f'<div class="chip-container">{chips_html}</div>', unsafe_allow_html=True)

    st.write("")
    st.info("For per-fundamental statistics of each match (as in the TOTALE sheet), filterable by individual player, go to **Scout & Stats**.")
