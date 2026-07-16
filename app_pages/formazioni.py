import streamlit as st

from roster import titolari
from ui_helpers import section_header


def render():
    section_header("Lineups", "Starting six, rotations and alternates by role, with recovery status for players on court.")

    # Court layout (3x2 for the active starting six)
    st.subheader("Court Layout (Starting Six)")

    court_starters = [p for p in titolari if p["pos"] != "L"]

    # Split into 3 columns to simulate the court grid
    cols = st.columns(3)
    for i, p in enumerate(court_starters):
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
