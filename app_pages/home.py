from collections import Counter

import pandas as pd
import plotly.colors as pcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import match_calendar as mc
import player_colors as pc
import players_grid as pg
import training_load
from ui_helpers import (
    GOOD_COLOR,
    LOW_COLOR,
    TQR_GREEN_MIN,
    TQR_MAX,
    TQR_MIN,
    WARN_COLOR,
    close_polygon,
    dark_polar_layout,
    tqr_recovery_label,
    tqr_yaxis_ticks,
    tqr_zone_color,
)
import calendar_view as cv

# Same convention as scout_statistiche.py's own OUTCOME_COLORS/SYMBOL_TO_COL
# -- duplicated here (rather than imported across pages) just for the two
# outcome-mix tiles below.
_OUTCOME_COLORS = {"=": "#7A1B1B", "-": "#F58518", "!": "#FDD835", "+": "#54A24B", "#": "#1B5E20", "/": "#E45756"}
_SYMBOL_TO_COL = {"=": "Err", "-": "Neg", "!": "Neutral", "+": "Pos", "#": "Perfect", "/": "Slash"}
_SCORE_POINTS = {"3-0": 3, "3-1": 3, "3-2": 2, "2-3": 1, "1-3": 0, "0-3": 0}
_MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Every plotly tile's own chart draws at this height, and every tile's
# bordered card (chart or text) is held to this same min-height via CSS
# below -- one standard footprint for every card on the grid, chart or
# not, instead of each tile picking its own (previously 62-150px).
TILE_CHART_HEIGHT = 132
# Tall enough that even the longest two-line titles (a "**Title** ·
# subtitle · dd Mon" snapshot title wrapping in a narrow quarter-width
# column) fit without pushing that card past every other one's height --
# min-height on every card (not just the tall ones) is what makes the
# whole row line up edge to edge.
TILE_CARD_MIN_HEIGHT = 228

# The 12 tiles that always show, pinned in this exact 3-row/4-column
# order -- not user-configurable, per an explicit request for a stable
# "core" dashboard instead of everything being toggleable. Everything
# else lives in OPTIONAL_CATALOG below, toggled through the Customize
# popover same as before.
FIXED_TILES = [
    "matches_league_position", "matches_recent_form", "scout_top_scorers", "scout_setting_points",
    "scout_top_efficiency_attack", "scout_attack_outcome", "scout_efficiency_trend_attack", "scout_setting_errors",
    "loads_readiness", "loads_acwr_chart", "wellness_low_recovery", "wellness_team_tqr_gauge",
]

# Every OTHER card Home can show, keyed for the Customize popover's
# checkboxes -- unchecked by default, since the 12 fixed tiles above are
# already the "always visible" core; these are opt-in extras. Grouped by
# source page for the popover's own sections; that grouping isn't shown
# on the page itself (titles alone carry enough context for a card this
# small).
OPTIONAL_CATALOG = [
    ("wellness_team_tqr_trend", "Team TQR trend", "Wellness"),
    ("wellness_individual_tqr", "Individual TQR trends", "Wellness"),
    ("loads_jumps", "Jumps per player", "Loads"),
    ("loads_rpe_scatter", "RPE vs. session duration", "Loads"),
    ("matches_score_patterns", "Score patterns", "Matches"),
    ("matches_per_month", "Matches per month", "Matches"),
    ("scout_top_efficiency_serve", "Top efficiency · Serve", "Scout & Stats"),
    ("scout_top_efficiency_receive", "Top efficiency · Receive", "Scout & Stats"),
    ("scout_team_shape", "Team shape radar", "Scout & Stats"),
    ("scout_serve_outcome", "Serve outcome mix", "Scout & Stats"),
    ("scout_efficiency_trend_serve", "Efficiency trend · Serve", "Scout & Stats"),
    ("scout_team_profile_bar", "Team profile · E% bar", "Scout & Stats"),
]

# Every tile is either a "trend" (season-wide, ignores the sidebar's period
# entirely -- trend lines, per-day/per-month charts, match results, season
# point totals) or a "snapshot" (exclusively the single latest available
# data point, also period-independent). Drives both the border color
# (green/yellow, see HERO_CSS below) and which data-scoping helper each
# tile function calls -- _season_wide_matches()/raw dataframes for trend
# tiles, _latest_match()/_latest_day() for snapshot ones.
TILE_SCOPE = {
    "wellness_low_recovery": "snapshot",
    "wellness_team_tqr_gauge": "snapshot",
    "wellness_team_tqr_trend": "trend",
    "wellness_individual_tqr": "trend",
    "loads_readiness": "snapshot",
    "loads_acwr_chart": "trend",
    "loads_jumps": "trend",
    "loads_rpe_scatter": "snapshot",
    "matches_league_position": "snapshot",
    "matches_recent_form": "trend",
    "matches_score_patterns": "trend",
    "matches_per_month": "trend",
    "scout_top_scorers": "trend",
    "scout_top_efficiency_attack": "snapshot",
    "scout_top_efficiency_serve": "snapshot",
    "scout_top_efficiency_receive": "snapshot",
    "scout_team_shape": "snapshot",
    "scout_serve_outcome": "snapshot",
    "scout_attack_outcome": "snapshot",
    "scout_efficiency_trend_attack": "trend",
    "scout_efficiency_trend_serve": "trend",
    "scout_setting_points": "snapshot",
    "scout_setting_errors": "snapshot",
    "scout_team_profile_bar": "snapshot",
}


