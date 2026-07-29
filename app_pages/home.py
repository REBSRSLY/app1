import pandas as pd
import streamlit as st

import calendar_view as cv
import data_loader as dl
import filters
import match_calendar as mc
import players_grid as pg
import training_load

GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"


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


def _snapshot_box(title: str, value_html: str, caption: str):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.markdown(value_html, unsafe_allow_html=True)
        st.caption(caption)


def _render_standings_snapshot(season: str):
    standings = mc.SEASON_STANDINGS.get(season, [])
    us = next((r for r in standings if r["is_us"]), None)
    if us is None:
        _snapshot_box("League position", '<div style="color:var(--muted);">—</div>', "No standings yet.")
        return
    _snapshot_box(
        "League position",
        f'<div style="font-size:2rem;font-weight:800;color:var(--accent);">#{us["pos"]}</div>',
        f"{us['pts']} pts · {us['w']}W–{us['l']}L · {len(standings)} teams",
    )


def _render_readiness_snapshot(rpe: pd.DataFrame):
    team_metrics = training_load.metrics_frame(rpe)
    team_metrics = team_metrics.dropna(subset=["acwr"])
    if team_metrics.empty:
        _snapshot_box("Team readiness", '<div style="color:var(--muted);">—</div>', "Not enough training history yet.")
        return

    ref_date = team_metrics.index.max()
    acwr = team_metrics.loc[ref_date, "acwr"]
    sweet_spot = 0.8 <= acwr <= 1.3
    spike = acwr > 1.5
    status = "Sweet spot" if sweet_spot else ("Spike risk" if spike else "Low load")
    color = LOW_COLOR if spike else GOOD_COLOR if sweet_spot else "#F0A600"
    _snapshot_box(
        "Team readiness (ACWR)",
        f'<div style="font-size:2rem;font-weight:800;color:{color};">{acwr:.2f}</div>',
        f"{status} · as of {ref_date.strftime('%d %b %Y')}",
    )


def _render_top_scorer():
    stats = dl.load_player_stats()
    if stats.empty:
        _snapshot_box("Top scorer", '<div style="color:var(--muted);">—</div>', "No season stats yet.")
        return
    ranked = stats.sort_values("points", ascending=False)
    top_name, top = ranked.index[0], ranked.iloc[0]
    _snapshot_box(
        "Top scorer this season",
        f'<div style="font-size:1.5rem;font-weight:800;">{top_name}</div>',
        f"{int(top['points'])} points · {int(top['appearances'])} matches played",
    )


def render():
    season = filters.season()
    matches = dl.load_match_list()
    data = dl.load_wellness_data()
    wellness = data["wellness"]

    _render_hero(season)

    with st.container(horizontal=True):
        st.metric("Matches analyzed", len(matches), border=True)
        st.metric("Players monitored", len(dl.load_player_names()) - 1, border=True)
        st.metric("First match", cv.fmt_date(min(matches)), border=True)
        st.metric("Last match", cv.fmt_date(max(matches)), border=True)

    # Recovery alert: lowest TQR recorded on the most recent survey day available
    last_date = wellness["Data"].max()
    last_day = wellness[wellness["Data"] == last_date].sort_values("Tqr")
    threshold = 15
    below_threshold = last_day[last_day["Tqr"] < threshold]

    if not below_threshold.empty:
        players_str = " · ".join(f"{r.player_name} (TQR {r.Tqr:.1f})" for r in below_threshold.itertuples())
        st.markdown(f"""
            <div class="alert-card" style="background:rgba(228,87,86,0.1); border-color:rgba(228,87,86,0.4);">
                <b style="color:{LOW_COLOR}">Low recovery</b> — {players_str} below threshold {threshold} on {last_date.strftime('%d/%m/%y')}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="alert-card" style="background:rgba(84,162,75,0.1); border-color:rgba(84,162,75,0.4);">
                <b style="color:{GOOD_COLOR}">Recovery on track</b> — no player below threshold {threshold} on {last_date.strftime('%d/%m/%y')}
            </div>
        """, unsafe_allow_html=True)

    col_standings, col_readiness, col_scorer = st.columns(3)
    with col_standings:
        _render_standings_snapshot(season)
    with col_readiness:
        _render_readiness_snapshot(data["rpe"])
    with col_scorer:
        _render_top_scorer()

    _render_recent_form()


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
                    f'<div style="width:14px;height:14px;border-radius:50%;background:{color};margin:0 auto 4px;"></div>'
                    f'<div style="font-size:11px;color:var(--muted);">{cv.fmt_date(m["date"])}</div>'
                    f'<div style="font-size:11px;font-weight:600;">{m["score"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with cols[-1]:
            wins = sum(1 for m in serie_a1 if mc.is_win(m))
            st.markdown(
                f'<div style="text-align:center; padding-top:4px;">'
                f'<div style="font-size:1.1rem;font-weight:700;">{wins}W – {len(serie_a1) - wins}L</div>'
                f'<div style="font-size:11px;color:var(--muted);">season record</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
