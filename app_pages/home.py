import streamlit as st

import data_loader as dl
from ui_helpers import section_header


def render():
    section_header("Home", "Colpo d'occhio sulla stagione: numeri chiave da scouting e wellness.")

    matches = dl.load_match_list()
    wellness = dl.load_wellness_data()["wellness"]

    with st.container(horizontal=True):
        st.metric("Partite analizzate", len(matches), border=True)
        st.metric("Atlete monitorate", len(dl.load_player_names()) - 1, border=True)
        st.metric("Prima partita", min(matches), border=True)
        st.metric("Ultima partita", max(matches), border=True)

    # Allerta recupero: TQR più basso registrato nell'ultimo giorno di rilevazione disponibile
    ultima_data = wellness["Data"].max()
    ultimo_giorno = wellness[wellness["Data"] == ultima_data].sort_values("Tqr")
    soglia = 15
    sotto_soglia = ultimo_giorno[ultimo_giorno["Tqr"] < soglia]

    if not sotto_soglia.empty:
        atlete_str = " · ".join(f"{r.player_name} (TQR {r.Tqr:.1f})" for r in sotto_soglia.itertuples())
        st.markdown(f"""
            <div class="alert-card">
                ⚠️ <b>Recupero basso</b> — {atlete_str} sotto soglia {soglia} il {ultima_data.strftime('%d/%m/%Y')}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="alert-card">
                ✅ <b>Recupero nella norma</b> — nessuna atleta sotto soglia {soglia} il {ultima_data.strftime('%d/%m/%Y')}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Accesso rapido</div>
            <div class="ph-line">📊 <b>Scout & Statistiche</b> — statistiche per fondamentale e distribuzione del gioco in attacco</div>
            <div class="ph-line">💤 <b>Carico & Wellness</b> — trend TQR, RPE e salti (in bozza, da definire insieme)</div>
            <div class="ph-line">📅 Prossimo impegno (partita/allenamento) — nessuna fonte dati calendario ancora collegata</div>
        </div>
    """, unsafe_allow_html=True)
