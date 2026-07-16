import streamlit as st

import data_loader as dl
from ui_helpers import section_header


def render():
    section_header("Home", "Season at a glance: key numbers from scouting and wellness.")

    matches = dl.load_match_list()
    wellness = dl.load_wellness_data()["wellness"]

    with st.container(horizontal=True):
        st.metric("Matches analyzed", len(matches), border=True)
        st.metric("Players monitored", len(dl.load_player_names()) - 1, border=True)
        st.metric("First match", min(matches), border=True)
        st.metric("Last match", max(matches), border=True)

    # Recovery alert: lowest TQR recorded on the most recent survey day available
    last_date = wellness["Data"].max()
    last_day = wellness[wellness["Data"] == last_date].sort_values("Tqr")
    threshold = 15
    below_threshold = last_day[last_day["Tqr"] < threshold]

    if not below_threshold.empty:
        players_str = " · ".join(f"{r.player_name} (TQR {r.Tqr:.1f})" for r in below_threshold.itertuples())
        st.markdown(f"""
            <div class="alert-card">
                ⚠️ <b>Low recovery</b> — {players_str} below threshold {threshold} on {last_date.strftime('%d %b %Y')}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="alert-card">
                ✅ <b>Recovery on track</b> — no player below threshold {threshold} on {last_date.strftime('%d %b %Y')}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Quick access</div>
            <div class="ph-line">📊 <b>Scout & Stats</b> — per-fundamental statistics and attack game distribution</div>
            <div class="ph-line">💤 <b>Load & Wellness</b> — TQR, RPE and jump trends (draft, to be defined together)</div>
            <div class="ph-line">📅 Next commitment (match/training) — no calendar data source connected yet</div>
        </div>
    """, unsafe_allow_html=True)
