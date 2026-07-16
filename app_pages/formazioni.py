import streamlit as st

from roster import titolari
from ui_helpers import section_header


def render():
    section_header("Formazioni", "Sestetto titolare, rotazioni e alternanze per ruolo, con lo stato di recupero di chi è in campo.")

    # Rappresentazione del campo da gioco (3x2 per il sestetto attivo)
    st.subheader("Disposizione in Campo (Sestetto)")

    campo_titolari = [p for p in titolari if p["pos"] != "L"]

    # Divisione in 3 colonne per simulare la griglia del campo da gioco
    cols = st.columns(3)
    for i, p in enumerate(campo_titolari):
        col_index = i % 3
        with cols[col_index]:
            alt_text = f"\n↔ {p['alt']}" if "alt" in p else ""
            st.metric(
                label=f"{p['pos']} - {p['role']}",
                value=p['name'],
                delta=alt_text if alt_text else None,
                delta_color="off"
            )

    st.write("---")
    libero = next(p for p in titolari if p["pos"] == "L")
    st.write(f"🛡️ **Libero:** {libero['name']} (`{libero['code']}`)")
