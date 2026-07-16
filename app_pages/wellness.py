import plotly.colors as pcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from ui_helpers import close_polygon, dark_polar_layout, date_range_picker, section_header

# Wellness questionnaire items: all 1-5, high = worse (confirmed by negative
# correlation with Tqr, which is 6-20 with high = better).
NEGATIVE_PARAMS = ["Fatica", "Sonno", "Doms", "Stress", "Mood"]
PARAM_LABELS = {
    "Fatica": "Fatigue",
    "Sonno": "Sleep",
    "Doms": "Muscle soreness",
    "Stress": "Stress",
    "Mood": "Mood",
    "Tqr": "TQR",
}
INVERTED_LABELS = {
    "Fatica": "Low fatigue",
    "Sonno": "Good sleep",
    "Doms": "Low soreness",
    "Stress": "Low stress",
    "Mood": "Good mood",
}
PARAM_RANGE = {
    "Fatica": (1, 5), "Sonno": (1, 5), "Doms": (1, 5),
    "Stress": (1, 5), "Mood": (1, 5), "Tqr": (6, 20),
}


def render():
    section_header(
        "Load & Wellness",
        "Daily monitoring: wellness questionnaire (Fatigue, Sleep, Doms, Stress, Mood, TQR), "
        "RPE/Training Load, jump count — for the team or an individual player.",
    )

    data = dl.load_wellness_data()
    wellness, rpe, salti = data["wellness"], data["rpe"], data["salti"]

    tab_wellness, tab_jumps, tab_rpe = st.tabs(["Wellness", "Jumps", "RPE / Load"])

    # ------------------------------------------------------------------
    # TAB 1 — Wellness radars (team by parameter, individual by profile)
    # ------------------------------------------------------------------
    with tab_wellness:
        start_d, end_d = date_range_picker("Date range", wellness["Data"], 7, "wellness_dates")
        period = wellness[(wellness["Data"].dt.date >= start_d) & (wellness["Data"].dt.date <= end_d)]
        st.caption(f"Averages over {start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')}.")

        col_team, col_player = st.columns(2)

        with col_team:
            with st.container(border=True):
                st.markdown("**Team · by parameter**")
                param = st.selectbox(
                    "Parameter", list(PARAM_LABELS.keys()),
                    format_func=lambda p: PARAM_LABELS[p], key="team_param",
                )
                players = sorted(period["player_name"].unique())
                team_avg = period.groupby("player_name")[param].mean().reindex(players)

                if team_avg.empty:
                    st.info("No data in this date range.")
                else:
                    lo, hi = PARAM_RANGE[param]
                    is_negative = param in NEGATIVE_PARAMS
                    r, theta = close_polygon(list(team_avg.values), list(team_avg.index))
                    fig = go.Figure(go.Scatterpolar(
                        r=r, theta=theta, fill="toself",
                        line_color="#c0392b" if is_negative else "#2ecc71",
                        fillcolor="rgba(192,57,43,0.25)" if is_negative else "rgba(46,204,113,0.25)",
                    ))
                    fig.update_layout(**dark_polar_layout([lo, hi]))
                    st.plotly_chart(fig, width="stretch", theme=None)

        with col_player:
            with st.container(border=True):
                st.markdown("**Individual player**")
                all_players = sorted(wellness["player_name"].unique())
                player_sel = st.selectbox("Player", all_players, key="wellness_player")
                p_period = period[period["player_name"] == player_sel]

                if p_period.empty:
                    st.info("No data for this player in this date range.")
                else:
                    inverted = [6 - p_period[p].mean() for p in NEGATIVE_PARAMS]
                    labels = [INVERTED_LABELS[p] for p in NEGATIVE_PARAMS]
                    tqr_avg = p_period["Tqr"].mean()
                    t = max(0.0, min(1.0, (tqr_avg - 6) / (20 - 6)))
                    color = pcolors.sample_colorscale("RdYlGn", [t])[0]
                    fill = color.replace("rgb", "rgba").replace(")", ", 0.35)")
                    r, theta = close_polygon(inverted, labels)
                    fig = go.Figure(go.Scatterpolar(r=r, theta=theta, fill="toself", line_color=color, fillcolor=fill))
                    fig.update_layout(**dark_polar_layout([1, 5]))
                    st.plotly_chart(fig, width="stretch", theme=None)
                    st.caption(f"Axes inverted so bigger = feeling better. Fill color reflects average TQR: {tqr_avg:.1f}/20.")

    # ------------------------------------------------------------------
    # TAB 2 — Jumps
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
    # TAB 3 — RPE / Training Load
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
