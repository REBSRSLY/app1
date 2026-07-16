import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Confronti",
        "Mettere a confronto due o più atlete, o due periodi della stagione, sulle stesse metriche (wellness o scouting).",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">🎛️ <b>Selettore:</b> 2+ atlete oppure 2 intervalli di date</div>
            <div class="ph-line">📊 <b>Metriche disponibili:</b> qualsiasi fondamentale scouting, TQR, RPE, salti</div>
            <div class="ph-line">💡 <b>Esempio d'uso:</b> Folie vs Heyrman nel periodo di alternanza per infortunio</div>
        </div>
    """, unsafe_allow_html=True)
