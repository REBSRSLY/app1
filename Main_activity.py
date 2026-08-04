"""App entry point: page config, top navigation and shared filters.

Navigation is a custom fixed top bar (plain st.button, styled via CSS keyed
off each button's auto-generated st-key class) rather than
st.navigation(position="top"): the native version's internal markup is
built by a ResizeObserver-driven overflow component that doesn't render
reliably in every environment and can't be reached with custom CSS with any
confidence, while plain buttons give full, verifiable control over the
colored border and the active-page gradient design asks for.

The collapsible sidebar is dedicated entirely to the season/competition/
period tools in filters.py, which every page reads from for continuity
instead of each keeping its own local date picker.
"""

import streamlit as st
import streamlit.components.v1 as components

import filters
import styles
from app_pages import (
    atlete,
    home,
    inserimento_dati,
    loads,
    partite,
    scout_statistiche,
    wellness,
)

st.set_page_config(
    page_title="Vero Volley Milano - Technical Staff",
    page_icon="Volley graphic design/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject()
filters.init()

PAGES = {
    "Home": home.render,
    "Players": atlete.render,
    "Matches": partite.render,
    "Scout & Stats": scout_statistiche.render,
    "Wellness": wellness.render,
    "Loads": loads.render,
    "Data Entry": inserimento_dati.render,
}

PAGE_ICONS = {
    "Home": "home",
    "Players": "badge",
    "Matches": "calendar_month",
    "Scout & Stats": "bar_chart",
    "Wellness": "monitor_heart",
    "Loads": "fitness_center",
    "Data Entry": "edit_note",
}

st.session_state.setdefault("menu", "Home")


def _set_menu(name):
    st.session_state.menu = name


NAV_CSS = """
<style>
    /* Fixed to the very top of the viewport, in Streamlit's own header
       band (same row as the sidebar's "<<" collapse control) instead of
       sitting in normal page flow below it. left:0 (rather than a
       hardcoded sidebar width) plus the sidebar's own higher z-index
       means the sidebar simply covers our left edge whenever it's
       expanded -- when it's collapsed (including via the auto-collapse
       below), the bar naturally extends to fill that space, no JS needed.
       right leaves room for Streamlit's own Deploy/menu buttons, which
       live in the same band on the far right. */
    div[data-testid="stHorizontalBlock"]:has(> div [class*="st-key-topnav_"]) {
        position: fixed;
        top: 0;
        left: 0;
        right: 112px;
        max-width: 760px;
        z-index: 999990;
        background: var(--ink);
        height: 52px;
        align-items: center;
        padding: 0 0 0 24px;
        margin-bottom: 0;
        border-bottom: 2px solid transparent;
        border-image: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 65%, var(--accent-3) 100%) 1;
    }
    [class*="st-key-topnav_"] button {
        border: 1.5px solid var(--accent) !important;
        border-radius: 7px !important;
        font-family: var(--display);
        font-weight: 700;
        font-size: 12.5px !important;
        text-transform: uppercase;
        letter-spacing: 0.01em;
        padding: 2px 10px !important;
        min-height: 34px !important;
        height: 34px !important;
    }
    [class*="st-key-topnav_"] button[kind="primary"] {
        background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 100%) !important;
        border: 1.5px solid transparent !important;
        color: #ffffff !important;
        box-shadow: 0 0 0 2px var(--accent-3);
    }
    /* Page content used to start right after the nav row when it was
       part of normal flow; now that the row is fixed/out of flow, this
       makes room for it instead of the first section rendering underneath. */
    div[data-testid="stMainBlockContainer"] {
        padding-top: 4.2rem !important;
    }
    /* The sidebar's filter tools (Season/Competition/Match/Period + preset
       buttons) can run taller than the viewport; rather than an internal
       scrollbar, just clip -- everything above the fold is still reachable,
       and switching pages auto-collapses the sidebar anyway (see the
       components.html script below). */
    [data-testid="stSidebarContent"] {
        overflow-y: hidden !important;
    }
</style>
"""
st.markdown(NAV_CSS, unsafe_allow_html=True)

# Auto-collapses the sidebar the moment a topnav page button is clicked.
# st.set_page_config(initial_sidebar_state=...) can't do this -- it only
# takes effect on the very first mount, not on later reruns -- so this
# reaches into the parent document (components.html renders in an iframe,
# but same-origin means window.parent.document is the real app DOM) and
# clicks Streamlit's own collapse button directly. Guarded by a flag on
# window.parent so the listener is attached once, not once per rerun.
components.html(
    """
    <script>
    (function () {
        const doc = window.parent.document;
        if (doc.__vvmSidebarAutocloseAttached) return;
        doc.__vvmSidebarAutocloseAttached = true;
        doc.addEventListener("click", function (e) {
            if (!e.target.closest('[class*="st-key-topnav_"] button')) return;
            setTimeout(function () {
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar && sidebar.getAttribute("aria-expanded") === "true") {
                    const collapseBtn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
                    if (collapseBtn) collapseBtn.click();
                }
            }, 150);
        });
    })();
    </script>
    """,
    height=0,
)

nav_cols = st.columns(len(PAGES), gap="small")
for col, (name, icon) in zip(nav_cols, PAGE_ICONS.items()):
    with col:
        st.button(
            name,
            icon=f":material/{icon}:",
            key=f"topnav_{name}",
            type="primary" if st.session_state.menu == name else "secondary",
            on_click=_set_menu,
            args=(name,),
        )

with st.sidebar:
    filters.render_sidebar_tools()

PAGES[st.session_state.menu]()