def _tile_box_key(tile_key: str) -> str:
    bucket = "trend" if TILE_SCOPE[tile_key] == "trend" else "snap"
    return f"home_tile_{bucket}_{tile_key}"


def _tile_title(title_md: str, latest_date=None):
    """Renders a tile's title -- trend tiles (latest_date=None) just get
    the plain "**Title**" markdown; snapshot tiles get a small muted date
    suffix next to it, so it's always clear which single day/match the
    card's number reflects."""
    if latest_date is None:
        st.markdown(title_md)
        return
    date_txt = latest_date.strftime("%d %b") if hasattr(latest_date, "strftime") else str(latest_date)
    st.markdown(
        f'{title_md} <span style="font-size:10px;color:var(--muted);font-weight:400;">· {date_txt}</span>',
        unsafe_allow_html=True,
    )


def _latest_match() -> dict | None:
    """Most recent match in season+competition scope, ignoring the
    sidebar's period -- the single data point every "snapshot" match/scout
    tile reduces to."""
    matches = filters.matches_full_season()
    return matches[0] if matches else None


HERO_CSS = f"""
<style>
    /* No card/box around the name+logo+Customize row on purpose -- just
       the content itself, unboxed, sitting directly on the page
       background like the sidebar's own brand block does. */
    .st-key-home_hero_box {{
        padding: 6px 18px;
        margin-bottom: 4px;
    }}
    .st-key-home_customize_box button {{ white-space: nowrap; }}
    /* Trend/season-wide tiles (full season regardless of the sidebar's
       period) get a green border; latest-snapshot tiles (today's/most
       recent single data point only) get a yellow one -- the two-bucket
       split TILE_SCOPE encodes for every tile on the page. */
    [class*="st-key-home_tile_trend_"] {{ border-color: {GOOD_COLOR} !important; }}
    [class*="st-key-home_tile_snap_"] {{ border-color: {WARN_COLOR} !important; }}
    /* Dashboard tiles: dense grid, small cards -- every chart inside is
       sized to match (see TILE_CHART_HEIGHT); this trims Streamlit's
       default inter-element spacing inside each card, which was the
       biggest source of the page needing to scroll. */
    .st-key-home_grid [data-testid="stElementContainer"] {{ margin-bottom: 2px !important; }}
    /* One standard card footprint for every tile, chart or text-only, so
       a row of mixed tile types still lines up edge to edge instead of
       each card hugging its own (different) content height. Targets the
       actual bordered container (a plain stVerticalBlock in this
       Streamlit version, two levels below stColumn: stColumn's own
       auto-wrapper stVerticalBlock, then stLayoutWrapper, then the real
       bordered one from st.container(border=True)) -- there's no
       separate "border wrapper" testid to key off directly. */
    .st-key-home_grid [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {{
        min-height: {TILE_CARD_MIN_HEIGHT}px;
    }}
</style>
"""


def _render_hero(season: str) -> list[str]:
    """Returns the OPTIONAL tile keys currently checked in the Customize
    popover -- built straight from this run's checkboxes (rather than read
    back from st.session_state under a different key) so render() always
    sees this run's actual selection immediately, not whatever was true
    before this rerun. The 12 FIXED_TILES aren't listed here at all --
    they always render, unconditionally, in render()."""
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
                f'<div style="color:var(--muted);font-size:0.78rem;margin-top:1px;">Technical Staff · A1 Women\'s · {filters.caption()}</div>',
                unsafe_allow_html=True,
            )

        with col_customize, st.container(key="home_customize_box"), st.popover("Customize", icon=":material/tune:", width="stretch"):
            st.markdown("**Add extra cards**")
            st.caption(
                "The 12 cards on the dashboard are fixed. These are opt-in extras -- "
                "cards with a "
                f'<span style="color:{GOOD_COLOR};">green</span> border always span the whole season; '
                f'cards with a <span style="color:{WARN_COLOR};">yellow</span> border show only the single '
                "latest available day or match (its date sits next to the title).",
                unsafe_allow_html=True,
            )
            by_page: dict[str, list[tuple[str, str]]] = {}
            for key, label, page in OPTIONAL_CATALOG:
                by_page.setdefault(page, []).append((key, label))
            for i, (page, items) in enumerate(by_page.items()):
                border = "border-top:1px solid var(--line);padding-top:8px;" if i > 0 else ""
                st.markdown(
                    f'<div style="color:var(--muted);font-size:11px;text-transform:uppercase;'
                    f'letter-spacing:0.06em;font-weight:700;margin-top:8px;{border}">{page}</div>',
                    unsafe_allow_html=True,
                )
                for key, label in items:
                    if st.checkbox(label, value=False, key=f"home_tile_{key}"):
                        selected.append(key)
    return selected


