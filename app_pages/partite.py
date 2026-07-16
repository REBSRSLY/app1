from datetime import datetime

import pandas as pd
import streamlit as st

from match_calendar import MATCHES
from ui_helpers import section_header


def render():
    section_header("Matches", "Full 2023/24 calendar and results (45 matches across Serie A1, Coppa Italia, Supercoppa, Champions League and playoffs).")

    df = pd.DataFrame(MATCHES).sort_values("date")
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

    st.caption("Score is always written as Milano–opponent sets. For per-fundamental scouting statistics of each match, filterable by individual player, go to **Scout & Stats**.")
