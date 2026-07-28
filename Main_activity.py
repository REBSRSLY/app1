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
    loads,
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
    "Wellness": wellness.render,
    "Loads": loads.render,
    "Comparisons": confronti.render,
    "Lineups": formazioni.render,
    "Data Entry": inserimento_dati.render,
}

PAGE_ICONS = {
    "Home": "home",
    "Players": "badge",
    "Matches": "calendar_month",
    "Scout & Stats": "bar_chart",
    "Wellness": "monitor_heart",
    "Loads": "fitness_center",
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

# Streamlit's own native collapse control is always disabled: this app only
# ever collapses to the icon rail via the custom button below, driven purely
# by our own session_state. Streamlit's native collapsed/expanded state
# (aria-expanded) is NOT a reliable signal to build on: it persists on its
# own across page reloads (independently of our session_state, seemingly via
# the browser rather than the Python session) and can end up stuck on the
# opposite value from what was just clicked. So rather than reading it, we
# unconditionally force the sidebar's width to whatever OUR state says it
# should be, in both directions, every rerun -- that's the only way to keep
# the visible width in sync with session_state regardless of whatever the
# native attribute happens to be doing underneath.
#
# Streamlit's native sidebar width transition also keeps a live Web
# Animation running on transform/min-width/max-width that overrides even
# !important values for as long as it's "running" (a CSS-transitions-vs-
# !important quirk); disabling the transition outright is what makes our
# own width override actually stick instead of being silently ignored.
if expanded:
    _sidebar_width_css = """
        [data-testid="stSidebar"] {
            min-width: 300px !important;
            max-width: 300px !important;
            width: 300px !important;
            transform: none !important;
        }
    """
else:
    _sidebar_width_css = """
        [data-testid="stSidebar"] {
            min-width: 64px !important;
            max-width: 64px !important;
            width: 64px !important;
            transform: none !important;
        }
        [data-testid="stSidebar"] [class*="st-key-navrail_"] button p,
        [data-testid="stSidebar"] [class*="st-key-expand_toggle"] button p { display: none; }
        [data-testid="stSidebar"] [class*="st-key-navrail_"] button,
        [data-testid="stSidebar"] [class*="st-key-expand_toggle"] button { justify-content: center; padding-left: 0; padding-right: 0; }
    """

st.markdown(
    f"""
    <style>
        [data-testid="stSidebarCollapseButton"] {{ display: none; }}
        [data-testid="stSidebar"] {{ transition: none !important; }}
        {_sidebar_width_css}
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
