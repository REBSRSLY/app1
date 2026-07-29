from itertools import groupby

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import player_colors as pc
import players_grid as pg
from ui_helpers import WELLNESS_ICONS, close_polygon, dark_polar_layout, rgba_from_hex

RECENT_MATCHES_N = 5
GOOD_COLOR = "#54A24B"
LOW_COLOR = "#E45756"
RECOVERY_THRESHOLD = 15

BASE_CARD_CSS = """
<style>
    /* Wide/short (not square) so First name, SURNAME, Score and Conv. each
       sit on their own line without wrapping mid-word or clipping. */
    [class*="st-key-playercard_"] button {
        width: 100%;
        min-width: 92px;
        height: 118px !important;
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
        padding: 5px 40px 5px 8px !important;
        line-height: 1.18;
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
    /* Name (First / SURNAME, wrapped in **bold** markdown) gets a bigger
       font than the Score/Conv lines. */
    [class*="st-key-playercard_"] button p strong {
        font-size: 14px;
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
    and a large jersey number pinned to the right edge, both keyed off the
    button's auto-generated st-key class."""
    rules = []
    for p in pg.ALL_PLAYERS:
        color = pc.color_for(p["surname"])
        number_content = str(p["number"]) if p["number"] is not None else ""
        rules.append(
            f'[class*="st-key-playercard_{p["surname"]}"] button {{ '
            f'background: linear-gradient(90deg, var(--surface) 0%, {rgba_from_hex(color, 0.55)} 100%) !important; '
            f'}} '
            f'[class*="st-key-playercard_{p["surname"]}"] button::after {{ '
            f'content: "{number_content}"; position: absolute; right: 6px; top: 50%; '
            f'transform: translateY(-50%); font-size: 1.9rem; font-weight: 800; '
            f'color: rgba(255,255,255,0.92); text-shadow: 0 1px 4px rgba(0,0,0,0.6); '
            f'z-index: 0; line-height: 1; pointer-events: none; }}'
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
    # Name/surname are bold so the "button p strong" CSS rule can give them
    # a bigger font than the Score/Conv lines; the jersey number itself is
    # drawn separately (pinned right) via the ::after in _player_card_css.
    st.button(
        f"{cap_badge}**{player['first']}**\n**{player['last'].upper()}**\nScore: {score}\nConv: {caps}",
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


def _ordered_fundamentals(present: set) -> list[str]:
    """dl.FONDAMENTALE_ORDER (the Excel sheet's own row order), restricted
    to whichever fundamentals this player actually has data for -- so the
    row order never reshuffles between players or reruns."""
    return [f for f in dl.FONDAMENTALE_ORDER if f in present]


def _recency_opacity(group: pd.DataFrame) -> pd.Series:
    """0.25 (oldest match in this fundamental) ramping up to 1.0 (most
    recent) -- "match" sorts correctly as a plain string since it's a
    fixed-width YY-MM-DD sheet name."""
    rank = group["match"].rank(method="dense")
    n = rank.max()
    if n <= 1:
        return pd.Series(1.0, index=group.index)
    return 0.25 + 0.75 * (rank - 1) / (n - 1)


def _performance_bar(recent: pd.DataFrame, value_col: str, title: str, color: str, x_range: list):
    """Mean +/- std bars: used for Ind, which is a plain non-negative count
    per fundamental so a single mean+spread bar reads cleanly."""
    agg = recent.groupby("fondamentale", observed=True).agg(
        mean=(value_col, "mean"), std=(value_col, "std"), tot=("Tot", "sum"),
    ).reset_index()
    agg["std"] = agg["std"].fillna(0)
    agg = agg[agg["tot"] > 0]

    if agg.empty:
        st.info(f"No {title.lower()} data in the last {RECENT_MATCHES_N} matches.")
        return

    agg["Fundamental"] = agg["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    order = _ordered_fundamentals(set(agg["fondamentale"]))
    order_labels = [dl.FONDAMENTALE_LABELS[f] for f in order]

    fig = px.bar(
        agg, x="mean", y="Fundamental", orientation="h", error_x="std",
        category_orders={"Fundamental": order_labels},
        labels={"mean": "", "Fundamental": ""},
        color_discrete_sequence=[color],
    )
    fig.update_layout(
        height=190, margin=dict(l=0, r=10, t=25, b=10),
        title=dict(text=title, font=dict(size=12)),
        xaxis=dict(range=x_range),
        yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
    )
    fig.update_traces(error_x=dict(thickness=1, width=3))
    st.plotly_chart(fig, width="stretch")


def _performance_range(recent: pd.DataFrame, value_col: str, title: str, color: str, is_percent: bool, x_range: list):
    """One scatter dot per match, per fundamental -- more recent matches
    more opaque. Thin gridlines across the fixed axis range (rather than
    an outline bar) are what makes each row readable now."""
    d = recent[recent["Tot"] > 0].copy()
    if d.empty:
        st.info(f"No {title.lower()} data in the last {RECENT_MATCHES_N} matches.")
        return

    d["Fundamental"] = d["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    d["opacity"] = d.groupby("fondamentale", group_keys=False).apply(_recency_opacity)
    order = _ordered_fundamentals(set(d["fondamentale"]))
    order_labels = [dl.FONDAMENTALE_LABELS[f] for f in order]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d[value_col], y=d["Fundamental"], mode="markers",
        marker=dict(color=color, opacity=d["opacity"], size=8, line=dict(width=0)),
        showlegend=False,
        customdata=d["match"],
        hovertemplate="%{y} · %{customdata}: %{x" + (":.0%" if is_percent else "") + "}<extra></extra>",
    ))
    fig.update_layout(
        height=190, margin=dict(l=0, r=10, t=25, b=10),
        title=dict(text=title, font=dict(size=12)),
        xaxis=dict(
            range=x_range, tickformat=".0%" if is_percent else None,
            dtick=(x_range[1] - x_range[0]) / 4,
            showgrid=True, gridcolor="rgba(255,255,255,0.14)", gridwidth=1,
            zeroline=True, zerolinecolor="rgba(255,255,255,0.3)", zerolinewidth=1,
        ),
        yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
    )
    st.plotly_chart(fig, width="stretch")


def _render_performance(surname: str, color: str):
    recent = _recent_matches(surname)
    if recent.empty:
        st.info("No scouting data for this player.")
        return

    _performance_range(recent, "E_pct", "Efficiency E%", color, is_percent=True, x_range=[-1, 1])
    _performance_bar(recent, "Ind", "Index", color, x_range=[0, 100])
    st.caption(f"Last {RECENT_MATCHES_N} matches, by fundamental.")


def _render_wellness_radar(surname: str, color: str):
    wellness = dl.load_wellness_data()["wellness"]
    p = wellness[wellness["player_name"] == surname]
    if p.empty:
        st.info("No wellness data for this player.")
        return

    recent = p[p["Data"] >= p["Data"].max() - pd.Timedelta(days=6)]
    icons = list(WELLNESS_ICONS.values())

    means = [recent[param].mean() for param in WELLNESS_ICONS]
    stds = [recent[param].std() for param in WELLNESS_ICONS]
    values = [6 - m for m in means]
    # Inversion (6 - x) is a shift, so std is unaffected -- upper/lower
    # bounds just add/subtract it around the already-inverted mean, clipped
    # to the 1-5 axis.
    upper = [min(5.0, v + (s if pd.notna(s) else 0)) for v, s in zip(values, stds)]
    lower = [max(1.0, v - (s if pd.notna(s) else 0)) for v, s in zip(values, stds)]

    last_date = recent["Data"].max()
    last_day = recent[recent["Data"] == last_date]
    last_values = [6 - last_day[param].mean() for param in WELLNESS_ICONS]

    tqr_avg = recent["Tqr"].mean()
    tqr_color = LOW_COLOR if tqr_avg < RECOVERY_THRESHOLD else GOOD_COLOR
    st.markdown(
        f'<div style="text-align:center; font-size:1.15rem; font-weight:700; color:{tqr_color};">TQR {tqr_avg:.1f}</div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    # ±1 std dev band: filled only between the lower and upper polygons
    # (fill="tonext" on the second trace), heavily transparent since it's
    # just context around the mean shape.
    r_lower, theta_lower = close_polygon(lower, icons)
    fig.add_trace(go.Scatterpolar(
        r=r_lower, theta=theta_lower, mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    r_upper, theta_upper = close_polygon(upper, icons)
    fig.add_trace(go.Scatterpolar(
        r=r_upper, theta=theta_upper, mode="lines", fill="tonext",
        line=dict(width=0), fillcolor=rgba_from_hex(color, 0.18),
        showlegend=False, hoverinfo="skip",
    ))
    # Mean shape: filled from center, lightly transparent (i.e. more
    # opaque) so it reads clearly over the fainter std band.
    r, theta = close_polygon(values, icons)
    fig.add_trace(go.Scatterpolar(
        r=r, theta=theta, fill="toself", line=dict(width=0), fillcolor=rgba_from_hex(color, 0.45),
        showlegend=False,
    ))
    # Most recent day: a solid outline with filled dots, drawn last so it
    # stands out over both fills.
    r_last, theta_last = close_polygon(last_values, icons)
    fig.add_trace(go.Scatterpolar(
        r=r_last, theta=theta_last, mode="lines+markers",
        line=dict(color=color, width=2), marker=dict(color=color, size=7),
        showlegend=False,
    ))
    fig.update_layout(**dark_polar_layout([1, 5]))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=10, b=10),
        polar=dict(
            radialaxis=dict(showticklabels=False, showline=False),
            angularaxis=dict(tickfont=dict(size=26)),
        ),
    )
    st.plotly_chart(fig, width="stretch", theme=None)
    st.caption("Last 7 days, bigger = feeling better. Faint band = ±1 std dev · solid line = most recent day.")


def _render_overview(surname: str):
    player = pg.PLAYERS_BY_SURNAME[surname]
    color = pc.color_for(surname)
    stats = dl.load_player_stats()

    with st.container(border=True):
        col_photo, col_info = st.columns([0.8, 2.2])
        with col_photo:
            st.image(pg.photo_path(player), width="stretch")
        with col_info:
            cap = "👑 " if player.get("captain") else ""
            st.markdown(f'<div class="overview-name">{cap}{player["first"]} {player["last"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="overview-role">{player["role"]}</div>', unsafe_allow_html=True)
            if surname in stats.index:
                row = stats.loc[surname]
                st.markdown(f"🏐 **{row['points']}** pts · **{row['appearances']}** matches")

            # Performance and Wellness share one toggle-switched section
            # (rather than both stacked) so the whole overview box stays
            # short enough to fit without scrolling the page.
            view = st.segmented_control(
                "Detail view", ["Performance", "Wellness"],
                default="Performance", key="players_detail_view",
                label_visibility="collapsed",
            )

        if view == "Wellness":
            _render_wellness_radar(surname, color)
        else:
            _render_performance(surname, color)


def render():
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