def _tile_low_recovery(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        wellness = dl.load_wellness_data()["wellness"]
        if wellness.empty:
            _tile_title("**Low recovery**")
            st.caption("No data available.")
            return
        last_date = wellness["Data"].max()
        _tile_title("**Low recovery**", last_date)
        last_day = wellness[wellness["Data"] == last_date].sort_values("Tqr")
        below = last_day[last_day["Tqr"] < TQR_GREEN_MIN]
        if below.empty:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding-top:6px;">'
                f'<span style="font-size:1.4rem;">✅</span>'
                f'<span style="color:{GOOD_COLOR};font-weight:700;font-size:0.95rem;">All clear</span></div>',
                unsafe_allow_html=True,
            )
            return
        # Full roster of names, not a "+N more" truncation -- wraps across
        # as many lines as it needs, since the card no longer has to hug a
        # single-line height.
        names_html = ", ".join(below["player_name"].tolist())
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:8px;">'
            f'<span style="font-size:2rem;font-weight:800;color:{LOW_COLOR};line-height:1;">{len(below)}</span>'
            f'<span style="font-size:11px;color:var(--muted);">below TQR {TQR_GREEN_MIN}</span></div>'
            f'<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.45;">{names_html}</div>',
            unsafe_allow_html=True,
        )


def _tile_team_tqr_gauge(tile_key: str):
    """Same gauge language as Team readiness/ACWR beside it, and as the
    Players page's own per-player TQR gauge -- the team's most recent-day
    average TQR, banded by CoreBo's 3-zone scale, with the recovery label
    spelled out underneath so the color isn't the only thing carrying
    the meaning."""
    with st.container(border=True, key=_tile_box_key(tile_key)):
        wellness = dl.load_wellness_data()["wellness"]
        d = wellness.dropna(subset=["Tqr"])
        if d.empty:
            _tile_title("**Team TQR**")
            st.caption("No data available.")
            return
        last_date = d["Data"].max()
        _tile_title("**Team TQR**", last_date)
        tqr = float(d.loc[d["Data"] == last_date, "Tqr"].mean())
        color = tqr_zone_color(tqr)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=tqr,
            number=dict(font=dict(size=24, color="#f2f2f2"), valueformat=".1f"),
            gauge=dict(
                axis=dict(range=[TQR_MIN, TQR_MAX], tickvals=[TQR_MIN, 13, TQR_GREEN_MIN, TQR_MAX], tickfont=dict(size=8, color="#9a9a9a")),
                bar=dict(color="#ffffff", thickness=0.28),
                bgcolor="rgba(0,0,0,0)",
                steps=[
                    {"range": [TQR_MIN, 13], "color": LOW_COLOR},
                    {"range": [13, TQR_GREEN_MIN], "color": WARN_COLOR},
                    {"range": [TQR_GREEN_MIN, TQR_MAX], "color": GOOD_COLOR},
                ],
            ),
        ))
        fig.update_layout(height=TILE_CHART_HEIGHT - 20, margin=dict(l=14, r=14, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f'<div style="text-align:center;font-size:11px;color:{color};font-weight:700;">{tqr_recovery_label(tqr)}</div>',
            unsafe_allow_html=True,
        )


def _tile_team_tqr_trend(tile_key: str):
    """Mini version of the Wellness page's own Team TQR trend, over the
    whole season regardless of the sidebar's period: mean line with a
    faint +/- std band around it, y-axis ticks colored by the same
    3-zone scale as every other TQR display in the app -- no separate
    threshold line needed, the ticks already carry that."""
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Team TQR** trend")
        wellness = dl.load_wellness_data()["wellness"]
        daily = (
            wellness.groupby("Data")["Tqr"].agg(["mean", "std"]).reset_index()
            .dropna(subset=["mean"]).sort_values("Data")
        )
        if daily.empty:
            st.caption("No data available.")
            return
        daily["std"] = daily["std"].fillna(0)
        upper = (daily["mean"] + daily["std"]).clip(upper=TQR_MAX)
        lower = (daily["mean"] - daily["std"]).clip(lower=TQR_MIN)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["Data"], y=lower, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=daily["Data"], y=upper, mode="lines", fill="tonexty",
            line=dict(width=0), fillcolor="rgba(46,204,113,0.18)", showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=daily["Data"], y=daily["mean"], mode="lines", line=dict(color="#2ecc71", width=2), showlegend=False,
        ))
        fig.update_layout(
            height=TILE_CHART_HEIGHT, margin=dict(l=10, r=10, t=0, b=10),
            yaxis=dict(range=[TQR_MIN, TQR_MAX], **tqr_yaxis_ticks()), xaxis_title=None,
        )
        st.plotly_chart(fig, width="stretch")


