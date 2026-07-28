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
    /* Wide/short (not square) so First name, SURNAME, Score and Conv. each
       sit on their own line without wrapping mid-word or clipping. */
    [class*="st-key-playercard_"] button {
        width: 100%;
        min-width: 92px;
        height: 82px !important;
        margin: 0 auto;
        font-weight: 600;
        font-size: 10px;
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        border: 1px solid rgba(255,255,255,0.15) !important;
        display: flex !important;
        flex-direction: column;
        justify-content: center !important;
        align-items: flex-start !important;
        text-align: left !important;
        position: relative;
        overflow: hidden;
        padding: 5px 26px 5px 8px !important;
        line-height: 1.28;
        white-space: normal;
        word-break: normal;
        overflow-wrap: normal;
    }
    [class*="st-key-playercard_"] button p {
        text-align: left !important;
        font-size: 10px;
        /* st.button doesn't turn "\\n" into <br> -- it's literal text inside
           one <p>, so plain "normal"/"nowrap" whitespace handling collapses
           our First/SURNAME/Score/Conv lines onto a single overflowing line.
           pre-line is what actually makes each "\\n" a real line break. */
        white-space: pre-line;
    }
    [class*="st-key-playercard_"] button div[data-testid="stMarkdownContainer"] {
        position: relative;
        z-index: 1;
        width: 100%;
    }
    [class*="st-key-playercard_"] button[kind="primary"] {
        border: 2px solid #ffffff !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.25);
    }
    .role-label {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        text-align: center;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Streamlit stretches every st.columns() row to the tallest sibling's
       height (flexbox align-items:stretch), which cascades down through
       nested columns/containers -- without this, each role box would
       stretch to match the much taller overview panel next to the grid
       instead of hugging its own 1-row-of-cards content. */
    div[data-testid="stVerticalBlock"]:has(> div .role-label) {
        height: auto !important;
        flex-grow: 0 !important;
        align-self: flex-start !important;
        border-width: 2px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div .role-label) {
        height: auto !important;
        align-items: flex-start !important;
    }
    .overview-name { font-size: 1.2rem; font-weight: 700; }
    .overview-role { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
</style>
"""


def _role_border_css() -> str:
    """Colors each role box's border (and its side label) with that role's
    color from players_grid.ROLE_COLORS, via the same :has() trick used
    above to fix the box height -- st.container(border=True) has no color
    parameter of its own."""
    rules = []
    for role, color in pg.ROLE_COLORS.items():
        slug = role.lower().replace(" ", "-")
        rules.append(
            f'div[data-testid="stVerticalBlock"]:has(> div .role-label-{slug}) {{ '
            f'border-color: {color} !important; }} '
            f'.role-label-{slug} {{ color: {color} !important; }}'
        )
    return f"<style>{''.join(rules)}</style>"


def _player_card_css() -> str:
    """Per-player background gradient (surface -> her color, left to right)
    and a large jersey-number watermark, both keyed off the button's
    auto-generated st-key class."""
    rules = []
    for p in pg.ALL_PLAYERS:
        color = pc.color_for(p["surname"])
        number_content = str(p["number"]) if p["number"] is not None else ""
        rules.append(
            f'[class*="st-key-playercard_{p["surname"]}"] button {{ '
            f'background: linear-gradient(90deg, var(--surface) 0%, {rgba_from_hex(color, 0.55)} 100%) !important; '
            f'}} '
            f'[class*="st-key-playercard_{p["surname"]}"] button::after {{ '
            f'content: "{number_content}"; position: absolute; right: 3px; bottom: 3px; '
            f'font-size: 1.15rem; font-weight: 800; color: var(--surface); z-index: 0; '
            f'line-height: 1; pointer-events: none; }}'
        )
    return f"<style>{''.join(rules)}</style>"


def _select_player(surname: str):
    st.session_state["selected_player"] = surname


def _render_player_card(player: dict, stats, selected: str):
    if player["surname"] in stats.index:
        row = stats.loc[player["surname"]]
        score, caps = row["points"], row["appearances"]
    else:
        score, caps = "—", "—"
    cap_badge = "👑 " if player.get("captain") else ""
    # The button *is* the card (no separate image/container), so the whole
    # visible surface is clickable, not just a caption underneath a photo.
    # Each field on its own short line (rather than combined) so long names
    # and the score/appearances numbers never wrap mid-word inside the card.
    st.button(
        f"{cap_badge}{player['first']}\n{player['last'].upper()}\nScore: {score}\nConv: {caps}",
        key=f"playercard_{player['surname']}",
        on_click=_select_player,
        args=(player["surname"],),
        type="primary" if player["surname"] == selected else "secondary",
        width="stretch",
    )


def _render_role_group(role: str, group_players: list[dict], stats, selected: str):
    slug = role.lower().replace(" ", "-")
    with st.container(border=True):
        col_label, col_cards = st.columns([0.14, 4])
        with col_label:
            st.markdown(f'<div class="role-label role-label-{slug}">{role}</div>', unsafe_allow_html=True)
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


def _performance_box(recent: pd.DataFrame, value_col: str, title: str, color: str, is_percent: bool):
    """Horizontal box plot: one box per fundamental, built directly from the
    per-match values in the last RECENT_MATCHES_N matches (no pre-aggregated
    mean/std -- the box/whiskers/points show the real match-to-match spread)."""
    d = recent[recent["Tot"] > 0].copy()
    if d.empty:
        st.info(f"No {title.lower()} data in the last {RECENT_MATCHES_N} matches.")
        return

    d["Fundamental"] = d["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    order = d.groupby("Fundamental")[value_col].median().sort_values().index.tolist()
    fig = px.box(
        d, x=value_col, y="Fundamental", orientation="h", points="all",
        category_orders={"Fundamental": order},
        labels={value_col: title, "Fundamental": ""},
        color_discrete_sequence=[color],
    )
    if is_percent:
        fig.update_layout(xaxis_tickformat=".0%")
    fig.update_layout(height=210, margin=dict(l=0, r=10, t=10, b=10), showlegend=False)
    fig.update_traces(marker=dict(size=4, opacity=0.75), line=dict(width=1.5), boxmean=False)
    st.plotly_chart(fig, width="stretch")


def _render_performance(surname: str, color: str):
    recent = _recent_matches(surname)
    if recent.empty:
        st.info("No scouting data for this player.")
        return

    st.caption(f"Last {RECENT_MATCHES_N} matches · box shows the spread across matches, dots are individual match values.")
    _performance_box(recent, "E_pct", "Efficiency E%", color, is_percent=True)
    _performance_box(recent, "Ind", "Index", color, is_percent=False)


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
    st.markdown(_role_border_css(), unsafe_allow_html=True)
    st.markdown(_player_card_css(), unsafe_allow_html=True)

    st.session_state.setdefault("selected_player", "Orro")
    selected = st.session_state["selected_player"]
    stats = dl.load_player_stats()
    groups = {role: list(g) for role, g in groupby(pg.ALL_PLAYERS, key=lambda p: p["role"])}

    # Grid gets more than half the width: the Setter/Opposite boxes each
    # only fit 2 cards side by side, so per-card space is tighter there than
    # in the 4-card rows -- a wider grid column is what keeps every card
    # readable instead of being squeezed by the overview panel next to it.
    col_grid, col_overview = st.columns([3, 2])

    with col_grid:
        # Row 1: Setter + Opposite side by side, in separate boxes (2 cards
        # each, so equal-width columns keep every card the same size).
        col_setter, col_opposite = st.columns(2)
        with col_setter:
            _render_role_group("Setter", groups["Setter"], stats, selected)
        with col_opposite:
            _render_role_group("Opposite", groups["Opposite"], stats, selected)

        # Rows 2-3: Outside Hitter and Middle Blocker, 4 cards each, full width.
        _render_role_group("Outside Hitter", groups["Outside Hitter"], stats, selected)
        _render_role_group("Middle Blocker", groups["Middle Blocker"], stats, selected)

        # Row 4: Libero (3 cards) + crest, kept at a 3:1 width ratio so the
        # Libero cards stay exactly as wide as every other card above.
        col_libero, col_crest = st.columns([3, 1])
        with col_libero:
            _render_role_group("Libero", groups["Libero"], stats, selected)
        with col_crest:
            with st.container(border=True):
                st.image(pg.CREST_PATH, width="stretch")

    with col_overview:
        _render_overview(selected)
