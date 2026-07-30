from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import calendar_view as cv
import data_loader as dl
import filters
import match_calendar as mc
import player_colors as pc
import players_grid as pg
import training_load
from ui_helpers import close_polygon, dark_polar_layout, tqr_yaxis_ticks

GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
WARN_COLOR = "#F0A600"
RECOVERY_THRESHOLD = 15

# Same convention as scout_statistiche.py's own OUTCOME_COLORS/SYMBOL_TO_COL
# -- duplicated here (rather than imported across pages) just for the one
# optional "Serve outcome mix" extra widget below.
_OUTCOME_COLORS = {"=": "#E45756", "-": "#F58518", "!": "#B0B0B0", "+": "#54A24B", "#": "#2E7D32", "/": "#8D6E63"}
_SYMBOL_TO_COL = {"=": "Err", "-": "Neg", "!": "Neutral", "+": "Pos", "#": "Perfect", "/": "Slash"}

# key -> (label, source page) -- the picker in the "Customize" popover lets
# the user add any of these below the fixed widgets already on the page.
# Dict order is preserved, so entries are grouped page-by-page here on
# purpose -- the popover renders one section per page, in this order.
EXTRA_WIDGETS = {
    "wellness_individual_tqr": ("Individual TQR trends", "Wellness"),
    "loads_acwr_chart": ("Team ACWR & weekly load", "Loads"),
    "loads_jumps": ("Jumps per player", "Loads"),
    "loads_rpe_by_role": ("RPE distribution by role", "Loads"),
    "loads_rpe_scatter": ("RPE vs. session duration", "Loads"),
    "matches_score_patterns": ("Score patterns", "Matches"),
    "matches_per_month": ("Matches per month by competition", "Matches"),
    "scout_serve_outcome": ("Serve outcome mix (team)", "Scout & Stats"),
    "scout_team_profile_bar": ("Team profile · E% per fundamental (bar)", "Scout & Stats"),
}


def _render_hero(season: str) -> list[str]:
    """Returns the list of extra widget keys currently checked in the
    Customize popover -- built straight from this run's checkboxes (rather
    than read back from st.session_state under a different key) so the
    rest of render() always sees this run's actual selection immediately,
    not whatever was true before this rerun."""
    spacer_l, col_crest, col_title, col_customize, spacer_r = st.columns(
        [0.03, 0.09, 0.58, 0.24, 0.03], vertical_alignment="center"
    )
    with col_crest:
        st.image(pg.CREST_PATH, width=52)
    with col_title:
        st.markdown(
            '<div style="font-size:1.4rem;font-weight:800;line-height:1.15;">Vero Volley Milano</div>'
            f'<div style="color:var(--muted);font-size:0.8rem;">Technical Staff · A1 Women\'s · Season {season}</div>',
            unsafe_allow_html=True,
        )

    selected: list[str] = []
    with col_customize:
        st.markdown(
            "<style>.st-key-home_customize_box button{white-space:nowrap;}</style>",
            unsafe_allow_html=True,
        )
        with st.container(key="home_customize_box"), st.popover("Customize", icon=":material/tune:", width="stretch"):
            st.markdown("**Add charts from other pages**")
            st.caption("Pick any chart from any screen to show below, grouped by where it comes from.")
            by_page: dict[str, list[tuple[str, str]]] = {}
            for key, (label, page) in EXTRA_WIDGETS.items():
                by_page.setdefault(page, []).append((key, label))
            for i, (page, items) in enumerate(by_page.items()):
                border = "border-top:1px solid var(--line);padding-top:8px;" if i > 0 else ""
                st.markdown(
                    f'<div style="color:var(--muted);font-size:11px;text-transform:uppercase;'
                    f'letter-spacing:0.06em;font-weight:700;margin-top:8px;{border}">{page}</div>',
                    unsafe_allow_html=True,
                )
                for key, label in items:
                    if st.checkbox(label, key=f"home_extra_{key}"):
                        selected.append(key)
    return selected


