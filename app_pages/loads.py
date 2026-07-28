import plotly.express as px
import streamlit as st

import data_loader as dl
import filters
import player_colors as pc
from ui_helpers import section_header

SECTIONS = ["Jumps", "RPE / Load"]


def _render_jumps(salti):
    salti_players = sorted(salti["player_name"].dropna().unique())
    sel_players = st.multiselect("Players", salti_players, default=salti_players, key="jumps_players")

    period = filters.filter_by_date_col(salti)
    period = period[period["player_name"].isin(sel_players)].dropna(subset=["SALTI"])

    if period.empty:
        st.info("No jump data for this selection.")
        return

    daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
    fig = px.bar(
        daily, x="Data", y="SALTI", color="player_name", barmode="stack",
        color_discrete_map=pc.color_map(daily["player_name"].unique()),
        labels={"Data": "Date", "SALTI": "Jumps", "player_name": "Player"},
    )
    fig.update_layout(legend_title_text="Player")
    st.plotly_chart(fig, width="stretch")


def _render_rpe(rpe):
    rpe_players = sorted(rpe["player_name"].dropna().unique())

    metric_label = st.segmented_control(
        "Metric", ["RPE", "Training Load"], default="Training Load", required=True, key="rpe_metric",
    )
    metric_col = "Rpe" if metric_label == "RPE" else "TL"
    agg = "mean" if metric_col == "Rpe" else "sum"

    sel_players = st.multiselect(
        "Players to compare", rpe_players, default=rpe_players[:5], key="rpe_players",
    )

    period = filters.filter_by_date_col(rpe)
    period = period[period["player_name"].isin(sel_players)].dropna(subset=[metric_col])

    if not sel_players or period.empty:
        st.info("Select at least one player with data in this date range.")
        return

    daily = period.groupby(["Data", "player_name"], as_index=False)[metric_col].agg(agg)
    fig = px.line(
        daily.sort_values("Data"), x="Data", y=metric_col, color="player_name", markers=True,
        color_discrete_map=pc.color_map(daily["player_name"].unique()),
        labels={"Data": "Date", metric_col: metric_label, "player_name": "Player"},
    )
    fig.update_layout(legend_title_text="Player")
    st.plotly_chart(fig, width="stretch")


def render():
    section_header("Loads", "Training load monitoring: jump count and RPE/Training Load — for the team or an individual player.")

    data = dl.load_wellness_data()
    rpe, salti = data["rpe"], data["salti"]

    st.caption(f":material/filter_alt: {filters.caption()} · change the period from the sidebar.")
    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="loads_section")

    if section == "Jumps":
        _render_jumps(salti)
    else:
        _render_rpe(rpe)
