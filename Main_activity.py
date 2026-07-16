"""App entry point: page config, sidebar and routing between sections.

Each menu entry is implemented in its own file under app_pages/, with a
render() function called from here based on the sidebar selection.

The sidebar nav is custom-built (session-state-driven buttons) rather than
Streamlit's native st.radio/native collapse, so that collapsing it leaves
behind a persistent icon-only rail instead of hiding everything.
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
    page_title="Vero Volley Milano - Technical Staff",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject()

# ---------------------------------------------------------------------------
# Sidebar & navigation
# ---------------------------------------------------------------------------

PAGES = {
    "Home": home.render,
    "Players": atlete.render,
    "Matches": partite.render,
    "Scout & Stats": scout_statistiche.render,
    "Load & Wellness": wellness.render,
    "Comparisons": confronti.render,
    "Lineups": formazioni.render,
    "Data Entry": inserimento_dati.render,
}

PAGE_ICONS = {
    "Home": "home",
    "Players": "badge",
    "Matches": "calendar_month",
    "Scout & Stats": "bar_chart",
    "Load & Wellness": "monitor_heart",
    "Comparisons": "compare_arrows",
    "Lineups": "grid_view",
    "Data Entry": "edit_note",
}

st.session_state.setdefault("menu", "Home")
st.session_state.setdefault("sidebar_expanded", True)


def _set_menu(name):
    st.session_state.menu = name


def _toggle_sidebar():
    st.session_state.sidebar_expanded = not st.session_state.sidebar_expanded


expanded = st.session_state.sidebar_expanded

if not expanded:
    # Shrink the native sidebar container to a narrow rail and hide the nav
    # button labels (kept in the DOM for accessibility, just visually hidden)
    # so only the icons remain visible.
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] { width: 64px !important; min-width: 64px !important; }
            [data-testid="stSidebar"] [class*="st-key-navrail_"] button p,
            [data-testid="stSidebar"] [class*="st-key-expand_toggle"] button p { display: none; }
            [data-testid="stSidebar"] [class*="st-key-navrail_"] button,
            [data-testid="stSidebar"] [class*="st-key-expand_toggle"] button { justify-content: center; padding-left: 0; padding-right: 0; }
            [data-testid="stSidebarCollapseButton"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar:
    if expanded:
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            st.markdown('<div class="brand-title">Vero Volley Milano</div>', unsafe_allow_html=True)
            st.button(
                "Collapse", icon=":material/chevron_left:", key="collapse_toggle",
                on_click=_toggle_sidebar, help="Collapse sidebar",
                type="tertiary",
            )
        st.markdown('<div class="brand-subtitle">Technical Staff · A1 Women\'s</div>', unsafe_allow_html=True)

        for name, icon in PAGE_ICONS.items():
            st.button(
                name,
                icon=f":material/{icon}:",
                key=f"nav_{name}",
                type="primary" if st.session_state.menu == name else "secondary",
                on_click=_set_menu,
                args=(name,),
                width="stretch",
            )
    else:
        st.button(
            "Expand", icon=":material/chevron_right:", key="expand_toggle",
            on_click=_toggle_sidebar, help="Expand sidebar",
            type="tertiary",
        )
        for name, icon in PAGE_ICONS.items():
            st.button(
                name,
                icon=f":material/{icon}:",
                key=f"navrail_{name}",
                type="primary" if st.session_state.menu == name else "secondary",
                on_click=_set_menu,
                args=(name,),
                help=name,
                width="stretch",
            )

# ---------------------------------------------------------------------------
# Render the selected section
# ---------------------------------------------------------------------------

PAGES[st.session_state.menu]()
