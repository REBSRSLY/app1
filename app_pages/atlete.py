import streamlit as st

import data_loader as dl
import players_grid as pg
from ui_helpers import section_header

CARD_CSS = """
<style>
    .roster-photo-wrap {
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 8px;
        background: #f2f2f2;
        line-height: 0;
    }
    .roster-name { font-weight: 700; font-size: 1rem; text-align: center; }
    .roster-role {
        font-size: 11px; color: var(--muted); text-transform: uppercase;
        letter-spacing: 0.05em; text-align: center; margin-bottom: 6px;
    }
    .roster-stats { font-size: 12px; color: var(--muted); text-align: center; }
    .roster-crest-cell { display: flex; align-items: center; justify-content: center; height: 100%; padding: 20px 0; }
</style>
"""


def _render_player_card(player: dict, stats):
    color = pg.ROLE_COLORS[player["role"]]
    with st.container(border=True):
        st.markdown(f'<div style="height:4px;margin:-1px -1px 10px -1px;border-radius:6px 6px 0 0;background:{color}"></div>', unsafe_allow_html=True)
        st.image(pg.photo_path(player), width="stretch")
        cap = ' <span class="stamp-captain">Captain</span>' if player.get("captain") else ""
        st.markdown(f'<div class="roster-name">{player["last"]}{cap}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="roster-role">{player["role"]}</div>', unsafe_allow_html=True)

        if player["surname"] in stats.index:
            row = stats.loc[player["surname"]]
            st.markdown(
                f'<div class="roster-stats">🏐 {row["points"]} pts · {row["appearances"]} matches</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="roster-stats">No scouting data</div>', unsafe_allow_html=True)


def render():
    section_header("Players", "Full roster by role, with season points and appearances.")
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    stats = dl.load_player_stats()

    for row in pg.GRID_ROWS:
        cols = st.columns(4)
        for col, player in zip(cols, row):
            with col:
                if player is None:
                    with st.container(border=True):
                        st.markdown('<div class="roster-crest-cell">', unsafe_allow_html=True)
                        st.image(pg.CREST_PATH, width="stretch")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    _render_player_card(player, stats)
