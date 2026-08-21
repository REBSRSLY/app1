from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import match_calendar as mc
import player_colors as pc
import players_grid as pg
import training_load
from ui_helpers import close_polygon, dark_polar_layout, tqr_yaxis_ticks
import calendar_view as cv

GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
WARN_COLOR = "#F0A600"
RECOVERY_THRESHOLD = 15

# Same convention as scout_statistiche.py's own OUTCOME_COLORS/SYMBOL_TO_COL
# -- duplicated here (rather than imported across pages) just for the one
# "Serve outcome mix" tile below.
_OUTCOME_COLORS = {"=": "#7A1B1B", "-": "#F58518", "!": "#FDD835", "+": "#54A24B", "#": "#1B5E20", "/": "#E45756"}
_SYMBOL_TO_COL = {"=": "Err", "-": "Neg", "!": "Neutral", "+": "Pos", "#": "Perfect", "/": "Slash"}
_SCORE_POINTS = {"3-0": 3, "3-1": 3, "3-2": 2, "2-3": 1, "1-3": 0, "0-3": 0}
_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Every card the Home dashboard can show, keyed for the Customize popover's
# checkboxes -- "default": True is what a first-time visitor sees; nothing
# here is hardcoded into the page layout anymore, render() just draws
# whichever keys are currently checked, in this catalog's order, wrapped
# into rows. Grouped by source page for the popover's own sections; that
# grouping isn't shown on the page itself (titles alone carry enough
# context for a card this small).
TILE_CATALOG = [
    ("wellness_low_recovery", "Low recovery", "Wellness", True),
    ("wellness_individual_tqr", "Individual TQR trends", "Wellness", False),
    ("loads_readiness", "Team readiness (ACWR)", "Loads", True),
    ("loads_acwr_chart", "ACWR & weekly load", "Loads", True),
    ("loads_jumps", "Jumps per player", "Loads", False),
    ("loads_rpe_by_role", "RPE distribution by role", "Loads", False),
    ("loads_rpe_scatter", "RPE vs. session duration", "Loads", False),
    ("matches_league_position", "League position", "Matches", True),
    ("matches_recent_form", "Recent form", "Matches", True),
    ("matches_score_patterns", "Score patterns", "Matches", True),
    ("matches_per_month", "Matches per month", "Matches", False),
    ("scout_top_scorers", "Top scorers", "Scout & Stats", True),
    ("scout_team_shape", "Team shape radar", "Scout & Stats", True),
    ("scout_serve_outcome", "Serve outcome mix", "Scout & Stats", True),
    ("scout_efficiency_trend", "Efficiency trend", "Scout & Stats", False),
    ("scout_team_profile_bar", "Team profile · E% bar", "Scout & Stats", False),
    ("players_squad_overview", "Squad overview", "Players", False),
]
TILE_LABELS = {key: label for key, label, _page, _default in TILE_CATALOG}

HERO_CSS = """
<style>
    /* A real hero moment instead of a plain header row -- a single-color
       mesh glow (Magenta Numia only, no blue) anchored at the top-left
       corner, simpler than the page-wide background's own mesh+diagonal
       combo so the hero still reads as its own distinct moment rather
       than repeating what's already behind every other box on the page. */
    .st-key-home_hero_box {
        background:
            radial-gradient(90% 140% at 0% 0%, #E0158C 0%, transparent 65%),
            #101418;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 6px 18px;
        margin-bottom: 4px;
    }
    .st-key-home_customize_box button { white-space: nowrap; }
    /* Dashboard tiles: dense grid, small cards -- every chart inside is
       sized to match (see each _tile_* function's own height=); this
       trims Streamlit's default inter-element spacing inside each card,
       which was the biggest source of the page needing to scroll. */
    .st-key-home_grid [data-testid="stElementContainer"] { margin-bottom: 2px !important; }
</style>
"""


