"""App entry point: page config, top navigation and shared filters.

Page navigation lives in a fixed top bar (st.navigation(position="top")) so
it's always visible and never has to share space with anything else. The
collapsible sidebar is dedicated entirely to the season/competition/period
tools in filters.py, which every page reads from for continuity instead of
each keeping its own local date picker.
"""

import streamlit as st

import filters
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
filters.init()

pages = [
    st.Page(home.render, title="Home", icon=":material/home:", url_path="home", default=True),
    st.Page(atlete.render, title="Players", icon=":material/badge:", url_path="players"),
    st.Page(partite.render, title="Matches", icon=":material/calendar_month:", url_path="matches"),
    st.Page(scout_statistiche.render, title="Scout & Stats", icon=":material/bar_chart:", url_path="scout-stats"),
    st.Page(wellness.render, title="Wellness", icon=":material/monitor_heart:", url_path="wellness"),
    st.Page(loads.render, title="Loads", icon=":material/fitness_center:", url_path="loads"),
    st.Page(confronti.render, title="Comparisons", icon=":material/compare_arrows:", url_path="comparisons"),
    st.Page(formazioni.render, title="Lineups", icon=":material/grid_view:", url_path="lineups"),
    st.Page(inserimento_dati.render, title="Data Entry", icon=":material/edit_note:", url_path="data-entry"),
]
page = st.navigation(pages, position="top")

with st.sidebar:
    filters.render_sidebar_tools()

page.run()
