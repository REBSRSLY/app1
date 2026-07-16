import streamlit as st

from roster import titolari, panchina
from ui_helpers import section_header


def _render_atleta_row(p, is_titolare=True):
    pos_str = f"**{p['pos']}**" if is_titolare else "—"
    tag_html = f'<span class="cap-tag">{p["tag"]}</span>' if "tag" in p else ""
    alt_str = f" *(alterna con {p['alt']})*" if "alt" in p else ""

    col1, col2, col3, col4 = st.columns([1, 4, 3, 2])
    with col1:
        st.markdown(pos_str)
    with col2:
        st.markdown(f"**{p['name']}** {tag_html}", unsafe_allow_html=True)
    with col3:
        st.write(p['role'])
    with col4:
        st.code(p['code'])

    if alt_str:
        st.caption(alt_str)
    st.write("---")


def render():
    section_header("Atlete", "Rosa completa. Ogni riga apre la scheda individuale con wellness + rendimento incrociati.")

    search_query = st.text_input("🔍 Cerca atleta...", placeholder="Inserisci il nome...")

    st.subheader("Titolari")
    st.write("---")
    for p in titolari:
        if not search_query or search_query.lower() in p['name'].lower():
            _render_atleta_row(p, is_titolare=True)

    st.subheader("Panchina")
    st.write("---")
    for p in panchina:
        if not search_query or search_query.lower() in p['name'].lower():
            _render_atleta_row(p, is_titolare=False)