def _topic_label(name: str):
    """Small gray label naming which page a group of widgets below it is
    pulled from -- lets each widget stay a quick glance while still
    pointing to where to go for the full picture."""
    st.markdown(
        f'<div style="color:var(--muted);font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.07em;font-weight:700;margin:2px 0 6px;">{name}</div>',
        unsafe_allow_html=True,
    )


def _render_low_recovery(wellness: pd.DataFrame):
    """Compact list instead of one long run-on sentence -- each player
    below threshold gets her own row with a colored TQR pill, worst-first,
    so the most urgent cases are immediately on top instead of buried in text."""
    last_date = wellness["Data"].max()
    last_day = wellness[wellness["Data"] == last_date].sort_values("Tqr")
    below = last_day[last_day["Tqr"] < RECOVERY_THRESHOLD]

    with st.container(border=True):
        if below.empty:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<span style="font-size:1.6rem;">✅</span>'
                f'<b style="color:{GOOD_COLOR};font-size:1.1rem;">Recovery on track</b></div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            '<span style="font-size:1.6rem;">⚠️</span>'
            f'<b style="color:{LOW_COLOR};font-size:1.1rem;">Low recovery</b></div>',
            unsafe_allow_html=True,
        )
        rows = list(below.itertuples())
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 2px;'
            f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
            f'<span style="font-weight:600;font-size:0.92rem;">{r.player_name}</span>'
            f'<span style="background:rgba(228,87,86,0.15);color:{LOW_COLOR};font-weight:700;'
            f'border-radius:10px;padding:1px 9px;font-size:12px;">TQR {r.Tqr:.1f}</span></div>'
            for i, r in enumerate(rows)
        )
        st.markdown(rows_html, unsafe_allow_html=True)


