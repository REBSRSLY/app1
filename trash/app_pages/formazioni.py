import streamlit as st

import data_loader as dl
import player_colors as pc
from roster import panchina, titolari

RECOVERY_THRESHOLD = 15  # same threshold as the Home page's recovery alert
GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"

CARD_CSS = """
<style>
    .lineup-role { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em; font-weight:700; }
    .lineup-name { font-size:1.05rem; font-weight:700; margin:2px 0 4px; }
    .lineup-tqr { font-size:12.5px; font-weight:600; }
</style>
"""


def _latest_tqr() -> dict[str, float]:
    """Most recent TQR reading per player, from the latest wellness survey
    day available (same reference day the Home page's recovery alert uses)."""
    wellness = dl.load_wellness_data()["wellness"]
    if wellness.empty:
        return {}
    last_day = wellness[wellness["Data"] == wellness["Data"].max()]
    return dict(zip(last_day["player_name"], last_day["Tqr"]))


def _card_border_css(players: list[dict]) -> str:
    rules = []
    for p in players:
        color = pc.color_for(p["name"])
        rules.append(f'[class*="st-key-lineup_card_{p["name"]}"] {{ border-color:{color} !important; }}')
    return f"<style>{''.join(rules)}</style>"


def _render_player_card(p: dict, tqr_by_player: dict, position_label: str):
    tqr = tqr_by_player.get(p["name"])
    with st.container(border=True, key=f"lineup_card_{p['name']}"):
        st.markdown(f'<div class="lineup-role">{position_label}</div>', unsafe_allow_html=True)
        cap = " · C" if p.get("tag") == "Captain" else ""
        st.markdown(f'<div class="lineup-name">{p["name"]}{cap}</div>', unsafe_allow_html=True)
        if "alt" in p:
            st.caption(f"Alt: {p['alt']}")
        if tqr is None:
            st.caption("No recent wellness data")
        else:
            color = LOW_COLOR if tqr < RECOVERY_THRESHOLD else GOOD_COLOR
            status = "Low recovery" if tqr < RECOVERY_THRESHOLD else "Recovered"
            st.markdown(f'<div class="lineup-tqr" style="color:{color}">TQR {tqr:.1f} · {status}</div>', unsafe_allow_html=True)


def render():
    st.markdown(CARD_CSS, unsafe_allow_html=True)
    st.markdown(_card_border_css(titolari + panchina), unsafe_allow_html=True)

    tqr_by_player = _latest_tqr()

    st.markdown("**Starting six**")
    cols = st.columns(4)
    for i, p in enumerate(titolari):
        with cols[i % 4]:
            label = "Libero" if p["pos"] == "L" else f"{p['pos']} · {p['role']}"
            _render_player_card(p, tqr_by_player, label)

    st.markdown("**Bench**")
    cols = st.columns(4)
    for i, p in enumerate(panchina):
        with cols[i % 4]:
            _render_player_card(p, tqr_by_player, p["role"])
