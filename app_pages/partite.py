import streamlit as st

from roster import partite
from ui_helpers import section_header


def render():
    section_header("Partite", "Elenco partite stagione (45 rilevate). Ogni partita apre lo scouting per fondamentale.")

    st.text_input("🔍 Filtra per data...", placeholder="Es. 24-03")

    # Rendering dei chip delle date delle partite in HTML
    chips_html = "".join([f'<span class="date-chip">{d}</span>' for d in partite])
    st.markdown(f'<div class="chip-container">{chips_html}</div>', unsafe_allow_html=True)

    st.write("")
    st.info("Per le statistiche per fondamentale di ogni partita (come nel foglio TOTALE), filtrabili per singola atleta, vai su **Scout & Statistiche**.")
