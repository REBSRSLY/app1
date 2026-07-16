import streamlit as st

from ui_helpers import section_header


def render():
    section_header(
        "Carico & Wellness",
        "Monitoraggio giornaliero: questionario wellness (Fatica, Sonno, Doms, Stress, Mood, TQR), "
        "RPE/Training Load, conteggio salti — per squadra o singola atleta.",
    )

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">📈 <b>Vista squadra:</b> trend TQR medio nel tempo (già in bozza nel primo mockup)</div>
            <div class="ph-line">👤 <b>Vista atleta:</b> stesso trend filtrato + confronto con carico (RPE × durata) e salti giornalieri</div>
            <div class="ph-line">⚙️ Soglie di allerta configurabili (es. TQR sotto una certa media)</div>
        </div>
    """, unsafe_allow_html=True)