def _render_hero(season: str) -> list[str]:
    """Returns the tile keys currently checked in the Customize popover --
    built straight from this run's checkboxes (rather than read back from
    st.session_state under a different key) so render() always sees this
    run's actual selection immediately, not whatever was true before this
    rerun. Every tile on the page -- not just a handful of "extras" -- is
    listed here now, so the whole dashboard is user-configurable."""
    with st.container(key="css_hero"):
        st.markdown(HERO_CSS, unsafe_allow_html=True)
    selected: list[str] = []
    with st.container(key="home_hero_box"):
        spacer_l, col_crest, col_title, col_customize, spacer_r = st.columns(
            [0.02, 0.1, 0.58, 0.24, 0.02], vertical_alignment="center"
        )
        with col_crest:
            st.image(pg.CREST_PATH, width=52)
        with col_title:
            st.markdown(
                '<div style="font-family:var(--display);font-size:1.5rem;font-weight:700;'
                'line-height:1.1;text-transform:uppercase;letter-spacing:0.01em;">Vero Volley Milano</div>'
                f'<div style="color:var(--muted);font-size:0.78rem;margin-top:1px;">Technical Staff · A1 Women\'s · Season {season}</div>',
                unsafe_allow_html=True,
            )

        with col_customize, st.container(key="home_customize_box"), st.popover("Customize", icon=":material/tune:", width="stretch"):
            st.markdown("**Choose what shows on Home**")
            st.caption(
                "Pick a season, competition and period in the sidebar -- every card below reads from it. "
                "Every card here is optional; toggle any of them on or off, grouped by where it comes from."
            )
            by_page: dict[str, list[tuple[str, str, bool]]] = {}
            for key, label, page, default in TILE_CATALOG:
                by_page.setdefault(page, []).append((key, label, default))
            for i, (page, items) in enumerate(by_page.items()):
                border = "border-top:1px solid var(--line);padding-top:8px;" if i > 0 else ""
                st.markdown(
                    f'<div style="color:var(--muted);font-size:11px;text-transform:uppercase;'
                    f'letter-spacing:0.06em;font-weight:700;margin-top:8px;{border}">{page}</div>',
                    unsafe_allow_html=True,
                )
                for key, label, default in items:
                    if st.checkbox(label, value=default, key=f"home_tile_{key}"):
                        selected.append(key)
    return selected


def _tile_low_recovery():
    with st.container(border=True, key="home_low_recovery_box"):
        st.markdown("**Low recovery**")
        wellness = filters.filter_by_date_col(dl.load_wellness_data()["wellness"])
        if wellness.empty:
            st.caption("No data in range.")
            return
        last_date = wellness["Data"].max()
        last_day = wellness[wellness["Data"] == last_date].sort_values("Tqr")
        below = last_day[last_day["Tqr"] < RECOVERY_THRESHOLD]
        if below.empty:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding-top:6px;">'
                f'<span style="font-size:1.4rem;">✅</span>'
                f'<span style="color:{GOOD_COLOR};font-weight:700;font-size:0.95rem;">All clear</span></div>',
                unsafe_allow_html=True,
            )
            return
        names = ", ".join(below["player_name"].head(3))
        more = f" +{len(below) - 3} more" if len(below) > 3 else ""
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:8px;">'
            f'<span style="font-size:2rem;font-weight:800;color:{LOW_COLOR};line-height:1;">{len(below)}</span>'
            f'<span style="font-size:11px;color:var(--muted);">below TQR {RECOVERY_THRESHOLD}</span></div>'
            f'<div style="font-size:11.5px;color:var(--muted);margin-top:2px;">{names}{more}</div>',
            unsafe_allow_html=True,
        )


