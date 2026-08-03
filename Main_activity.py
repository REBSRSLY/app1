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
    /* Pin the nav row to the top of the scrollable area, just below
       Streamlit's own deploy/menu header. */
    div[data-testid="stHorizontalBlock"]:has(> div [class*="st-key-topnav_"]) {
        position: sticky;
        top: 0;
        z-index: 999;
        background: var(--background, #0e1117);
        padding: 6px 0 10px;
        margin-bottom: 4px;
    }
    [class*="st-key-topnav_"] button {
        border: 2px solid var(--accent) !important;
        border-radius: 8px !important;
        font-weight: 600;
    }
    [class*="st-key-topnav_"] button[kind="primary"] {
        background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 100%) !important;
        border: 2px solid transparent !important;
        color: #ffffff !important;
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

nav_cols = st.columns(len(PAGES))
for col, (name, icon) in zip(nav_cols, PAGE_ICONS.items()):
    with col:
        st.button(
            name,
            icon=f":material/{icon}:",
            key=f"topnav_{name}",
            type="primary" if st.session_state.menu == name else "secondary",
            on_click=_set_menu,
            args=(name,),
            width="stretch",
        )

with st.sidebar:
    filters.render_sidebar_tools()

PAGES[st.session_state.menu]()
