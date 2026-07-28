from datetime import datetime

import pandas as pd
import streamlit as st

import calendar_view as cv
import data_loader as dl
import match_calendar as mc
from ui_helpers import section_header


def _render_by_competition(season: str, season_matches: list[dict]):
    st.markdown(cv.BOX_CSS, unsafe_allow_html=True)

    present = [c for c in mc.COMPETITION_ORDER if any(m["competition"] == c for m in season_matches)]
    if "Serie A1" not in present:
        st.info("No championship matches recorded for this season yet.")
    else:
        col_results, col_standings = st.columns([1, 1.2])
        with col_results:
            st.markdown(cv.render_competition_box("Serie A1", season_matches, show_round=False), unsafe_allow_html=True)
        with col_standings:
            st.markdown(
                cv.render_standings_box(mc.SEASON_STANDINGS.get(season, []), color=mc.COMPETITIONS["Serie A1"]["color"]),
                unsafe_allow_html=True,
            )

    secondary = [c for c in present if c != "Serie A1"]
    for i in range(0, len(secondary), 2):
        cols = st.columns(2)
        for col, comp in zip(cols, secondary[i:i + 2]):
            with col:
                st.markdown(cv.render_competition_box(comp, season_matches), unsafe_allow_html=True)


def _render_full_calendar(season: str, season_matches: list[dict]):
    st.markdown(cv.CALENDAR_CSS, unsafe_allow_html=True)
    st.markdown(cv.render_legend(), unsafe_allow_html=True)

    salti_dates = sorted(dl.load_wellness_data()["salti"]["Data"].dt.date.unique())
    months = mc.season_months(season)
    if not months:
        st.info("No matches to show on the calendar for this season.")
        return

    labels = [f"{cv.MONTH_NAMES[m]} {y}" for y, m in months]
    picked = st.selectbox("Month", options=list(range(len(months))), format_func=lambda i: labels[i], key=f"month_{season}")
    year, month = months[picked]
    st.markdown(cv.render_month_calendar(season_matches, year, month, salti_dates), unsafe_allow_html=True)


def _render_list_tab():
    df = pd.DataFrame(mc.MATCHES).sort_values("date")
    df["Date"] = df["date"].apply(lambda d: datetime.strptime(d, "%y-%m-%d").strftime("%d %b %Y"))
    df["Venue"] = df["home"].map({True: "Home", False: "Away"})
    df["Round"] = df.apply(lambda r: f"{r['competition']} ({r['round']})", axis=1)
    df["Result"] = df["score"].apply(lambda s: "W" if int(s.split("-")[0]) > int(s.split("-")[1]) else "L")

    search = st.text_input("🔍 Search matches...", placeholder="E.g. date, opponent or competition")
    if search:
        s = search.lower()
        mask = df.apply(lambda r: s in r["Date"].lower() or s in r["opponent"].lower() or s in r["Round"].lower(), axis=1)
        df = df[mask]

    st.dataframe(
        df[["Date", "opponent", "Venue", "Round", "score", "Result"]].rename(columns={
            "opponent": "Opponent", "score": "Score",
        }),
        hide_index=True,
        width="stretch",
        column_config={
            "Result": st.column_config.TextColumn(width="small"),
        },
    )


def render():
    section_header("Matches", "Results and standings by competition, plus the full season calendar.")

    season = st.selectbox("Season", mc.SEASONS, index=0, key="season_select")
    season_matches = mc.matches_for_season(season)

    if not season_matches:
        st.info(f"No matches recorded yet for the {season} season.")
        return

    st.subheader("By competition")
    _render_by_competition(season, season_matches)

    st.write("---")
    st.subheader("Full calendar")
    _render_full_calendar(season, season_matches)

    st.write("---")
    with st.expander("All matches (searchable list)"):
        _render_list_tab()

    st.caption("Score is always written as Milano–opponent sets. For per-fundamental scouting statistics of each match, filterable by individual player, go to **Scout & Stats**.")
