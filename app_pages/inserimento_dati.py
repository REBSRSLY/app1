import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Inserimento dati",
        "Caricamento nuovi dati: wellness/RPE/salti giornalieri per atleta, oppure scouting di una nuova partita.",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">📝 <b>Form wellness giornaliero:</b> seleziona atleta + data → Fatica, Sonno, Doms, Stress, Mood (calcolo TQR automatico)</div>
            <div class="ph-line">⏱️ <b>Form RPE/salti:</b> seleziona sessione (AM/PM) → RPE, durata, numero salti</div>
            <div class="ph-line">📥 <b>Import scouting partita:</b> caricamento da file esterno (formato da definire) oppure inserimento manuale per fondamentale</div>
        </div>
    """, unsafe_allow_html=True)