def _tile_readiness(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        rpe = dl.load_wellness_data()["rpe"]
        team_metrics = training_load.metrics_frame(rpe).dropna(subset=["acwr"])
        if team_metrics.empty:
            _tile_title("**Team readiness** · ACWR")
            st.caption("Not enough training history yet.")
            return
        ref_date = team_metrics.index.max()
        _tile_title("**Team readiness** · ACWR", ref_date)
        acwr = float(team_metrics.loc[ref_date, "acwr"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=acwr,
            number=dict(font=dict(size=24, color="#f2f2f2"), valueformat=".2f"),
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
        fig.update_layout(height=TILE_CHART_HEIGHT - 20, margin=dict(l=14, r=14, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")


def _tile_league_position(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
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
                height=TILE_CHART_HEIGHT - 60, margin=dict(l=8, r=40, t=0, b=0),
                xaxis=dict(visible=False, range=[0, max(us["pts"], other["pts"]) * 1.3]),
                yaxis=dict(tickfont=dict(size=10)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f2f2f2",
            )
            st.plotly_chart(fig, width="stretch")


def _tile_recent_form(tile_key: str):
    season_matches = filters.matches_full_season()
    serie_a1 = sorted((m for m in season_matches if m["competition"] == "Serie A1"), key=lambda m: m["pdate"])
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Recent form** · Serie A1")
        if not serie_a1:
            st.caption("No Serie A1 matches this season.")
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


def _tile_score_patterns(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Score patterns**")
        matches = filters.matches_full_season()
        if not matches:
            st.caption("No matches this season.")
            return
        counts = Counter(m["score"] for m in matches)
        scores = sorted(counts.keys(), key=lambda s: _SCORE_POINTS.get(s, 0))
        fig = go.Figure(go.Bar(
            x=[counts[s] for s in scores], y=scores, orientation="h",
            marker_color=[cv.RESULT_COLORS[_SCORE_POINTS.get(s, 0)] for s in scores],
        ))
        fig.update_layout(height=TILE_CHART_HEIGHT - 20, margin=dict(l=10, r=10, t=0, b=10), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, width="stretch")


def _tile_matches_per_month(tile_key: str):
    """One of the trend/season-wide tiles: "per month" only means
    something across a whole season, so this always spans it regardless
    of the sidebar's period (see TILE_SCOPE)."""
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Matches per month** · season")
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
        fig.update_layout(height=TILE_CHART_HEIGHT, margin=dict(l=10, r=10, t=0, b=10), showlegend=False)
        st.plotly_chart(fig, width="stretch")


def _tile_top_scorers(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Top scorers** · season")
        in_window = {m["date"] for m in filters.matches_full_season()}
        scout = dl.load_scout_data()
        base = scout[scout["match"].isin(in_window) & (~scout["is_team"]) & (scout["palla"] == "Totale")]
        points = base[base["fondamentale"].isin(dl.POINT_FONDAMENTALI)].groupby("player_code")["Perfect"].sum()
        appearances = base.groupby("player_code")["match"].nunique()
        stats = pd.DataFrame({"points": points, "appearances": appearances}).fillna(0)
        if stats.empty:
            st.caption("No stats this season.")
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


def _render_top_efficiency(fondamentale: str, latest: dict):
    """Quality leaderboard for the latest match only -- best E% for
    `fondamentale` among players who've actually had enough touches that
    match (dl.MIN_RELIABLE_N) to trust the number, so a 1-for-1 outlier
    can't top the list."""
    scout = dl.load_scout_data()
    base = scout[
        (scout["match"] == latest["date"]) & (~scout["is_team"])
        & (scout["fondamentale"] == fondamentale) & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
    ]
    if base.empty:
        st.caption("No data for this match.")
        return
    agg = base.set_index("player_name")[["E_pct", "Tot"]]
    agg = agg[agg["Tot"] >= dl.MIN_RELIABLE_N]
    if agg.empty:
        st.caption("Not enough volume in this match.")
        return
    ranked = agg.sort_values("E_pct", ascending=False).head(3)
    medals = ["🥇", "🥈", "🥉"]
    rows = list(ranked.reset_index().itertuples())
    rows_html = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 2px;'
        f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
        f'<span style="font-size:0.95rem;">{medals[i]}</span>'
        f'<span style="flex:1;padding-left:6px;font-weight:700;font-size:0.86rem;">{r.player_name}</span>'
        f'<span style="color:var(--accent);font-weight:700;font-size:0.86rem;">{r.E_pct * 100:.0f}%</span>'
        f'</div>'
        for i, r in enumerate(rows)
    )
    st.markdown(rows_html, unsafe_allow_html=True)


def _tile_top_efficiency(tile_key: str, title: str, fondamentale: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title(title)
            st.caption("No matches yet.")
            return
        _tile_title(title, latest["pdate"])
        _render_top_efficiency(fondamentale, latest)


def _tile_top_efficiency_attack(tile_key: str):
    _tile_top_efficiency(tile_key, "**Top efficiency** · Attack", "Attacco")


def _tile_top_efficiency_serve(tile_key: str):
    _tile_top_efficiency(tile_key, "**Top efficiency** · Serve", "Battuta")


def _tile_top_efficiency_receive(tile_key: str):
    _tile_top_efficiency(tile_key, "**Top efficiency** · Receive", "Ricezione")


def _tile_team_shape(tile_key: str):
    """Exclusively the latest match's per-fundamental E% -- a single
    filled polygon (no season aggregate/std band anymore) since a
    snapshot tile reduces to one match's own numbers."""
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Team shape** · E%")
            st.caption("No matches yet.")
            return
        _tile_title("**Team shape** · E%", latest["pdate"])
        scout = dl.load_scout_data()
        d = scout[
            (scout["match"] == latest["date"]) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ]
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(d["fondamentale"])]
        if len(present) < 3:
            st.caption("Not enough data for a radar.")
            return
        labels = [dl.FONDAMENTALE_ABBR[f] for f in present]
        per_fond = d.groupby("fondamentale")["E_pct"].mean().reindex(present)
        values = (per_fond + 0.5).fillna(0.5).tolist()

        fig = go.Figure()
        r, theta = close_polygon(values, labels)
        fig.add_trace(go.Scatterpolar(
            r=r, theta=theta, mode="lines+markers", fill="toself",
            line=dict(color="#1655a5", width=2), marker=dict(color="#1655a5", size=5),
            fillcolor="rgba(22,85,165,0.25)", showlegend=False,
        ))
        top = (max(values, default=1.0) * 1.1) or 1.5
        fig.update_layout(**dark_polar_layout([0, top]))
        fig.update_layout(
            polar=dict(radialaxis=dict(showticklabels=False), angularaxis=dict(tickfont=dict(size=8))),
            height=TILE_CHART_HEIGHT - 32, margin=dict(l=32, r=32, t=6, b=6),
        )
        st.plotly_chart(fig, width="stretch", theme=None)


def _home_scout_team_agg(scout: pd.DataFrame, fondamentale: str, match_dates: set[str]) -> dict | None:
    """Sums raw outcome counts for the team's rows of `fondamentale`
    across every match sheet in `match_dates` -- the pre-computed
    season-total row these tiles used to read can't be narrowed down to
    a single match, so this recomputes from the raw per-match rows
    instead. Callers here pass a single latest-match date (snapshot
    tiles), but it works for any set."""
    d = scout[
        scout["match"].isin(match_dates) & scout["is_team"]
        & (scout["fondamentale"] == fondamentale) & (scout["palla"] == "Totale")
    ]
    if d.empty:
        return None
    cols = ["Tot", "Err", "Slash", "Neg", "Neutral", "Pos", "Perfect"]
    return {c: int(d[c].fillna(0).sum()) for c in cols if c in d.columns}


def _outcome_mix_bar(fondamentale: str, latest: dict):
    """Slim single 100%-stacked horizontal bar of the latest match's
    outcome mix -- a compact, small-multiple-friendly stand-in for the
    full Scout & Stats outcome-mix chart, which needs far more room than
    a Home tile has. A bar reads the mix (length = share) more reliably
    than the donut this used to be (angle is harder to compare than
    length), and stacks the same colors used everywhere else in the app."""
    scout = dl.load_scout_data()
    counts = _home_scout_team_agg(scout, fondamentale, {latest["date"]})
    if counts is None:
        st.caption("No data for this match.")
        return
    legenda = dl.legenda_fondamentale(fondamentale)
    rows = []
    for simbolo, _nome, _ in legenda:
        col = _SYMBOL_TO_COL.get(simbolo)
        count = counts.get(col, 0) if col else 0
        if count <= 0:
            continue
        rows.append({"Outcome": simbolo, "count": count, "y": fondamentale})
    d = pd.DataFrame(rows)
    if d.empty:
        st.caption("No outcome data.")
        return
    fig = px.bar(
        d, x="count", y="y", color="Outcome", orientation="h",
        color_discrete_map=_OUTCOME_COLORS,
        labels={"count": "", "y": ""},
    )
    fig.update_traces(hovertemplate="%{fullData.name}: %{x}<extra></extra>")
    fig.update_layout(
        barmode="stack", barnorm="percent", showlegend=False,
        height=TILE_CHART_HEIGHT - 60, margin=dict(l=0, r=10, t=10, b=25),
        xaxis=dict(ticksuffix="%"), yaxis=dict(showticklabels=False),
    )
    st.plotly_chart(fig, width="stretch")


def _tile_serve_outcome(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Serve outcome mix**")
            st.caption("No matches yet.")
            return
        _tile_title("**Serve outcome mix**", latest["pdate"])
        _outcome_mix_bar("Battuta", latest)


def _tile_attack_outcome(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Attack outcome mix**")
            st.caption("No matches yet.")
            return
        _tile_title("**Attack outcome mix**", latest["pdate"])
        _outcome_mix_bar("Attacco", latest)


def _render_efficiency_trend(fondamentale: str):
    match_dates = {m["date"] for m in filters.matches_full_season()}
    scout = dl.load_scout_data()
    d = scout[
        scout["match"].isin(match_dates) & (scout["fondamentale"] == fondamentale)
        & scout["is_team"] & (scout["palla"] == "Totale") & (scout["match"] != dl.SEASON_LABEL)
    ].copy()
    if d.empty:
        st.caption("No data this season.")
        return
    d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
    d = d.sort_values("pdate")
    if len(d) == 1:
        # A "trend" line with a single point degenerates into an
        # unreadable Plotly axis (it zooms to sub-second ticks around
        # that one x-value) -- a plain single-match readout is honest
        # about there only being one match played so far this season.
        row = d.iloc[0]
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:8px;padding-top:10px;">'
            f'<span style="font-size:2rem;font-weight:800;color:#29B6F6;line-height:1;">{row["E_pct"] * 100:.0f}%</span>'
            f'<span style="font-size:11px;color:var(--muted);">only 1 match so far ({mc.match_label(row["match"])})</span></div>',
            unsafe_allow_html=True,
        )
        return
    fig = go.Figure(go.Scatter(
        x=d["pdate"], y=d["E_pct"], mode="lines+markers", fill="tozeroy",
        line=dict(color="#29B6F6", width=2), marker=dict(size=5), fillcolor="rgba(41,182,246,0.15)",
    ))
    fig.update_layout(
        height=TILE_CHART_HEIGHT, margin=dict(l=10, r=10, t=0, b=10),
        yaxis=dict(tickformat=".0%", title=None), xaxis=dict(title=None),
    )
    st.plotly_chart(fig, width="stretch")


def _tile_efficiency_trend_attack(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Efficiency trend** · Attack")
        _render_efficiency_trend("Attacco")


def _tile_efficiency_trend_serve(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Efficiency trend** · Serve")
        _render_efficiency_trend("Battuta")


def _tile_individual_tqr(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Individual TQR** trend")
        wellness = dl.load_wellness_data()["wellness"]
        daily = wellness.dropna(subset=["Tqr"]).groupby(["Data", "player_name"], as_index=False)["Tqr"].mean().sort_values("Data")
        if daily.empty:
            st.caption("No wellness data available.")
            return
        fig = px.line(
            daily, x="Data", y="Tqr", color="player_name",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "", "Tqr": "", "player_name": "Player"},
        )
        fig.update_layout(
            height=TILE_CHART_HEIGHT + 20, margin=dict(l=10, r=10, t=0, b=10), showlegend=False,
            yaxis=dict(range=[TQR_MIN, TQR_MAX], **tqr_yaxis_ticks()),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_loads_acwr_chart(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**ACWR** & weekly load")
        rpe = dl.load_wellness_data()["rpe"]
        team_metrics = training_load.metrics_frame(rpe)
        d = team_metrics.dropna(subset=["acwr"])
        if d.empty:
            st.caption("Not enough training history (needs 28+ days of data).")
            return
        top = max(2.5, float(d["acwr"].max()) + 0.2)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d.index, y=d["acute"], marker_color="#4C78A8", opacity=0.55))
        fig.add_trace(go.Scatter(x=d.index, y=d["acwr"], yaxis="y2", line=dict(color="#E45756", width=2)))
        fig.add_hrect(y0=0.8, y1=1.3, yref="y2", fillcolor="rgba(84,162,75,0.18)", line_width=0)
        fig.add_hrect(y0=1.5, y1=top, yref="y2", fillcolor="rgba(228,87,86,0.14)", line_width=0)
        fig.update_layout(
            yaxis=dict(title=None), yaxis2=dict(title=None, overlaying="y", side="right", range=[0, top]),
            showlegend=False, height=TILE_CHART_HEIGHT - 20, margin=dict(l=10, r=10, t=0, b=10),
        )
        st.plotly_chart(fig, width="stretch")


def _tile_loads_jumps(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        st.markdown("**Jumps** · per player")
        salti = dl.load_wellness_data()["salti"].dropna(subset=["SALTI"])
        if salti.empty:
            st.caption("No jump data available.")
            return
        daily = salti.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
        fig = px.bar(
            daily, x="Data", y="SALTI", color="player_name", barmode="stack",
            color_discrete_map=pc.color_map(daily["player_name"].unique()),
            labels={"Data": "", "SALTI": "", "player_name": "Player"},
        )
        fig.update_layout(showlegend=False, height=TILE_CHART_HEIGHT + 20, margin=dict(l=10, r=10, t=0, b=10))
        st.plotly_chart(fig, width="stretch")


def _tile_loads_rpe_scatter(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        rpe_all = dl.load_wellness_data()["rpe"].dropna(subset=["Rpe", "Time"])
        if rpe_all.empty:
            _tile_title("**RPE** vs. duration")
            st.caption("No RPE data available.")
            return
        last_date = rpe_all["Data"].max()
        _tile_title("**RPE** vs. duration", last_date)
        rpe = rpe_all[rpe_all["Data"] == last_date]
        fig = px.scatter(
            rpe, x="Time", y="Rpe", color="player_name", opacity=0.65,
            color_discrete_map=pc.color_map(rpe["player_name"].unique()),
            labels={"Time": "", "Rpe": ""},
        )
        fig.update_layout(showlegend=False, height=TILE_CHART_HEIGHT + 20, margin=dict(l=0, r=10, t=0, b=10))
        st.plotly_chart(fig, width="stretch")


# Attack-only zones and the roles that hit from each -- same mapping as
# Scout & Stats' own Setting distribution court, just cropped down to the
# net-side strip (y 6-9) since a Home tile has no room for the full court
# silhouette (net line, back-row P5/P6/P1) that chart also draws.
_ZONE_X = {"P4": (0, 3), "P3": (3, 6), "P2": (6, 9)}
_ZONE_ROLES = {"P4": ["Outside Hitter"], "P3": ["Middle Blocker"], "P2": ["Opposite"]}


def _home_attack_by_role(scout: pd.DataFrame, match_dates: set[str]) -> pd.DataFrame:
    d = scout[
        scout["match"].isin(match_dates) & (~scout["is_team"])
        & (scout["fondamentale"] == "Attacco") & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
    ].copy()
    if d.empty:
        return d
    names = dl.load_player_names()
    roles = dl.load_player_roles()
    name_to_role = {names[code]: dl.ROLE_LABELS.get(r, r) for code, r in roles.items() if code in names}
    d["Role"] = d["player_name"].map(name_to_role)
    return d


def _mini_zone_court(attack: pd.DataFrame, count_col: str, colorscale: str):
    """Cropped court strip -- just the P4/P3/P2 attack zones near the
    net, dropping the rest of the court silhouette a Home tile has no
    room for -- colored by `count_col` (raw counts, e.g. "Perfect" for
    points or "Err" for errors) as a share of each zone's own attacks."""
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=6, x1=9, y1=9, line=dict(color="rgba(255,255,255,0.5)", width=2))
    for x in (3, 6):
        fig.add_shape(type="line", x0=x, y0=6, x1=x, y1=9, line=dict(color="rgba(255,255,255,0.25)", width=1))
    any_data = False
    for zone, (x0, x1) in _ZONE_X.items():
        sub = attack[attack["Role"].isin(_ZONE_ROLES[zone])] if not attack.empty else attack
        tot = sub["Tot"].sum() if not sub.empty else 0
        value = (sub[count_col].sum() / tot) if tot > 0 else None
        if tot > 0:
            any_data = True
        t = 0.0 if value is None else max(0.0, min(1.0, value / 0.6))
        color = "rgba(255,255,255,0.08)" if value is None else pcolors.sample_colorscale(colorscale, [t])[0].replace("rgb", "rgba").replace(")", ",0.75)")
        fig.add_shape(type="rect", x0=x0, y0=6, x1=x1, y1=9, fillcolor=color, line=dict(color="rgba(255,255,255,0.5)", width=1))
        text = "—" if value is None else f"{value * 100:.0f}%"
        fig.add_annotation(x=(x0 + x1) / 2, y=7.5, showarrow=False, font=dict(color="#ffffff", size=13), text=f"<b>{zone}</b><br>{text}")
    fig.update_xaxes(visible=False, range=[-0.2, 9.2])
    fig.update_yaxes(visible=False, range=[5.7, 9.3], scaleanchor="x")
    fig.update_layout(height=TILE_CHART_HEIGHT - 10, margin=dict(l=10, r=10, t=0, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    if not any_data:
        st.caption("No attacks in this match.")


def _tile_setting_points(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Distribution** · points (P4/P3/P2)")
            st.caption("No matches yet.")
            return
        _tile_title("**Distribution** · points (P4/P3/P2)", latest["pdate"])
        attack = _home_attack_by_role(dl.load_scout_data(), {latest["date"]})
        _mini_zone_court(attack, "Perfect", "Greens")


def _tile_setting_errors(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Distribution** · errors (P4/P3/P2)")
            st.caption("No matches yet.")
            return
        _tile_title("**Distribution** · errors (P4/P3/P2)", latest["pdate"])
        attack = _home_attack_by_role(dl.load_scout_data(), {latest["date"]})
        _mini_zone_court(attack, "Err", "Reds")


def _tile_team_profile_bar(tile_key: str):
    with st.container(border=True, key=_tile_box_key(tile_key)):
        latest = _latest_match()
        if latest is None:
            _tile_title("**Team profile** · E% bar")
            st.caption("No matches yet.")
            return
        _tile_title("**Team profile** · E% bar", latest["pdate"])
        scout = dl.load_scout_data()
        rows = []
        for fond in dl.FONDAMENTALE_ORDER:
            counts = _home_scout_team_agg(scout, fond, {latest["date"]})
            if counts is None or counts["Tot"] <= 0:
                continue
            e_pct = dl.e_pct_from_counts(fond, counts)
            if e_pct is None:
                continue
            rows.append({"Fundamental": dl.FONDAMENTALE_ABBR[fond], "E_pct": e_pct})
        if not rows:
            st.caption("No data for this match.")
            return
        team = pd.DataFrame(rows)
        order_labels = team["Fundamental"].tolist()
        fig = px.bar(
            team, x="E_pct", y="Fundamental", orientation="h",
            category_orders={"Fundamental": order_labels},
            color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
            labels={"E_pct": "", "Fundamental": ""},
        )
        fig.update_layout(
            coloraxis_showscale=False, xaxis_tickformat=".0%", height=TILE_CHART_HEIGHT + 20,
            yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
            margin=dict(l=0, r=10, t=0, b=10),
        )
        st.plotly_chart(fig, width="stretch")


TILE_RENDERERS = {
    "wellness_low_recovery": _tile_low_recovery,
    "wellness_team_tqr_gauge": _tile_team_tqr_gauge,
    "wellness_team_tqr_trend": _tile_team_tqr_trend,
    "wellness_individual_tqr": _tile_individual_tqr,
    "loads_readiness": _tile_readiness,
    "loads_acwr_chart": _tile_loads_acwr_chart,
    "loads_jumps": _tile_loads_jumps,
    "loads_rpe_scatter": _tile_loads_rpe_scatter,
    "matches_league_position": _tile_league_position,
    "matches_recent_form": _tile_recent_form,
    "matches_score_patterns": _tile_score_patterns,
    "matches_per_month": _tile_matches_per_month,
    "scout_top_scorers": _tile_top_scorers,
    "scout_top_efficiency_attack": _tile_top_efficiency_attack,
    "scout_top_efficiency_serve": _tile_top_efficiency_serve,
    "scout_top_efficiency_receive": _tile_top_efficiency_receive,
    "scout_team_shape": _tile_team_shape,
    "scout_serve_outcome": _tile_serve_outcome,
    "scout_attack_outcome": _tile_attack_outcome,
    "scout_efficiency_trend_attack": _tile_efficiency_trend_attack,
    "scout_efficiency_trend_serve": _tile_efficiency_trend_serve,
    "scout_setting_points": _tile_setting_points,
    "scout_setting_errors": _tile_setting_errors,
    "scout_team_profile_bar": _tile_team_profile_bar,
}

# 4 (not 5) -- gives each card more room now that several draw a real
# chart rather than a thin sparkline, and divides the 12 fixed tiles into
# exactly 3 clean rows with no leftover column.
TILES_PER_ROW = 4


def render():
    season = filters.season()
    selected = _render_hero(season)
    all_keys = FIXED_TILES + selected

    with st.container(key="home_grid"):
        for row_start in range(0, len(all_keys), TILES_PER_ROW):
            row_keys = all_keys[row_start:row_start + TILES_PER_ROW]
            # A short final row uses exactly as many columns as it has
            # tiles (not the full TILES_PER_ROW) so those cards stretch
            # to fill the row's width instead of leaving empty columns
            # trailing off to one side.
            cols = st.columns(len(row_keys), gap="small")
            for col, key in zip(cols, row_keys):
                with col:
                    TILE_RENDERERS[key](key)
