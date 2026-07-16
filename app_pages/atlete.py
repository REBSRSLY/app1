import streamlit as st

from roster import titolari, panchina
from ui_helpers import section_header


def _render_dossier_card(p, is_starter=True):
    file_id = f"FILE · {p['pos']} · {p['code']}" if "pos" in p else f"FILE · {p['code']}"
    tab_class = "starter" if is_starter else "bench"
    captain_html = '<span class="stamp-captain">Captain</span>' if "tag" in p else ""

    with st.container(border=True):
        st.markdown(f'<div class="dossier-tab {tab_class}"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dossier-id">{file_id}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dossier-name">{p["name"]}{captain_html}</div>', unsafe_allow_html=True)
        st.caption(p["role"])
        if "alt" in p:
            st.caption(f"Alternates with: {p['alt']}")


def _render_grid(players, is_starter):
    cols = st.columns(3)
    for i, p in enumerate(players):
        with cols[i % 3]:
            _render_dossier_card(p, is_starter=is_starter)


def render():
    section_header("Players", "Full roster. Each file summarizes role, position and rotation notes.")

    search_query = st.text_input("🔍 Search player...", placeholder="Type a name...")

    def _matches(p):
        return not search_query or search_query.lower() in p["name"].lower()

    st.subheader("Starting Roster")
    _render_grid([p for p in titolari if _matches(p)], is_starter=True)

    st.subheader("Bench")
    _render_grid([p for p in panchina if _matches(p)], is_starter=False)