def _tile_readiness():
    with st.container(border=True):
        st.markdown("**Team readiness** · ACWR")
        rpe = dl.load_wellness_data()["rpe"]
        team_metrics = training_load.metrics_frame(rpe).dropna(subset=["acwr"])
        if team_metrics.empty:
            st.caption("Not enough training history yet.")
            return
        _, period_end = filters.period()
        in_range = team_metrics.index[team_metrics.index <= pd.Timestamp(period_end)]
        if in_range.empty:
            st.caption("No data at or before the end of this range.")
            return
        ref_date = in_range.max()
        acwr = float(team_metrics.loc[ref_date, "acwr"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=acwr,
            number=dict(font=dict(size=26, color="#f2f2f2"), valueformat=".2f"),
            gauge=dict(
                axis=dict(range=[0, 2], tickfont=dict(size=8, color="#9a9a9a")),
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
        fig.update_layout(height=88, margin=dict(l=14, r=14, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")


def _tile_league_position():
    with st.container(border=True):
        st.markdown("**League position**")
        season = filters.season()
        standings = mc.SEASON_STANDINGS.get(season, [])
        us = next((r for r in standings if r["is_us"]), None)
        if us is None or not standings:
            st.caption("No standings yet.")
            return
        st.markdown(
            f'<div style="font-size:2.2rem;font-weight:800;color:var(--accent);line-height:1;'
            f'margin-bottom:4px;">#{us["pos"]}</div>',
            unsafe_allow_html=True,
        )
        other = standings[0] if us["pos"] != 1 else (standings[1] if len(standings) > 1 else None)
        if other is not None:
            fig = go.Figure(go.Bar(
                x=[us["pts"], other["pts"]], y=["Milano", other["team"]], orientation="h",
                marker_color=["#1655a5", "#8a8a8a"],
                text=[f"{us['pts']} pts", f"{other['pts']} pts"], textposition="outside",
                textfont=dict(color="#f2f2f2", size=10),
            ))
            fig.update_layout(
                height=62, margin=dict(l=8, r=40, t=0, b=0),
                xaxis=dict(visible=False, range=[0, max(us["pts"], other["pts"]) * 1.3]),
                yaxis=dict(tickfont=dict(size=10)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f2f2f2",
            )
            st.plotly_chart(fig, width="stretch")


def _tile_recent_form():
    in_scope = filters.matches_in_scope()
    serie_a1 = sorted((m for m in in_scope if m["competition"] == "Serie A1"), key=lambda m: m["pdate"])
    with st.container(border=True):
        st.markdown("**Recent form** · Serie A1")
        if not serie_a1:
            st.caption("No matches in scope.")
            return
        recent = serie_a1[-3:]
        cols = st.columns(len(recent) + 1)
        for col, m in zip(cols, recent):
            with col:
                color = cv.RESULT_COLORS[mc.result_points(m)]
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="width:12px;height:12px;border-radius:50%;background:{color};margin:0 auto 3px;"></div>'
                    f'<div style="font-size:9.5px;color:var(--muted);white-space:nowrap;">{cv.fmt_date(m["date"])}</div>'
                    f'<div style="font-size:11px;font-weight:700;white-space:nowrap;">{m["score"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with cols[-1]:
            wins = sum(1 for m in serie_a1 if mc.is_win(m))
            st.markdown(
                f'<div style="text-align:center;padding-top:6px;">'
                f'<div style="font-size:0.95rem;font-weight:800;white-space:nowrap;">{wins}W–{len(serie_a1) - wins}L</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _tile_score_patterns():
    with st.container(border=True):
        st.markdown("**Score patterns**")
        matches = filters.matches_in_scope()
        if not matches:
            st.caption("No matches in scope.")
            return
        counts = Counter(m["score"] for m in matches)
        scores = sorted(counts.keys(), key=lambda s: _SCORE_POINTS.get(s, 0))
        fig = go.Figure(go.Bar(
            x=[counts[s] for s in scores], y=scores, orientation="h",
            marker_color=[cv.RESULT_COLORS[_SCORE_POINTS.get(s, 0)] for s in scores],
        ))
        fig.update_layout(height=85, margin=dict(l=10, r=10, t=0, b=10), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")


def _tile_matches_per_month():
    with st.container(border=True):
        st.markdown("**Matches per month**")
        season_matches = mc.matches_for_season(filters.season())
        if not season_matches:
            st.caption("No matches this season.")
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
            labels={"month": "", "count": "", "competition": ""},
        )
        fig.update_layout(height=120, margin=dict(l=10, r=10, t=0, b=10), showlegend=False)
        st.plotly_chart(fig, width="stretch")


def _tile_top_scorers():
    with st.container(border=True):
        st.markdown("**Top scorers** in scope")
        scout = dl.load_scout_data()
        in_scope = {m["date"] for m in filters.matches_in_scope()}
        base = scout[scout["match"].isin(in_scope) & (~scout["is_team"]) & (scout["palla"] == "Totale")]
        points = base[base["fondamentale"].isin(dl.POINT_FONDAMENTALI)].groupby("player_code")["Perfect"].sum()
        appearances = base.groupby("player_code")["match"].nunique()
        stats = pd.DataFrame({"points": points, "appearances": appearances}).fillna(0)
        if stats.empty:
            st.caption("No stats in scope.")
            return
        stats["points"] = stats["points"].astype(int)
        stats["player_name"] = stats.index.map(dl.load_player_names())
        stats = stats.set_index("player_name")
        ranked = stats.sort_values("points", ascending=False).head(3)
        medals = ["🥇", "🥈", "🥉"]
        rows = list(ranked.itertuples())
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 2px;'
            f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
            f'<span style="font-size:0.95rem;">{medals[i]}</span>'
            f'<span style="flex:1;padding-left:6px;font-weight:700;font-size:0.86rem;">{r.Index}</span>'
            f'<span style="color:var(--accent);font-weight:700;font-size:0.86rem;">{int(r.points)} pts</span>'
            f'</div>'
            for i, r in enumerate(rows)
        )
        st.markdown(rows_html, unsafe_allow_html=True)


def _tile_team_shape():
    with st.container(border=True):
        st.markdown("**Team shape** · E%")
        scout = dl.load_scout_data()
        in_scope = {m["date"] for m in filters.matches_in_scope()}
        d = scout[
            scout["match"].isin(in_scope) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ].copy()
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(d["fondamentale"])]
        if len(present) < 3:
            st.caption("Not enough data for a radar.")
            return
        labels = [dl.FONDAMENTALE_ABBR[f] for f in present]
        agg = d.groupby("fondamentale")["E_pct"].agg(["mean", "std"]).reindex(present)
        d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
        last_date = d["pdate"].max()
        last_per_fond = d[d["pdate"] == last_date].groupby("fondamentale")["E_pct"].mean().reindex(present)

        values = (agg["mean"] + 0.5).fillna(0.5).tolist()
        stds = agg["std"].fillna(0).tolist()
        last_values = (last_per_fond + 0.5).fillna(pd.Series(values, index=present)).tolist()
        upper = [v + s for v, s in zip(values, stds)]
        lower = [v - s for v, s in zip(values, stds)]

        fig = go.Figure()
        r_lower, theta_lower = close_polygon(lower, labels)
        fig.add_trace(go.Scatterpolar(r=r_lower, theta=theta_lower, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        r_upper, theta_upper = close_polygon(upper, labels)
        fig.add_trace(go.Scatterpolar(
            r=r_upper, theta=theta_upper, mode="lines", fill="tonext",
            line=dict(width=0), fillcolor="rgba(22,85,165,0.18)", showlegend=False, hoverinfo="skip",
        ))
        r, theta = close_polygon(values, labels)
        fig.add_trace(go.Scatterpolar(r=r, theta=theta, mode="lines", line=dict(color="rgba(22,85,165,0.7)", width=1.2), showlegend=False))
        r_last, theta_last = close_polygon(last_values, labels)
        fig.add_trace(go.Scatterpolar(
            r=r_last, theta=theta_last, mode="lines+markers",
            line=dict(color="#1655a5", width=2), marker=dict(color="#1655a5", size=5), showlegend=False,
        ))
        top = max(max(upper, default=1.0), max(last_values, default=1.0)) * 1.1 or 1.5
        fig.update_layout(**dark_polar_layout([0, top]))
        fig.update_layout(
            polar=dict(radialaxis=dict(showticklabels=False), angularaxis=dict(tickfont=dict(size=8))),
            height=100, margin=dict(l=32, r=32, t=6, b=6),
        )
        st.plotly_chart(fig, width="stretch", theme=None)


def _tile_serve_outcome():
    with st.container(border=True):
        st.markdown("**Serve outcome mix**")
        scout = dl.load_scout_data()
        team = scout[
            (scout["match"] == dl.SEASON_LABEL) & scout["is_team"]
            & (scout["fondamentale"] == "Battuta") & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ]
        if team.empty:
            st.caption("No serve data available.")
            return
        row = team.iloc[0]
        legenda = dl.legenda_fondamentale("Battuta")
        rows = []
        for simbolo, nome, _ in legenda:
            col = _SYMBOL_TO_COL.get(simbolo)
            if col is None:
                continue
            count = row.get(col, 0)
            rows.append({"Outcome": nome, "count": 0 if pd.isna(count) else count})
        d = pd.DataFrame(rows)
        if d.empty or d["count"].sum() == 0:
            st.caption("No serve outcome data.")
            return
        color_map = {nome: _OUTCOME_COLORS.get(simbolo, "#888888") for simbolo, nome, _ in legenda}
        fig = px.pie(d, names="Outcome", values="count", hole=0.55, color="Outcome", color_discrete_map=color_map)
        fig.update_traces(textinfo="percent", textfont_size=10)
        fig.update_layout(height=82, margin=dict(l=10, r=10, t=0, b=6), showlegend=False)
        st.plotly_chart(fig, width="stretch")


def _tile_efficiency_trend():
    with st.container(border=True):
        st.markdown("**Efficiency trend** · Attack")
        scout = dl.load_scout_data()
        in_scope = set(_in_scope_dates())
        d = scout[
            scout["match"].isin(in_scope) & (scout["fondamentale"] == "Attacco")
            & scout["is_team"] & (scout["palla"] == "Totale") & (scout["match"] != dl.SEASON_LABEL)
        ].copy()
        if d.empty:
            st.caption("No data in scope.")
            return
        d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
        d = d.sort_values("pdate")
        fig = go.Figure(go.Scatter(
            x=d["pdate"], y=d["E_pct"], mode="lines+markers",
            line=dict(color="#29B6F6", width=2), marker=dict(size=4),
        ))
        fig.update_layout(
            height=110, margin=dict(l=10, r=10, t=0, b=10),
            yaxis=dict(tickformat=".0%", title=None), xaxis=dict(title=None),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_individual_tqr():
    with st.container(border=True):
        st.markdown("**Individual TQR** trend")
        wellness = dl.load_wellness_data()["wellness"]
        period = filters.filter_by_date_col(wellness)
        daily = period.dropna(subset=["Tqr"]).groupby(["Data", "player_name"], as_index=False)["Tqr"].mean().sort_values("Data")
        if daily.empty:
            st.caption("No wellness data in this date range.")
            return
        fig = px.line(
            daily, x="Data", y="Tqr", color="player_name",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "", "Tqr": "", "player_name": "Player"},
        )
        fig.add_hline(y=RECOVERY_THRESHOLD, line_dash="dash", line_color=LOW_COLOR)
        fig.update_layout(
            height=150, margin=dict(l=10, r=10, t=0, b=10), showlegend=False,
            yaxis=dict(range=[6, 20], **tqr_yaxis_ticks()),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_loads_acwr_chart():
    with st.container(border=True):
        st.markdown("**ACWR** & weekly load")
        rpe = dl.load_wellness_data()["rpe"]
        start, end = filters.period()
        team_metrics = training_load.metrics_frame(rpe)
        d = team_metrics.loc[
            (team_metrics.index >= pd.Timestamp(start)) & (team_metrics.index <= pd.Timestamp(end))
        ].dropna(subset=["acwr"])
        if d.empty:
            st.caption("Not enough training history (needs 28+ days).")
            return
        top = max(2.5, float(d["acwr"].max()) + 0.2)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d.index, y=d["acute"], marker_color="#4C78A8", opacity=0.55))
        fig.add_trace(go.Scatter(x=d.index, y=d["acwr"], yaxis="y2", line=dict(color="#E45756", width=2)))
        fig.add_hrect(y0=0.8, y1=1.3, yref="y2", fillcolor="rgba(84,162,75,0.18)", line_width=0)
        fig.add_hrect(y0=1.5, y1=top, yref="y2", fillcolor="rgba(228,87,86,0.14)", line_width=0)
        fig.update_layout(
            yaxis=dict(title=None), yaxis2=dict(title=None, overlaying="y", side="right", range=[0, top]),
            showlegend=False, height=85, margin=dict(l=10, r=10, t=0, b=10),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_loads_jumps():
    with st.container(border=True):
        st.markdown("**Jumps** · per player")
        salti = dl.load_wellness_data()["salti"]
        period = filters.filter_by_date_col(salti).dropna(subset=["SALTI"])
        if period.empty:
            st.caption("No jump data in this date range.")
            return
        daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
        fig = px.bar(
            daily, x="Data", y="SALTI", color="player_name", barmode="stack",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "", "SALTI": "", "player_name": "Player"},
        )
        fig.update_layout(showlegend=False, height=150, margin=dict(l=10, r=10, t=0, b=10))
        st.plotly_chart(fig, width="stretch")


def _tile_loads_rpe_by_role():
    with st.container(border=True):
        st.markdown("**RPE** by role")
        rpe = dl.load_wellness_data()["rpe"]
        period = filters.filter_by_date_col(rpe)
        d = period.dropna(subset=["Rpe", "RUOLO"]).copy()
        if d.empty:
            st.caption("No RPE data in this period.")
            return
        d["Role"] = d["RUOLO"].map(dl.ROLE_LABELS)
        order = d.groupby("Role")["Rpe"].median().sort_values().index.tolist()
        fig = px.box(
            d, x="Rpe", y="Role", orientation="h", points="outliers",
            category_orders={"Role": order}, color="Role", color_discrete_map=pg.ROLE_COLORS,
            labels={"Rpe": "", "Role": ""},
        )
        fig.update_layout(showlegend=False, height=140, margin=dict(l=0, r=10, t=0, b=10))
        st.plotly_chart(fig, width="stretch")


def _tile_loads_rpe_scatter():
    with st.container(border=True):
        st.markdown("**RPE** vs. duration")
        rpe = dl.load_wellness_data()["rpe"]
        period = filters.filter_by_date_col(rpe)
        d = period.dropna(subset=["Rpe", "Time"])
        if d.empty:
            st.caption("No RPE data in this period.")
            return
        fig = px.scatter(
            d, x="Time", y="Rpe", color="player_name", opacity=0.65,
            color_discrete_map=pc.color_map(d["player_name"].unique()),
            labels={"Time": "", "Rpe": ""},
        )
        fig.update_layout(showlegend=False, height=140, margin=dict(l=0, r=10, t=0, b=10))
        st.plotly_chart(fig, width="stretch")


def _tile_team_profile_bar():
    with st.container(border=True):
        st.markdown("**Team profile** · E% bar")
        scout = dl.load_scout_data()
        team = scout[
            (scout["match"] == dl.SEASON_LABEL) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ].copy()
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(team["fondamentale"])]
        if not present:
            st.caption("No season data yet.")
            return
        order_labels = [dl.FONDAMENTALE_ABBR[f] for f in present]
        team["Fundamental"] = team["fondamentale"].map(dl.FONDAMENTALE_ABBR)
        fig = px.bar(
            team, x="E_pct", y="Fundamental", orientation="h",
            category_orders={"Fundamental": order_labels},
            color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
            labels={"E_pct": "", "Fundamental": ""},
        )
        fig.update_layout(
            coloraxis_showscale=False, xaxis_tickformat=".0%", height=150,
            yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
            margin=dict(l=0, r=10, t=0, b=10),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_squad_overview():
    with st.container(border=True):
        st.markdown("**Squad overview**")
        counts: dict[str, int] = {}
        for p in pg.ALL_PLAYERS:
            counts[p["role"]] = counts.get(p["role"], 0) + 1
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:2px 0;">'
            f'<span style="display:flex;align-items:center;gap:6px;font-size:0.82rem;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{pg.ROLE_COLORS.get(role, "#888")};"></span>{role}</span>'
            f'<span style="font-weight:700;font-size:0.86rem;">{n}</span></div>'
            for role, n in counts.items()
        )
        st.markdown(
            f'<div style="font-size:1.7rem;font-weight:800;line-height:1;margin-bottom:4px;">{len(pg.ALL_PLAYERS)}'
            f'<span style="font-size:11px;color:var(--muted);font-weight:400;"> players</span></div>{rows_html}',
            unsafe_allow_html=True,
        )


def _in_scope_dates():
    return [m["date"] for m in filters.matches_in_scope()]


TILE_RENDERERS = {
    "wellness_low_recovery": _tile_low_recovery,
    "wellness_individual_tqr": _tile_individual_tqr,
    "loads_readiness": _tile_readiness,
    "loads_acwr_chart": _tile_loads_acwr_chart,
    "loads_jumps": _tile_loads_jumps,
    "loads_rpe_by_role": _tile_loads_rpe_by_role,
    "loads_rpe_scatter": _tile_loads_rpe_scatter,
    "matches_league_position": _tile_league_position,
    "matches_recent_form": _tile_recent_form,
    "matches_score_patterns": _tile_score_patterns,
    "matches_per_month": _tile_matches_per_month,
    "scout_top_scorers": _tile_top_scorers,
    "scout_team_shape": _tile_team_shape,
    "scout_serve_outcome": _tile_serve_outcome,
    "scout_efficiency_trend": _tile_efficiency_trend,
    "scout_team_profile_bar": _tile_team_profile_bar,
    "players_squad_overview": _tile_squad_overview,
}

TILES_PER_ROW = 5


def render():
    season = filters.season()
    selected = _render_hero(season)

    with st.container(key="home_grid"):
        for row_start in range(0, len(selected), TILES_PER_ROW):
            row_keys = selected[row_start:row_start + TILES_PER_ROW]
            cols = st.columns(TILES_PER_ROW, gap="small")
            for col, key in zip(cols, row_keys):
                with col:
                    TILE_RENDERERS[key]()
