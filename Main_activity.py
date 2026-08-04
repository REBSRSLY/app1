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
       live in the same band on the far right; a fixed width + auto
       margins centers the bar within whatever's left of that span. */
    div[data-testid="stHorizontalBlock"]:has(> div [class*="st-key-topnav_"]) {
        position: fixed;
        top: 0;
        left: 0;
        right: 112px;
        width: 1080px;
        margin: 0 auto;
        z-index: 999990;
        background: var(--ink);
        height: 54px;
        align-items: center;
        padding: 0 8px;
        border-bottom: 2px solid transparent;
        border-image: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 65%, var(--accent-3) 100%) 1;
    }
    /* Compact enough that even "Scout & Stats"/"Data Entry" -- the two
       longest labels -- fit on one line: smaller icon, tight padding, no
       letter-spacing, explicit nowrap as a hard backstop against wrapping
       rather than relying on width alone. */
    [class*="st-key-topnav_"] button {
        border: 1px solid var(--accent) !important;
        border-radius: 6px !important;
        font-family: var(--display);
        font-weight: 700;
        font-size: 11.5px !important;
        text-transform: uppercase;
        letter-spacing: 0;
        padding: 4px 10px !important;
        min-height: 38px !important;
        height: 38px !important;
        white-space: nowrap !important;
        gap: 4px;
    }
    [class*="st-key-topnav_"] button p {
        white-space: nowrap !important;
    }
    [class*="st-key-topnav_"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
    }
    [class*="st-key-topnav_"] button[kind="primary"] {
        background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 100%) !important;
        border: 1px solid transparent !important;
        color: #ffffff !important;
        box-shadow: 0 0 0 2px var(--accent-3);
    }
    /* Page content used to start right after the nav row when it was
       part of normal flow; now that the row is fixed/out of flow, this
       makes room for it instead of the first section rendering underneath.
       Matches the nav's own height (54px) plus 1px of clearance -- px,
       not rem: the root font-size here is 15px, not the usual 16px, so
       a rem value big enough to clear the nav overshot the gap by more
       than intended (55.5px could be trimmed further, not padded more). */
    div[data-testid="stMainBlockContainer"] {
        padding-top: 55px !important;
    }
    /* The sidebar's filter tools (Season/Competition/Match/Period + preset
       buttons) can run taller than the viewport; rather than an internal
       scrollbar, just clip -- everything above the fold is still reachable,
       and switching pages auto-collapses the sidebar anyway (see the
       components.html script below). */
    [data-testid="stSidebarContent"] {
        overflow-y: hidden !important;
    }
    /* Every st.markdown(<style>...) / components.html() call (this one,
       styles.py's, home.py's HERO_CSS) renders as its own zero-height
       stElementContainer -- but Streamlit's vertical gap is a flex `gap`
       on their shared parent, which reserves a full gap-slot for EVERY
       child regardless of height, including these invisible ones. With
       5 such elements stacked above the page's real first block, that
       was 5 stacked gaps (~75px) of dead space nobody could see the
       cause of. display:none removes them from the flex layout entirely
       instead of just collapsing their own (already-zero) height, which
       is what actually closes those gaps -- the CSS/JS inside still
       applies/runs either way, since neither depends on being visible. */
    div[data-testid="stElementContainer"]:has(style),
    div[data-testid="stElementContainer"]:has(iframe) {
        display: none;
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
            width="stretch",
        )

with st.sidebar:
    filters.render_sidebar_tools()

PAGES[st.session_state.menu]()
