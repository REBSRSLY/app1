import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import player_colors as pc
import players_grid as pg
import training_load

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


def _reference_date(rpe: pd.DataFrame):
    """Latest training day at or before the active period's end -- the
    anchor the KPI row and heatmap read "as of". None if the period ends
    before any training data exists."""
    _, end = filters.period()
    available = rpe["Data"].dropna()
    available = available[available <= pd.Timestamp(end)]
    return available.max() if not available.empty else None


def _render_kpis(rpe: pd.DataFrame, team_metrics: pd.DataFrame, ref_date):
    cols = st.columns(4)
    if ref_date is None or ref_date not in team_metrics.index:
        for col, label in zip(cols, ["Avg TL", "Avg RPE", "Team ACWR", "Weekly monotony"]):
            with col:
                st.metric(label, "—", border=True)
        return

    row = team_metrics.loc[ref_date]
    today_sessions = rpe[rpe["Data"] == ref_date]
    rpe_today = today_sessions["Rpe"].mean() if not today_sessions.empty else None

    with cols[0]:
        st.metric("Avg TL", f"{row['daily_tl']:.0f}", border=True)
    with cols[1]:
        st.metric("Avg RPE", f"{rpe_today:.1f}" if pd.notna(rpe_today) else "—", border=True)
    with cols[2]:
        st.metric("Team ACWR", f"{row['acwr']:.2f}" if pd.notna(row["acwr"]) else "—", border=True)
    with cols[3]:
        st.metric("Weekly monotony", f"{row['monotony']:.2f}" if pd.notna(row["monotony"]) else "—", border=True)


def _render_acwr_chart(team_metrics: pd.DataFrame, start, end):
    d = team_metrics.loc[(team_metrics.index >= pd.Timestamp(start)) & (team_metrics.index <= pd.Timestamp(end))]
    d = d.dropna(subset=["acwr"])
    if d.empty:
        st.info("Not enough training history yet in this period to compute ACWR (needs 28+ days of prior data).")
        return

    top = max(2.5, float(d["acwr"].max()) + 0.2)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=d.index, y=d["acute"], name="Weekly load (7d)", marker_color="#4C78A8", opacity=0.55))
    fig.add_trace(go.Scatter(x=d.index, y=d["acwr"], name="ACWR", yaxis="y2", line=dict(color="#E45756", width=2)))
    fig.add_hrect(y0=0.8, y1=1.3, yref="y2", fillcolor="rgba(84,162,75,0.18)", line_width=0)
    fig.add_hrect(y0=1.5, y1=top, yref="y2", fillcolor="rgba(228,87,86,0.14)", line_width=0)
    fig.update_layout(
        yaxis=dict(title="Weekly load (TL)"),
        yaxis2=dict(title="ACWR", overlaying="y", side="right", range=[0, top]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=320, margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Green band 0.8–1.3 = sweet spot · red band >1.5 = injury-risk spike.")


def _render_heatmap(rpe: pd.DataFrame, ref_date):
    if ref_date is None:
        st.info("No sessions in the last 7 days.")
        return

    start = ref_date - pd.Timedelta(days=6)
    window = rpe[(rpe["Data"] >= start) & (rpe["Data"] <= ref_date)]
    if window.empty:
        st.info("No sessions in the last 7 days.")
        return

    pivot = window.groupby(["player_name", "Data"])["Rpe"].mean().unstack("Data")
    dates = pd.date_range(start, ref_date, freq="D")
    pivot = pivot.reindex(columns=dates).sort_index()

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[d.strftime("%d %b") for d in dates], y=pivot.index.tolist(),
        colorscale="RdYlGn_r", zmin=1, zmax=10,
        colorbar=dict(title="RPE"),
        hovertemplate="%{y} · %{x}<br>RPE: %{z:.1f}<extra></extra>",
    ))
    fig.update_layout(height=max(280, 28 * len(pivot.index)), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_role_box(period_rpe: pd.DataFrame):
    d = period_rpe.dropna(subset=["Rpe", "RUOLO"]).copy()
    if d.empty:
        st.info("No RPE data in this period.")
        return

    d["Role"] = d["RUOLO"].map(dl.ROLE_LABELS)
    order = d.groupby("Role")["Rpe"].median().sort_values().index.tolist()
    fig = px.box(
        d, x="Rpe", y="Role", orientation="h", points="outliers",
        category_orders={"Role": order}, color="Role", color_discrete_map=pg.ROLE_COLORS,
        labels={"Rpe": "RPE", "Role": ""},
    )
    fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_scatter(period_rpe: pd.DataFrame):
    d = period_rpe.dropna(subset=["Rpe", "Time"])
    if d.empty:
        st.info("No RPE data in this period.")
        return

    fig = px.scatter(
        d, x="Time", y="Rpe", color="player_name", opacity=0.65,
        color_discrete_map=pc.color_map(d["player_name"].unique()),
        labels={"Time": "Duration (min)", "Rpe": "RPE"},
    )
    fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_individual_trend(rpe: pd.DataFrame, team_metrics: pd.DataFrame, start, end):
    players = sorted(rpe["player_name"].dropna().unique())
    if not players:
        st.info("No RPE data available.")
        return
    player_sel = st.selectbox("Player", players, key="load_trend_player")

    player_metrics = training_load.metrics_frame(rpe, player_sel)
    d_player = player_metrics.loc[(player_metrics.index >= pd.Timestamp(start)) & (player_metrics.index <= pd.Timestamp(end))]
    d_team = team_metrics.loc[(team_metrics.index >= pd.Timestamp(start)) & (team_metrics.index <= pd.Timestamp(end))]

    if d_player.empty:
        st.info("No RPE data for this player in this period.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d_player.index, y=d_player["daily_tl"], name=player_sel, line=dict(color=pc.color_for(player_sel))))
    fig.add_trace(go.Scatter(x=d_team.index, y=d_team["daily_tl"], name="Team average", line=dict(color="#9a9a9a", dash="dash")))
    fig.update_layout(
        yaxis_title="Daily TL", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=280, margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Look for an athlete tracking systematically above her teammates at similar training volume -- a sign of possible extra fatigue or poor recovery.")


def _render_load(rpe: pd.DataFrame):
    start, end = filters.period()
    ref_date = _reference_date(rpe)
    team_metrics = training_load.metrics_frame(rpe)

    _render_kpis(rpe, team_metrics, ref_date)
    if ref_date is not None:
        st.caption(f"As of {ref_date.strftime('%d %b %Y')}, the latest training day in the selected period.")

    col_heat, col_acwr = st.columns([1, 1.3])
    with col_heat:
        with st.container(border=True):
            st.markdown("**Team heatmap** · last 7 days")
            _render_heatmap(rpe, ref_date)
    with col_acwr:
        with st.container(border=True):
            st.markdown("**Team ACWR & weekly load**")
            _render_acwr_chart(team_metrics, start, end)

    period_rpe = filters.filter_by_date_col(rpe)
    col_role, col_scatter = st.columns(2)
    with col_role:
        with st.container(border=True):
            st.markdown("**RPE distribution by role**")
            _render_role_box(period_rpe)
    with col_scatter:
        with st.container(border=True):
            st.markdown("**RPE vs. session duration**")
            _render_scatter(period_rpe)

    with st.container(border=True):
        st.markdown("**Individual trend vs. team average**")
        _render_individual_trend(rpe, team_metrics, start, end)


def render():
    data = dl.load_wellness_data()
    rpe, salti = data["rpe"], data["salti"]

    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="loads_section")

    if section == "Jumps":
        _render_jumps(salti)
    else:
        _render_load(rpe)
