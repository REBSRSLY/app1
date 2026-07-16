"""Punto di ingresso dell'app: configurazione pagina, sidebar e routing tra le sezioni.

Ogni voce del menu è implementata nel proprio file dentro app_pages/, con una
funzione render() richiamata da qui in base alla scelta nella sidebar.
"""

import streamlit as st

import styles
from app_pages import (
    atlete,
    confronti,
    formazioni,
    home,
    inserimento_dati,
    partite,
    scout_statistiche,
    wellness,
)

st.set_page_config(
    page_title="Vero Volley Milano - Staff Tecnico",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject()

# ---------------------------------------------------------------------------
# Sidebar & Navigazione
# ---------------------------------------------------------------------------

PAGES = {
    "Home": home.render,
    "Atlete": atlete.render,
    "Partite": partite.render,
    "Scout & Statistiche": scout_statistiche.render,
    "Carico & Wellness": wellness.render,
    "Confronti": confronti.render,
    "Formazioni": formazioni.render,
    "Inserimento dati": inserimento_dati.render,
}

with st.sidebar:
    st.markdown('<div class="brand-title">Vero Volley Milano</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Staff tecnico · A1 Femminile</div>', unsafe_allow_html=True)

    menu = st.radio(
        "Menu Navigazione",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )

# ---------------------------------------------------------------------------
# Rendering della sezione selezionata
# ---------------------------------------------------------------------------

PAGES[menu]()
