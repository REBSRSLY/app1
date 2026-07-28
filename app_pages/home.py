import streamlit as st

import calendar_view as cv
import data_loader as dl
import filters
import match_calendar as mc
from ui_helpers import section_header

GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"


def render():
    section_header("Home", "Season at a glance: key numbers from scouting and wellness.")
    st.caption(f":material/filter_alt: Sidebar scope: {filters.caption()} — most pages below follow it.")

    matches = dl.load_match_list()
    wellness = dl.load_wellness_data()["wellness"]

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
