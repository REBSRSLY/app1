import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import calendar_view as cv
import data_loader as dl
import filters
import match_calendar as mc
import players_grid as pg
import training_load
from ui_helpers import close_polygon, dark_polar_layout

GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
WARN_COLOR = "#F0A600"
RECOVERY_THRESHOLD = 15


def _render_hero(season: str):
    col_crest, col_title = st.columns([0.1, 1], vertical_alignment="center")
    with col_crest:
        st.image(pg.CREST_PATH, width="stretch")
    with col_title:
        st.markdown(
            '<div style="font-size:1.9rem;font-weight:800;line-height:1.15;">Vero Volley Milano</div>'
            f'<div style="color:var(--muted);font-size:0.95rem;">Technical Staff · A1 Women\'s · Season {season}</div>',
            unsafe_allow_html=True,
        )


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
                '<div style="display:flex;align-items:center;gap:12px;">'
                '<span style="font-size:1.8rem;">✅</span>'
                f'<div><b style="color:{GOOD_COLOR};font-size:1.05rem;">Recovery on track</b><br>'
                f'<span style="color:var(--muted);font-size:12.5px;">No player below threshold {RECOVERY_THRESHOLD} '
                f'on {last_date.strftime("%d/%m/%y")}</span></div></div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
            '<span style="font-size:1.8rem;">⚠️</span>'
            f'<div><b style="color:{LOW_COLOR};font-size:1.05rem;">Low recovery</b><br>'
            f'<span style="color:var(--muted);font-size:12.5px;">Below threshold {RECOVERY_THRESHOLD} '
            f'on {last_date.strftime("%d/%m/%y")}</span></div></div>',
            unsafe_allow_html=True,
        )
        rows = list(below.itertuples())
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 2px;'
            f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
            f'<span style="font-weight:600;">{r.player_name}</span>'
            f'<span style="background:rgba(228,87,86,0.15);color:{LOW_COLOR};font-weight:700;'
            f'border-radius:12px;padding:2px 11px;font-size:12.5px;">TQR {r.Tqr:.1f}</span></div>'
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
            number=dict(font=dict(size=42, color="#f2f2f2"), valueformat=".2f"),
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
        fig.update_layout(height=230, margin=dict(l=25, r=25, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.caption(f"As of {ref_date.strftime('%d %b %Y')} · green 0.8–1.3 = sweet spot · red >1.5 = spike risk.")


def _render_league_position(season: str):
    with st.container(border=True):
        st.markdown("**League position**")
        standings = mc.SEASON_STANDINGS.get(season, [])
        us = next((r for r in standings if r["is_us"]), None)
        if us is None or not standings:
            st.caption("No standings yet.")
            return

        st.markdown(
            f'<div style="font-size:3.2rem;font-weight:800;color:var(--accent);line-height:1;">#{us["pos"]}</div>'
            f'<div style="color:var(--muted);font-size:0.9rem;margin-bottom:10px;">'
            f'of {len(standings)} teams · {us["w"]}W–{us["l"]}L · {us["pts"]} pts</div>',
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
                height=130, margin=dict(l=10, r=50, t=5, b=5),
                xaxis=dict(visible=False, range=[0, max(us["pts"], other["pts"]) * 1.3]),
                yaxis=dict(tickfont=dict(size=13)),
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
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 2px;'
            f'{"border-bottom:1px solid var(--line);" if i < len(rows) - 1 else ""}">'
            f'<span style="font-size:1.15rem;">{medals[i]}</span>'
            f'<span style="flex:1;padding-left:10px;font-weight:700;font-size:1.05rem;">{r.Index}</span>'
            f'<span style="color:var(--accent);font-weight:700;">{int(r.points)} pts</span>'
            f'</div>'
            for i, r in enumerate(rows)
        )
        st.markdown(rows_html, unsafe_allow_html=True)
        st.caption(" · ".join(f"{r.Index}: {int(r.appearances)} matches" for r in rows))


def _render_team_shape():
    with st.container(border=True):
        st.markdown("**Team shape** · efficiency (E%) across fundamentals")
        scout = dl.load_scout_data()
        team = scout[
            (scout["match"] == dl.SEASON_LABEL) & scout["is_team"]
            & (scout["palla"] == "Totale") & (scout["Tot"] > 0)
        ]
        present = [f for f in dl.FONDAMENTALE_ORDER if f in set(team["fondamentale"])]
        if len(present) < 3:
            st.caption("Not enough season data yet for a radar.")
            return

        labels = [dl.FONDAMENTALE_LABELS[f] for f in present]
        # +50pp shift, same trick as Scout & Stats' own (Ind-based) team
        # radar: E_pct can be negative, which would collapse/invert a polar
        # shape around the origin. But E_pct also reaches ~90% here (Set),
        # so shifted values can reach ~1.4 -- a [0, 1] axis clipped that
        # part of the shape flat against the rim. [0, 1.5] gives the full
        # +50pp-shifted range (-100%..+100% => 0..2, but this scope tops
        # out well under that) room to actually plot.
        values = [team.loc[team["fondamentale"] == f, "E_pct"].iloc[0] + 0.5 for f in present]
        r, theta = close_polygon(values, labels)
        fig = go.Figure(go.Scatterpolar(r=r, theta=theta, fill="toself", line_color="#1655a5", fillcolor="rgba(22,85,165,0.35)"))
        fig.update_layout(**dark_polar_layout([0, 1.5]))
        fig.update_layout(polar=dict(radialaxis=dict(showticklabels=False)), height=300, margin=dict(l=30, r=30, t=10, b=10))
        st.plotly_chart(fig, width="stretch", theme=None)
        st.caption("Full-season team E% per fundamental, shifted +50pp onto the radial axis so negative E% still plots.")


def _render_recent_form():
    """Last 5 Serie A1 results as colored dots (same win-margin scale used
    on the Matches page's standings) -- a quick "how's it going" snapshot
    that the old static Quick access panel didn't give, and which the
    fixed top nav already makes redundant as a navigation aid."""
    season_matches = mc.matches_for_season(filters.season())
    serie_a1 = sorted((m for m in season_matches if m["competition"] == "Serie A1"), key=lambda m: m["pdate"])
    if not serie_a1:
        return

    recent = serie_a1[-5:]
    with st.container(border=True):
        st.markdown("**Recent form** · Serie A1")
        cols = st.columns(len(recent) + 1)
        for col, m in zip(cols, recent):
            with col:
                color = cv.RESULT_COLORS[mc.result_points(m)]
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="width:22px;height:22px;border-radius:50%;background:{color};margin:0 auto 6px;"></div>'
                    f'<div style="font-size:12px;color:var(--muted);">{cv.fmt_date(m["date"])}</div>'
                    f'<div style="font-size:13px;font-weight:700;">{m["score"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with cols[-1]:
            wins = sum(1 for m in serie_a1 if mc.is_win(m))
            st.markdown(
                f'<div style="text-align:center; padding-top:6px;">'
                f'<div style="font-size:1.4rem;font-weight:800;">{wins}W – {len(serie_a1) - wins}L</div>'
                f'<div style="font-size:12px;color:var(--muted);">season record</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


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

    _render_hero(season)

    _topic_label("Wellness")
    col_recovery, _ = st.columns([1, 1])
    with col_recovery:
        _render_low_recovery(wellness)

    _topic_label("Loads")
    _render_readiness_gauge(data["rpe"])

    _topic_label("Matches")
    col_league, col_form = st.columns(2)
    with col_league:
        _render_league_position(season)
    with col_form:
        _render_recent_form()

    _topic_label("Scout & Stats")
    col_scorers, col_shape = st.columns(2)
    with col_scorers:
        _render_top_scorers()
    with col_shape:
        _render_team_shape()

    _render_how_to()
