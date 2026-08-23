import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import player_colors as pc
import training_load
import ui_helpers

SECTIONS = ["Jumps", "RPE / Load"]


def _render_jumps_cumulative(period: pd.DataFrame):
    """Running jump total per player over the period -- workload
    accumulating over time reads faster from a rising line than from
    picking out the tallest daily bars in the stacked chart above."""
    daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum().sort_values("Data")
    daily["cumulative"] = daily.groupby("player_name")["SALTI"].cumsum()
    fig = px.line(
        daily, x="Data", y="cumulative", color="player_name",
        category_orders={"player_name": pc.sort_by_role(daily["player_name"].unique())},
        color_discrete_map=pc.color_map(daily["player_name"].unique()),
        labels={"Data": "Date", "cumulative": "Cumulative jumps", "player_name": "Player"},
        markers=True,
    )
    fig.update_layout(legend_title_text="Player", height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_jumps(salti):
    # No player filter here (removed) -- every chart on this page shows
    # the whole roster with a role-ordered legend, same as every other
    # page's jump/load views. A player with nothing to show simply
    # contributes nothing to the stack/line rather than needing to be
    # deselected first.
    period = filters.filter_by_date_col(salti).dropna(subset=["SALTI"])

    if period.empty:
        st.info("No jump data for this selection.")
        return

    with st.container(border=True):
        st.markdown("**Jumps per player** · daily")
        barmode, barnorm = ui_helpers.bar_mode_toggle("jumps_bar_mode")
        daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
        fig = px.bar(
            daily, x="Data", y="SALTI", color="player_name",
            # Role order, not volume -- same player always lands in the
            # same stacking/grouping position regardless of who jumped
            # most that day, and Grouped mode clusters same-role players
            # next to each other.
            category_orders={"player_name": pc.sort_by_role(daily["player_name"].unique())},
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "Date", "SALTI": "Jumps", "player_name": "Player"},
        )
        fig.update_layout(
            barmode=barmode, barnorm=barnorm,
            legend_title_text="Player", height=320, margin=dict(l=10, r=10, t=10, b=10),
            yaxis_tickformat=".0%" if barnorm else None,
        )
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**Cumulative jumps** · per player")
        _render_jumps_cumulative(period)


def _render_how_to_expander():
    """Same "How to read" affordance the Scout & Stats sections carry --
    these are standard sports-science figures (Foster sRPE, Gabbett ACWR)
    whose names don't explain themselves, and their formulas otherwise
    live only in training_load.py where nobody using the app can see them."""
    with st.expander("How to read \"RPE / Load\"", icon=":material/menu_book:"):
        st.markdown("**RPE** — the athlete's own 1–10 rating of how hard a session felt.")
        st.markdown("**TL** (training load) — `RPE × session minutes`, Foster's sRPE method.")
        st.markdown("---")
        st.markdown(
            f"**Acute load** = `rolling {training_load.ACUTE_DAYS}-day sum of daily TL` — "
            "this week's accumulated work."
        )
        st.markdown(
            f"**Chronic load** = `rolling {training_load.CHRONIC_DAYS}-day sum / 4` — the average "
            "week across the trailing 4 weeks, divided so it stays on the same weekly scale "
            "as the acute load."
        )
        st.markdown(
            "**Team ACWR** = `acute / chronic` — 0.8–1.3 is the sweet spot (green band on the "
            "chart), above 1.5 flags a sudden spike (red band), below 0.8 a de-trained "
            f"drop-off. Needs {training_load.CHRONIC_DAYS}+ days of prior history before it can be computed at all."
        )


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