def _render_readiness_gauge(rpe: pd.DataFrame):
    with st.container(border=True):
        st.markdown("**Team readiness** · ACWR")
        team_metrics = training_load.metrics_frame(rpe).dropna(subset=["acwr"])
        if team_metrics.empty:
            st.caption("Not enough training history yet.")
            return

        ref_date = team_metrics.index.max()
        acwr = float(team_metrics.loc[ref_date, "acwr"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=acwr,
            number=dict(font=dict(size=36, color="#f2f2f2"), valueformat=".2f"),
            gauge=dict(
                axis=dict(range=[0, 2], tickfont=dict(color="#9a9a9a")),
                bar=dict(color="#ffffff", thickness=0.28),
                bgcolor="rgba(0,0,0,0)",
                steps=[
                    {"range": [0, 0.8], "color": WARN_COLOR},
                    {"range": [0.8, 1.3], "color": GOOD_COLOR},
                    {"range": [1.3, 1.5], "color": WARN_COLOR},
                    {"range": [1.5, 2], "color": LOW_COLOR},
                ],
            ),
        ))
        fig.update_layout(height=160, margin=dict(l=20, r=20, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")


def _render_league_position(season: str):
    with st.container(border=True):
        st.markdown("**League position**")
        standings = mc.SEASON_STANDINGS.get(season, [])
        us = next((r for r in standings if r["is_us"]), None)
        if us is None or not standings:
            st.caption("No standings yet.")
            return

        st.markdown(
            f'<div style="font-size:2.8rem;font-weight:800;color:var(--accent);line-height:1;'
            f'margin-bottom:6px;">#{us["pos"]}</div>',
            unsafe_allow_html=True,
        )

        # Compare our points to whichever's more informative: the leader if
        # we're not #1, otherwise the runner-up (our cushion at the top).
        other = standings[0] if us["pos"] != 1 else (standings[1] if len(standings) > 1 else None)
        if other is not None:
            fig = go.Figure(go.Bar(
                x=[us["pts"], other["pts"]], y=["Milano", other["team"]], orientation="h",
                marker_color=["#1655a5", "#8a8a8a"],
                text=[f"{us['pts']} pts", f"{other['pts']} pts"], textposition="outside",
                textfont=dict(color="#f2f2f2"),
            ))
            fig.update_layout(
                height=95, margin=dict(l=8, r=40, t=2, b=2),
                xaxis=dict(visible=False, range=[0, max(us["pts"], other["pts"]) * 1.3]),
                yaxis=dict(tickfont=dict(size=11)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f2f2f2",
            )
            st.plotly_chart(fig, width="stretch")


def _render_top_scorers():
    """Top 3, ranked list -- a photo for just the #1 gave that single
    player disproportionate visual weight for what's meant to be a quick
    top-3 leaderboard, not a player spotlight."""
    with st.container(border=True):
        st.markdown("**Top scorers** this season")
        stats = dl.load_player_stats()
        if stats.empty:
            st.caption("No season stats yet.")
            return

        ranked = stats.sort_values("points", ascending=False).head(3)
        medals = ["🥇", "🥈", "🥉"]
        rows = list(ranked.itertuples())
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 2px;'
            f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
            f'<span style="font-size:1.05rem;">{medals[i]}</span>'
            f'<span style="flex:1;padding-left:8px;font-weight:700;font-size:0.95rem;">{r.Index}</span>'
            f'<span style="text-align:right;line-height:1.25;">'
            f'<span style="color:var(--accent);font-weight:700;font-size:0.92rem;">{int(r.points)} pts</span><br>'
            f'<span style="color:var(--muted);font-size:10.5px;">{int(r.appearances)} matches</span>'
            f'</span></div>'
            for i, r in enumerate(rows)
        )
        st.markdown(rows_html, unsafe_allow_html=True)


def _render_team_shape():
    """Same enriched radar principle as the Wellness page's own radars: a
    faint mean shape, a +/-1 std dev band around it, and a solid outline
    for the most recent match in scope layered on top -- instead of a
    single flat shape that only shows one snapshot."""
    with st.container(border=True):
        st.markdown("**Team shape** · efficiency (E%)")
        scout = dl.load_scout_data()
        in_scope = {m["date"] for m in filters.matches_in_scope()}
        d = scout[
            scout["match"].isin(in_scope) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ].copy()
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(d["fondamentale"])]
        if len(present) < 3:
            st.caption("Not enough data in this scope for a radar.")
            return

        labels = [dl.FONDAMENTALE_LABELS[f] for f in present]
        agg = d.groupby("fondamentale")["E_pct"].agg(["mean", "std"]).reindex(present)
        d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
        last_date = d["pdate"].max()
        last_per_fond = d[d["pdate"] == last_date].groupby("fondamentale")["E_pct"].mean().reindex(present)

        # +50pp shift, same trick as the Wellness/Scout & Stats radars: E_pct
        # can be negative, which would collapse/invert a polar shape around
        # the origin. It also reaches ~90% here (Set), so shifted values can
        # reach ~1.4 -- [0, 1.5] gives that room instead of clipping at 1.
        values = (agg["mean"] + 0.5).fillna(0.5).tolist()
        stds = agg["std"].fillna(0).tolist()
        last_values = (last_per_fond + 0.5).fillna(pd.Series(values, index=present)).tolist()
        upper = [v + s for v, s in zip(values, stds)]
        lower = [v - s for v, s in zip(values, stds)]

        fig = go.Figure()
        r_lower, theta_lower = close_polygon(lower, labels)
        fig.add_trace(go.Scatterpolar(
            r=r_lower, theta=theta_lower, mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        r_upper, theta_upper = close_polygon(upper, labels)
        fig.add_trace(go.Scatterpolar(
            r=r_upper, theta=theta_upper, mode="lines", fill="tonext",
            line=dict(width=0), fillcolor="rgba(22,85,165,0.18)",
            showlegend=False, hoverinfo="skip",
        ))
        r, theta = close_polygon(values, labels)
        fig.add_trace(go.Scatterpolar(
            r=r, theta=theta, mode="lines", line=dict(color="rgba(22,85,165,0.7)", width=1.2),
            showlegend=False,
        ))
        r_last, theta_last = close_polygon(last_values, labels)
        fig.add_trace(go.Scatterpolar(
            r=r_last, theta=theta_last, mode="lines+markers",
            line=dict(color="#1655a5", width=2), marker=dict(color="#1655a5", size=6),
            showlegend=False,
        ))

        top = max(max(upper, default=1.0), max(last_values, default=1.0)) * 1.1 or 1.5
        fig.update_layout(**dark_polar_layout([0, top]))
        fig.update_layout(
            polar=dict(radialaxis=dict(showticklabels=False), angularaxis=dict(tickfont=dict(size=9))),
            height=230, margin=dict(l=55, r=55, t=25, b=25),
        )
        st.plotly_chart(fig, width="stretch", theme=None)


def _render_recent_form():
    """Last 5 Serie A1 results as colored dots (same win-margin scale used
    on the Matches page's standings) -- a quick "how's it going" snapshot
    that the old static Quick access panel didn't give, and which the
    fixed top nav already makes redundant as a navigation aid."""
    season_matches = mc.matches_for_season(filters.season())
    serie_a1 = sorted((m for m in season_matches if m["competition"] == "Serie A1"), key=lambda m: m["pdate"])
    if not serie_a1:
        return

    recent = serie_a1[-4:]
    with st.container(border=True):
        st.markdown("**Recent form** · Serie A1")
        cols = st.columns(len(recent) + 1)
        for col, m in zip(cols, recent):
            with col:
                color = cv.RESULT_COLORS[mc.result_points(m)]
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="width:15px;height:15px;border-radius:50%;background:{color};margin:0 auto 4px;"></div>'
                    f'<div style="font-size:10px;color:var(--muted);white-space:nowrap;">{cv.fmt_date(m["date"])}</div>'
                    f'<div style="font-size:11.5px;font-weight:700;white-space:nowrap;">{m["score"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with cols[-1]:
            wins = sum(1 for m in serie_a1 if mc.is_win(m))
            st.markdown(
                f'<div style="text-align:center; padding-top:8px;">'
                f'<div style="font-size:1.05rem;font-weight:800;white-space:nowrap;">{wins}W–{len(serie_a1) - wins}L</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _extra_wellness_individual_tqr():
    with st.container(border=True):
        st.markdown("**Individual TQR** · trend over time")
        wellness = dl.load_wellness_data()["wellness"]
        period = filters.filter_by_date_col(wellness)
        daily = period.dropna(subset=["Tqr"]).groupby(["Data", "player_name"], as_index=False)["Tqr"].mean().sort_values("Data")
        if daily.empty:
            st.info("No wellness data in this date range.")
            return
        fig = px.line(
            daily, x="Data", y="Tqr", color="player_name",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "Date", "Tqr": "TQR", "player_name": "Player"},
        )
        fig.add_hline(y=RECOVERY_THRESHOLD, line_dash="dash", line_color=LOW_COLOR)
        fig.update_layout(
            height=250, margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="TQR", range=[6, 20], **tqr_yaxis_ticks()), legend_title_text="Player",
        )
        st.plotly_chart(fig, width="stretch")


def _extra_loads_acwr_chart():
    with st.container(border=True):
        st.markdown("**Team ACWR** & weekly load")
        rpe = dl.load_wellness_data()["rpe"]
        start, end = filters.period()
        team_metrics = training_load.metrics_frame(rpe)
        d = team_metrics.loc[
            (team_metrics.index >= pd.Timestamp(start)) & (team_metrics.index <= pd.Timestamp(end))
        ].dropna(subset=["acwr"])
        if d.empty:
            st.info("Not enough training history in this period to compute ACWR (needs 28+ days of prior data).")
            return

        top = max(2.5, float(d["acwr"].max()) + 0.2)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d.index, y=d["acute"], name="Weekly load (7d)", marker_color="#4C78A8", opacity=0.55))
        fig.add_trace(go.Scatter(x=d.index, y=d["acwr"], name="ACWR", yaxis="y2", line=dict(color="#E45756", width=2)))
        fig.add_hrect(y0=0.8, y1=1.3, yref="y2", fillcolor="rgba(84,162,75,0.18)", line_width=0)
        fig.add_hrect(y0=1.5, y1=top, yref="y2", fillcolor="rgba(228,87,86,0.14)", line_width=0)
        fig.update_layout(
            yaxis=dict(title="Weekly load (TL)"), yaxis2=dict(title="ACWR", overlaying="y", side="right", range=[0, top]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            height=240, margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, width="stretch")


def _extra_loads_jumps():
    with st.container(border=True):
        st.markdown("**Jumps** · per player")
        salti = dl.load_wellness_data()["salti"]
        period = filters.filter_by_date_col(salti).dropna(subset=["SALTI"])
        if period.empty:
            st.info("No jump data in this date range.")
            return
        daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
        fig = px.bar(
            daily, x="Data", y="SALTI", color="player_name", barmode="stack",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "Date", "SALTI": "Jumps", "player_name": "Player"},
        )
        fig.update_layout(legend_title_text="Player", height=240, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")


def _extra_loads_rpe_by_role():
    with st.container(border=True):
        st.markdown("**RPE distribution** · by role")
        rpe = dl.load_wellness_data()["rpe"]
        period = filters.filter_by_date_col(rpe)
        d = period.dropna(subset=["Rpe", "RUOLO"]).copy()
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
        fig.update_layout(showlegend=False, height=210, margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")


def _extra_loads_rpe_scatter():
    with st.container(border=True):
        st.markdown("**RPE** vs. session duration")
        rpe = dl.load_wellness_data()["rpe"]
        period = filters.filter_by_date_col(rpe)
        d = period.dropna(subset=["Rpe", "Time"])
        if d.empty:
            st.info("No RPE data in this period.")
            return
        fig = px.scatter(
            d, x="Time", y="Rpe", color="player_name", opacity=0.65,
            color_discrete_map=pc.color_map(d["player_name"].unique()),
            labels={"Time": "Duration (min)", "Rpe": "RPE"},
        )
        fig.update_layout(showlegend=False, height=210, margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")


_SCORE_POINTS = {"3-0": 3, "3-1": 3, "3-2": 2, "2-3": 1, "1-3": 0, "0-3": 0}
_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _extra_matches_score_patterns():
    with st.container(border=True):
        st.markdown("**Score patterns**")
        matches = filters.matches_in_scope()
        if not matches:
            st.info("No matches in this scope.")
            return
        counts = Counter(m["score"] for m in matches)
        scores = sorted(counts.keys(), key=lambda s: _SCORE_POINTS.get(s, 0))
        fig = go.Figure(go.Bar(
            x=[counts[s] for s in scores], y=scores, orientation="h",
            marker_color=[cv.RESULT_COLORS[_SCORE_POINTS.get(s, 0)] for s in scores],
        ))
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Matches", yaxis_title="")
        st.plotly_chart(fig, width="stretch")


def _extra_matches_per_month():
    with st.container(border=True):
        st.markdown("**Matches per month** · by competition")
        season_matches = mc.matches_for_season(filters.season())
        if not season_matches:
            st.info("No matches this season.")
            return
        df = pd.DataFrame(season_matches)
        order = sorted({(d.year, d.month) for d in df["pdate"]})
        order_labels = [f"{_MONTH_NAMES[m]} {y}" for y, m in order]
        df["month"] = df["pdate"].apply(lambda d: f"{_MONTH_NAMES[d.month]} {d.year}")
        counts = df.groupby(["month", "competition"], observed=True).size().reset_index(name="count")
        fig = px.bar(
            counts, x="month", y="count", color="competition",
            category_orders={"month": order_labels, "competition": mc.COMPETITION_ORDER},
            color_discrete_map={k: v["color"] for k, v in mc.COMPETITIONS.items()},
            labels={"month": "", "count": "Matches", "competition": ""},
        )
        fig.update_layout(
            height=200, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig, width="stretch")


def _extra_scout_serve_outcome():
    with st.container(border=True):
        st.markdown("**Serve outcome mix** · team")
        scout = dl.load_scout_data()
        team = scout[
            (scout["match"] == dl.SEASON_LABEL) & scout["is_team"]
            & (scout["fondamentale"] == "Battuta") & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ]
        if team.empty:
            st.info("No serve data available.")
            return

        row = team.iloc[0]
        legenda = dl.legenda_fondamentale("Battuta")
        rows = []
        for simbolo, nome, _ in legenda:
            col = _SYMBOL_TO_COL.get(simbolo)
            if col is None:
                continue
            count = row.get(col, 0)
            rows.append({"Outcome": f"{nome} ({simbolo})", "count": 0 if pd.isna(count) else count})
        d = pd.DataFrame(rows)
        if d.empty or d["count"].sum() == 0:
            st.info("No serve outcome data available.")
            return

        color_map = {f"{nome} ({simbolo})": _OUTCOME_COLORS.get(simbolo, "#888888") for simbolo, nome, _ in legenda}
        fig = px.pie(d, names="Outcome", values="count", hole=0.5, color="Outcome", color_discrete_map=color_map)
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, width="stretch")


def _extra_scout_team_profile_bar():
    with st.container(border=True):
        st.markdown("**Team profile** · E% per fundamental (bar)")
        scout = dl.load_scout_data()
        team = scout[
            (scout["match"] == dl.SEASON_LABEL) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ].copy()
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(team["fondamentale"])]
        if not present:
            st.info("No season data yet.")
            return
        order_labels = [dl.FONDAMENTALE_LABELS[f] for f in present]
        team["Fundamental"] = team["fondamentale"].map(dl.FONDAMENTALE_LABELS)
        fig = px.bar(
            team, x="E_pct", y="Fundamental", orientation="h",
            category_orders={"Fundamental": order_labels},
            color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
            labels={"E_pct": "Efficiency E%", "Fundamental": ""},
        )
        fig.update_layout(
            coloraxis_showscale=False, xaxis_tickformat=".0%", height=200,
            yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
            margin=dict(l=0, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, width="stretch")


def _render_how_to():
    st.caption(
        "**How to use this app** · Pick a season, competition and period in the sidebar -- every page "
        "reads from it. Switch pages with the top bar. Scout & Stats has four sections (Team Profile, "
        "General stats, Game distribution, Scout Sheet) picked with the segmented control at its top. "
        "Upload your own scouting or wellness files in Data Entry to see what the app reads from them."
    )


def render():
    season = filters.season()
    data = dl.load_wellness_data()
    wellness = data["wellness"]

    extra = _render_hero(season)
    margin = 0.03
    col_w = (1 - 2 * margin) / 3

    _, col_a, col_b, col_c, _ = st.columns([margin, col_w, col_w, col_w, margin])

    with col_a:
        _topic_label("Wellness")
        _render_low_recovery(wellness)
        if "wellness_individual_tqr" in extra:
            _extra_wellness_individual_tqr()
        _topic_label("Loads")
        _render_readiness_gauge(data["rpe"])
        if "loads_acwr_chart" in extra:
            _extra_loads_acwr_chart()
        if "loads_jumps" in extra:
            _extra_loads_jumps()
        if "loads_rpe_by_role" in extra:
            _extra_loads_rpe_by_role()
        if "loads_rpe_scatter" in extra:
            _extra_loads_rpe_scatter()

    with col_b:
        _topic_label("Matches")
        _render_league_position(season)
        _render_recent_form()
        if "matches_score_patterns" in extra:
            _extra_matches_score_patterns()
        if "matches_per_month" in extra:
            _extra_matches_per_month()

    with col_c:
        _topic_label("Scout & Stats")
        _render_top_scorers()
        _render_team_shape()
        if "scout_serve_outcome" in extra:
            _extra_scout_serve_outcome()
        if "scout_team_profile_bar" in extra:
            _extra_scout_team_profile_bar()

    _, mid, _ = st.columns([margin, 1 - 2 * margin, margin])
    with mid:
        _render_how_to()
