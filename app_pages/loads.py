import plotly.express as px
import streamlit as st

import data_loader as dl
from ui_helpers import date_range_picker, section_header


def render():
    section_header("Loads", "Training load monitoring: jump count and RPE/Training Load — for the team or an individual player.")

    data = dl.load_wellness_data()
    rpe, salti = data["rpe"], data["salti"]

    tab_jumps, tab_rpe = st.tabs(["Jumps", "RPE / Load"])

    # ------------------------------------------------------------------
    # TAB 1 — Jumps
    # ------------------------------------------------------------------
    with tab_jumps:
        salti_players = sorted(salti["player_name"].dropna().unique())
        start_d, end_d = date_range_picker("Date range", salti["Data"], 14, "jumps_dates")
        sel_players = st.multiselect("Players", salti_players, default=salti_players, key="jumps_players")

        mask = (
            (salti["Data"].dt.date >= start_d) & (salti["Data"].dt.date <= end_d)
            & salti["player_name"].isin(sel_players)
        )
        period = salti[mask].dropna(subset=["SALTI"])

        if period.empty:
            st.info("No jump data for this selection.")
        else:
            daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
            fig = px.bar(
                daily, x="Data", y="SALTI", color="player_name", barmode="stack",
                labels={"Data": "Date", "SALTI": "Jumps", "player_name": "Player"},
            )
            fig.update_layout(legend_title_text="Player")
            st.plotly_chart(fig, width="stretch")

    # ------------------------------------------------------------------
    # TAB 2 — RPE / Training Load
    # ------------------------------------------------------------------
    with tab_rpe:
        rpe_players = sorted(rpe["player_name"].dropna().unique())
        start_d, end_d = date_range_picker("Date range", rpe["Data"], 14, "rpe_dates")

        metric_label = st.segmented_control(
            "Metric", ["RPE", "Training Load"], default="Training Load", required=True, key="rpe_metric",
        )
        metric_col = "Rpe" if metric_label == "RPE" else "TL"
        agg = "mean" if metric_col == "Rpe" else "sum"

        sel_players = st.multiselect(
            "Players to compare", rpe_players, default=rpe_players[:5], key="rpe_players",
        )

        mask = (
            (rpe["Data"].dt.date >= start_d) & (rpe["Data"].dt.date <= end_d)
            & rpe["player_name"].isin(sel_players)
        )
        period = rpe[mask].dropna(subset=[metric_col])

        if not sel_players or period.empty:
            st.info("Select at least one player with data in this date range.")
        else:
            daily = period.groupby(["Data", "player_name"], as_index=False)[metric_col].agg(agg)
            fig = px.line(
                daily.sort_values("Data"), x="Data", y=metric_col, color="player_name", markers=True,
                labels={"Data": "Date", metric_col: metric_label, "player_name": "Player"},
            )
            fig.update_layout(legend_title_text="Player")
            st.plotly_chart(fig, width="stretch")
