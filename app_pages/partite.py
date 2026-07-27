from datetime import datetime

import pandas as pd
import streamlit as st

import calendar_view as cv
import data_loader as dl
import match_calendar as mc
from ui_helpers import section_header


def _render_calendar_tab():
    st.markdown(cv.CALENDAR_CSS, unsafe_allow_html=True)
    st.markdown(cv.render_legend(), unsafe_allow_html=True)

    salti_dates = sorted(dl.load_wellness_data()["salti"]["Data"].dt.date.unique())

    year_tabs = st.tabs([str(y) for y in mc.SEASON_YEARS])
    for year, tab in zip(mc.SEASON_YEARS, year_tabs):
        with tab:
            year_matches = mc.matches_for_year(year)
            if not year_matches and not any(d.year == year for d in salti_dates):
                st.info(f"No matches or sessions recorded for {year}.")
                continue

            available_months = cv.months_with_data(year, salti_dates)
            default_month = available_months[0] if available_months else 1
            month = st.selectbox(
                "Month",
                options=list(range(1, 13)),
                index=list(range(1, 13)).index(default_month),
                format_func=lambda m: cv.MONTH_NAMES[m],
                key=f"month_{year}",
            )
            st.markdown(cv.render_month_calendar(year, month, salti_dates), unsafe_allow_html=True)
            st.caption(f"{len(year_matches)} matches recorded in {year} (hover an event for details).")

    st.write("---")
    st.subheader("Standings · Serie A1 2023/24")
    st.caption(
        "Computed from the real results of the 26 championship rounds: "
        "3-0/3-1 win = 3pt, 3-2 win = 2pt, 2-3 loss = 1pt, 0-3/1-3 loss = 0pt. "
        "Playoffs, Coppa Italia and Champions League don't count towards these standings."
    )
    st.markdown(cv.render_standings(mc.STANDINGS_2023_24), unsafe_allow_html=True)


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
    section_header("Matches", "Full 2023/24 calendar and results (45 matches across Serie A1, Coppa Italia, Supercoppa, Champions League and playoffs).")

    tab_calendar, tab_list = st.tabs(["Calendar", "List"])
    with tab_calendar:
        _render_calendar_tab()
    with tab_list:
        _render_list_tab()

    st.caption("Score is always written as Milano–opponent sets. For per-fundamental scouting statistics of each match, filterable by individual player, go to **Scout & Stats**.")
