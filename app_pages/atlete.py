from itertools import groupby

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import player_colors as pc
import players_grid as pg
from ui_helpers import WELLNESS_ICONS, close_polygon, dark_polar_layout, rgba_from_hex, section_header

RECENT_MATCHES_N = 5

BASE_CARD_CSS = """
<style>
    [class*="st-key-playercard_"] button {
        width: 100%;
        font-weight: 600;
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.7);
        border: 1px solid rgba(255,255,255,0.15) !important;
    }
    [class*="st-key-playercard_"] button[kind="primary"] {
        border: 2px solid #ffffff !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.25);
    }
    .role-box { margin-bottom: 12px; }
    .role-label {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        text-align: center;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        height: 100%;
        min-height: 64px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .overview-name { font-size: 1.2rem; font-weight: 700; }
    .overview-role { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
</style>
"""


def _player_gradient_css() -> str:
    """One background-gradient rule per player, keyed off their button's
    auto-generated st-key class -- this is what makes each card read as
    "that player's color" instead of a flat per-role accent."""
    rules = []
    for p in pg.ALL_PLAYERS:
        color = pc.color_for(p["surname"])
        rules.append(
            f'[class*="st-key-playercard_{p["surname"]}"] button {{ '
            f'background: linear-gradient(135deg, {color}, {rgba_from_hex(color, 0.45)}) !important; '
            f'}}'
        )
    return f"<style>{''.join(rules)}</style>"


def _select_player(surname: str):
    st.session_state["selected_player"] = surname


def _render_player_card(player: dict, stats, selected: str):
    if player["surname"] in stats.index:
        row = stats.loc[player["surname"]]
        label = f"{row['points']} pts · {row['appearances']} m"
    else:
        label = "No data"
    cap = "👑 " if player.get("captain") else ""
    # The button *is* the card (no separate image/container), so the whole
    # visible surface is clickable, not just a caption underneath a photo.
    st.button(
        f"{cap}**{player['first']} {player['last']}**\n{label}",
        key=f"playercard_{player['surname']}",
        on_click=_select_player,
        args=(player["surname"],),
        type="primary" if player["surname"] == selected else "secondary",
        width="stretch",
    )


def _render_role_group(role: str, group_players: list[dict], stats, selected: str):
    with st.container(border=True):
        col_label, col_cards = st.columns([0.3, 4])
        with col_label:
            st.markdown(f'<div class="role-label">{role}</div>', unsafe_allow_html=True)
        with col_cards:
            cols = st.columns(len(group_players))
            for col, player in zip(cols, group_players):
                with col:
                    _render_player_card(player, stats, selected)


def _recent_matches(surname: str, n: int = RECENT_MATCHES_N) -> pd.DataFrame:
    """This player's scout rows (any fundamental, palla=Totale) from her
    last `n` matches by date -- not the season aggregate."""
    scout = dl.load_scout_data()
    rows = scout[
        (scout["match"] != dl.SEASON_LABEL) & (scout["palla"] == "Totale")
        & (~scout["is_team"]) & (scout["player_name"] == surname)
    ]
    recent_matches = sorted(rows["match"].unique(), reverse=True)[:n]
    return rows[rows["match"].isin(recent_matches)]


def _performance_bar(recent: pd.DataFrame, value_col: str, title: str, color: str, is_percent: bool):
    agg = recent.groupby("fondamentale", observed=True).agg(
        mean=(value_col, "mean"), std=(value_col, "std"), tot=("Tot", "sum"),
    ).reset_index()
    agg["std"] = agg["std"].fillna(0)
    agg = agg[agg["tot"] > 0].sort_values("mean")

    if agg.empty:
        st.info(f"No {title.lower()} data in the last {RECENT_MATCHES_N} matches.")
        return

    agg["Fundamental"] = agg["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    fig = px.bar(
        agg, x="mean", y="Fundamental", orientation="h", error_x="std",
        labels={"mean": title, "Fundamental": ""},
        color_discrete_sequence=[color],
    )
    if is_percent:
        fig.update_layout(xaxis_tickformat=".0%")
    fig.update_layout(height=210, margin=dict(l=0, r=10, t=10, b=10))
    fig.update_traces(error_x=dict(thickness=1, width=3))
    st.plotly_chart(fig, width="stretch")


def _render_performance(surname: str, color: str):
    recent = _recent_matches(surname)
    if recent.empty:
        st.info("No scouting data for this player.")
        return

    st.caption(f"Last {RECENT_MATCHES_N} matches · bars show the mean, whiskers show the standard deviation.")
    _performance_bar(recent, "E_pct", "Efficiency E%", color, is_percent=True)
    _performance_bar(recent, "Ind", "Index", color, is_percent=False)


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
    fig = go.Figure(go.Scatterpolar(r=r, theta=theta, fill="toself", line_color=color, fillcolor=rgba_from_hex(color, 0.3)))
    fig.update_layout(**dark_polar_layout([1, 5]))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=10, b=10),
        polar=dict(radialaxis=dict(showticklabels=False, showline=False)),
    )
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

        st.markdown("**Performance** · by fundamental")
        _render_performance(surname, color)

        st.markdown("**Wellness**")
        _render_wellness_radar(surname, color)


def render():
    section_header("Players", "Click a player for her season overview.")
    st.markdown(BASE_CARD_CSS, unsafe_allow_html=True)
    st.markdown(_player_gradient_css(), unsafe_allow_html=True)

    st.session_state.setdefault("selected_player", "Orro")
    selected = st.session_state["selected_player"]
    stats = dl.load_player_stats()

    col_grid, col_overview = st.columns([3, 2])

    with col_grid:
        for role, group in groupby(pg.ALL_PLAYERS, key=lambda p: p["role"]):
            _render_role_group(role, list(group), stats, selected)

        col_a, col_b, col_c = st.columns([2, 1, 2])
        with col_b:
            st.image(pg.CREST_PATH, width="stretch")

    with col_overview:
        _render_overview(selected)