def _render_heatmap(rpe: pd.DataFrame):
    """Spans the sidebar's selected period rather than a fixed trailing
    week, so it lines up with every other chart on the page."""
    window = filters.filter_by_date_col(rpe).dropna(subset=["Data"])
    if window.empty:
        st.info("No sessions in this period.")
        return

    pivot = window.groupby(["player_name", "Data"])["Rpe"].mean().unstack("Data")
    dates = pd.date_range(window["Data"].min(), window["Data"].max(), freq="D")
    pivot = pivot.reindex(columns=dates).sort_index()

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[d.strftime("%d %b") for d in dates], y=pivot.index.tolist(),
        colorscale="RdYlGn_r", zmin=1, zmax=10,
        colorbar=dict(title="RPE"),
        hovertemplate="%{y} · %{x}<br>RPE: %{z:.1f}<extra></extra>",
    ))
    fig.update_layout(height=max(280, 28 * len(pivot.index)), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_load_drilldown(period_rpe: pd.DataFrame):
    """Click-to-drill-down bar chart: each bar is a session duration (the
    load's length in minutes), height = the team's average RPE across
    every player who logged a session that long. Clicking a bar drills
    into which players logged that duration and what RPE each of them
    gave it -- the average alone hides exactly the spread a coach would
    want to check before trusting "a 100-minute session felt like a 7".
    A breadcrumb rolls back up to the aggregate view."""
    d = period_rpe.dropna(subset=["Rpe", "Time"]).copy()
    if d.empty:
        st.info("No RPE data in this period.")
        return

    selected = st.session_state.get("load_drill_duration")

    if selected is not None:
        sub = d[d["Time"] == selected]
        if st.button("‹ All durations", key="load_drill_back"):
            st.session_state["load_drill_duration"] = None
            st.rerun()
        if sub.empty:
            st.info("No data left for this duration in the current scope.")
            return
        per_player = sub.groupby("player_name", as_index=False)["Rpe"].mean().sort_values("Rpe", ascending=False)
        fig = px.bar(
            per_player, x="player_name", y="Rpe", color="player_name",
            category_orders={"player_name": pc.sort_by_role(per_player["player_name"].unique())},
            color_discrete_map=pc.color_map(per_player["player_name"].unique()),
            labels={"player_name": "", "Rpe": "RPE"},
        )
        fig.update_layout(
            showlegend=False, height=280, margin=dict(l=0, r=10, t=10, b=10), yaxis=dict(range=[0, 10]),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(f"RPE each player gave a {selected:g}-minute session, this period.")
        return

    agg = d.groupby("Time", as_index=False)["Rpe"].mean().sort_values("Time")
    fig = px.bar(agg, x="Time", y="Rpe", labels={"Time": "Duration (min)", "Rpe": "Avg RPE"})
    fig.update_traces(marker_color="#4C78A8")
    fig.update_layout(height=280, margin=dict(l=0, r=10, t=10, b=10), yaxis=dict(range=[0, 10]))
    event = st.plotly_chart(
        fig, width="stretch", on_select="rerun", selection_mode="points", key="load_drill_chart",
    )
    points = event.selection.points if event else []
    # Streamlit keeps the chart's last selection in session_state even
    # after we've already acted on it and the reader has clicked back --
    # without this guard, the very next rerun would see that same stale
    # selection and immediately re-drill into it, making "back" a no-op.
    current_sel = tuple(p.get("point_index") for p in points)
    if points and current_sel != st.session_state.get("load_drill_last_sel"):
        st.session_state["load_drill_last_sel"] = current_sel
        st.session_state["load_drill_duration"] = points[0]["x"]
        st.rerun()
    st.caption("Click a bar to see which players logged that duration and what RPE they gave it.")


# Marker size (px) for a point no other player shares that day, and how
# much bigger it gets per extra player nested around it -- see
# _render_scatter's docstring for the nesting/ordering rule.
_RING_BASE_SIZE = 14
_RING_STEP = 7


def _ring_sized_traces(day_df: pd.DataFrame, players_order: list[str], rank: dict, color_map: dict) -> list[go.Scatter]:
    """One marker trace per roster player for a single day's points, sized
    so players sharing the exact same (duration, RPE) point nest as
    concentric rings instead of hiding each other: whoever comes earlier
    in `players_order` gets a bigger marker (drawn first/behind, in trace
    order below), whoever comes later gets a smaller one (drawn later, on
    top) -- so the fixed role order, not the specific players involved,
    decides which ring sits outside which every time."""
    traces = []
    for p in players_order:
        sub = day_df[day_df["player_name"] == p]
        if sub.empty:
            traces.append(go.Scatter(x=[], y=[], mode="markers", name=p, showlegend=False))
            continue
        sizes = []
        for _, row in sub.iterrows():
            group = day_df[(day_df["Time"] == row["Time"]) & (day_df["Rpe"] == row["Rpe"])]
            nested_inside = sum(1 for other in group["player_name"] if rank[other] > rank[p])
            sizes.append(_RING_BASE_SIZE + nested_inside * _RING_STEP)
        traces.append(go.Scatter(
            x=sub["Time"], y=sub["Rpe"], mode="markers", name=p,
            marker=dict(size=sizes, color=color_map[p], line=dict(width=1, color="rgba(0,0,0,0.45)")),
            showlegend=False,
        ))
    return traces


def _render_scatter(period_rpe: pd.DataFrame):
    """Same RPE-vs-duration cloud as before, but scrubbable day by day
    (a Gapminder-style animation_frame slider + play button) instead of
    one flat scatter for the whole period, so a coach can watch the
    cloud move match by match rather than reading every day at once.
    Two or more players logging the exact same (duration, RPE) pair on
    the same day nest as concentric rings (see _ring_sized_traces)
    instead of one marker hiding the other."""
    d = period_rpe.dropna(subset=["Rpe", "Time", "Data"]).copy()
    if d.empty:
        st.info("No RPE data in this period.")
        return

    players_order = pc.sort_by_role(d["player_name"].dropna().unique())
    rank = {p: i for i, p in enumerate(players_order)}
    color_map = pc.color_map(players_order)
    dates = sorted(d["Data"].dt.date.unique())

    fig = go.Figure(
        data=_ring_sized_traces(d[d["Data"].dt.date == dates[0]], players_order, rank, color_map),
        frames=[
            go.Frame(
                data=_ring_sized_traces(d[d["Data"].dt.date == day], players_order, rank, color_map),
                name=day.isoformat(),
            )
            for day in dates
        ],
    )
    # Legend-only swatches (the real per-player traces above are
    # showlegend=False, since re-adding all 15 to the legend on every
    # frame would just repeat it) -- same trick as the Trend chart above.
    for p in players_order:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=9, color=color_map[p]), name=p))

    fig.update_layout(
        xaxis=dict(title="Duration (min)", range=[0, d["Time"].max() * 1.1]),
        yaxis=dict(title="RPE", range=[0, 10.5]),
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0, y=-0.24, xanchor="left", yanchor="top",
            buttons=[dict(
                label="▶ Play", method="animate",
                args=[None, dict(frame=dict(duration=450, redraw=True), fromcurrent=True, transition=dict(duration=0))],
            )],
        )],
        sliders=[dict(
            active=0, x=0.1, y=-0.24, len=0.9, xanchor="left", yanchor="top",
            currentvalue=dict(prefix="Match day: "),
            steps=[
                dict(method="animate", label=day.strftime("%d %b %y"), args=[
                    [day.isoformat()], dict(mode="immediate", frame=dict(duration=0, redraw=True)),
                ])
                for day in dates
            ],
        )],
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Play or drag the slider to scrub through match days. Nested rings = more than one player logged the "
        "exact same duration/RPE that day (outer ring = earlier in the roster order, innermost = latest)."
    )


def _render_individual_trend(rpe: pd.DataFrame, team_metrics: pd.DataFrame, start, end):
    players = pc.sort_by_role(rpe["player_name"].dropna().unique())
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
    team_metrics = training_load.metrics_frame(rpe)

    _render_how_to_expander()

    col_heat, col_acwr = st.columns([1, 1.3])
    with col_heat:
        with st.container(border=True):
            st.markdown("**Team heatmap** · RPE per player")
            _render_heatmap(rpe)
    with col_acwr:
        with st.container(border=True):
            st.markdown("**Team ACWR & weekly load**")
            _render_acwr_chart(team_metrics, start, end)

    period_rpe = filters.filter_by_date_col(rpe)
    with st.container(border=True):
        st.markdown("**RPE by duration** · click a bar to drill into players")
        _render_load_drilldown(period_rpe)

    with st.container(border=True):
        st.markdown("**RPE vs. session duration** · scrub through match days")
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
