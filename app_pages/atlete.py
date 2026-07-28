import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import player_colors as pc
import players_grid as pg
from ui_helpers import close_polygon, dark_polar_layout, section_header

CARD_CSS = """
<style>
    .roster-crest-cell { display: flex; align-items: center; justify-content: center; height: 100%; padding: 20px 0; }
    [class*="st-key-playercard_"] button { width: 100%; font-weight: 600; }
    .overview-name { font-size: 1.2rem; font-weight: 700; }
    .overview-role { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
</style>
"""

# Wellness questionnaire items shown as icons instead of text labels (see
# wellness.py for the same 1-5, high = worse items used team-wide).
WELLNESS_ICONS = {"Fatica": "🔋", "Sonno": "😴", "Doms": "💪", "Stress": "😌", "Mood": "🙂"}


def _select_player(surname: str):
    st.session_state["selected_player"] = surname


def _render_player_card(player: dict, stats, selected: str):
    color = pc.color_for(player["surname"])
    with st.container(border=True):
        st.markdown(f'<div style="height:4px;margin:-1px -1px 10px -1px;border-radius:6px 6px 0 0;background:{color}"></div>', unsafe_allow_html=True)
        st.image(pg.photo_path(player), width="stretch")

        if player["surname"] in stats.index:
            row = stats.loc[player["surname"]]
            label = f"{row['points']} pts · {row['appearances']} m"
        else:
            label = "No data"
        cap = "👑 " if player.get("captain") else ""
        st.button(
            f"{cap}{player['last']}\n{label}",
            key=f"playercard_{player['surname']}",
            on_click=_select_player,
            args=(player["surname"],),
            type="primary" if player["surname"] == selected else "secondary",
            width="stretch",
        )


def _render_performance(surname: str, color: str):
    scout = dl.load_scout_data()
    season = scout[
        (scout["match"] == dl.SEASON_LABEL) & (scout["palla"] == "Totale")
        & (~scout["is_team"]) & (scout["player_name"] == surname) & (scout["Tot"] > 0)
    ].copy()

    if season.empty:
        st.info("No scouting data for this player.")
        return

    season["Fundamental"] = season["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    season = season.sort_values("E_pct")
    fig = px.bar(
        season, x="E_pct", y="Fundamental", orientation="h",
        labels={"E_pct": "Efficiency E%", "Fundamental": ""},
        color_discrete_sequence=[color],
    )
    fig.update_layout(xaxis_tickformat=".0%", height=230, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _render_wellness_radar(surname: str, color: str):
    wellness = dl.load_wellness_data()["wellness"]
    p = wellness[wellness["player_name"] == surname]
    if p.empty:
        st.info("No wellness data for this player.")
        return

    recent = p[p["Data"] >= p["Data"].max() - pd.Timedelta(days=6)]
    values = [6 - recent[param].mean() for param in WELLNESS_ICONS]
    icons = list(WELLNESS_ICONS.values())
    r, theta = close_polygon(values, icons)
    fig = go.Figure(go.Scatterpolar(r=r, theta=theta, fill="toself", line_color=color, fillcolor=_rgba(color, 0.3)))
    fig.update_layout(**dark_polar_layout([1, 5]))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig, width="stretch", theme=None)
    st.caption("Last 7 days, bigger = feeling better.")


def _render_overview(surname: str):
    player = pg.PLAYERS_BY_SURNAME[surname]
    color = pc.color_for(surname)
    stats = dl.load_player_stats()

    with st.container(border=True):
        col_photo, col_info = st.columns([1, 2])
        with col_photo:
            st.image(pg.photo_path(player), width="stretch")
        with col_info:
            cap = "👑 " if player.get("captain") else ""
            st.markdown(f'<div class="overview-name">{cap}{player["first"]} {player["last"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="overview-role">{player["role"]}</div>', unsafe_allow_html=True)
            if surname in stats.index:
                row = stats.loc[surname]
                st.markdown(f"🏐 **{row['points']}** pts · **{row['appearances']}** matches")

        st.markdown("**Performance** · efficiency by fundamental")
        _render_performance(surname, color)

        st.markdown("**Wellness**")
        _render_wellness_radar(surname, color)


def render():
    section_header("Players", "Click a player for her season overview.")
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    st.session_state.setdefault("selected_player", "Orro")
    selected = st.session_state["selected_player"]
    stats = dl.load_player_stats()

    col_grid, col_overview = st.columns([3, 2])

    with col_grid:
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
                        _render_player_card(player, stats, selected)

    with col_overview:
        _render_overview(selected)
