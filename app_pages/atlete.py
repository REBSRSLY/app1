import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import player_colors as pc
import players_grid as pg
import training_load
from ui_helpers import GOOD_COLOR, LOW_COLOR, WARN_COLOR, WELLNESS_ICONS, close_polygon, dark_polar_layout, rgba_from_hex

# English labels for the 5 wellness items, paired with WELLNESS_ICONS so
# every radar trace can name its own points on hover (duplicated from
# wellness.py's PARAM_LABELS rather than cross-imported, per this app's
# convention for small stable per-page constants).
WELLNESS_PARAM_LABELS = {"Fatica": "Fatigue", "Sonno": "Sleep", "Doms": "Muscle soreness", "Stress": "Stress", "Mood": "Mood"}

BASE_CARD_CSS = """
<style>
    /* Narrow vertical strips: the name reads bottom-to-top so each card
       needs only its own text height in width, which is what lets the
       whole grid sit in a much narrower column than the old wide cards
       (score/appearances moved to the detail panel, which has room). */
    [class*="st-key-playercard_"] button {
        width: 100%;
        min-width: 0;
        height: 150px !important;
        margin: 0 auto;
        font-weight: 700;
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.8);
        border: 1px solid rgba(255,255,255,0.15) !important;
        display: flex !important;
        align-items: flex-end !important;
        justify-content: center !important;
        position: relative;
        overflow: hidden;
        padding: 6px 2px 8px !important;
    }
    [class*="st-key-playercard_"] button p {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        text-align: left !important;
        white-space: nowrap;
        font-size: 13px;
        letter-spacing: 0.02em;
        line-height: 1;
    }
    [class*="st-key-playercard_"] button p strong {
        font-size: 13px;
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
        font-family: var(--display);
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.1em;
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
    /* None of these open with a "**Title**" markdown (role boxes use a
       side label, overview/crest use photos/stats), so they need the
       opaque-card fill given explicitly by key instead of the global
       title-based rule in styles.py. :has(> div .role-label) alone can't
       carry a background -- it also matches every ANCESTOR of a role box
       (column/row wrappers all the way up), since :has()'s inner clause
       matches any descendant, not just the box itself. */
    [class*="st-key-role_group_"], .st-key-player_overview_box, .st-key-player_crest_box {
        background: var(--surface) !important;
    }
    /* Player photo: rendered from the full-resolution source and scaled
       here, so the browser downsamples a 254px image instead of blowing
       up a 64px one (see _render_overview). */
    .st-key-player_overview_box [data-testid="stImage"] img {
        width: 64px !important;
        height: 64px !important;
        object-fit: contain;
    }
    .overview-name { font-family: var(--display); font-size: 1.3rem; font-weight: 700; letter-spacing: 0.01em; }
    /* Crest card sits in the Libero row's spare 4th slot. The rule above
       pins that row to flex-start (so role boxes never stretch to the
       overview panel), which also stopped this card from filling the
       row -- overridden here just for the row that holds the crest, so
       it ends up exactly as tall as the Libero box beside it. */
    div[data-testid="stHorizontalBlock"]:has(> div .crest-wordmark) {
        align-items: stretch !important;
    }
    /* st.container(key=...) wraps the block in a stLayoutWrapper that
       only takes its content's height -- it has to grow too, or the card
       inside it stops short of the row regardless of its own height. */
    div[data-testid="stLayoutWrapper"]:has(> .st-key-player_crest_box) {
        height: 100% !important;
        flex-grow: 1 !important;
    }
    .st-key-player_crest_box {
        height: 100% !important;
        align-self: stretch !important;
    }
    .st-key-player_crest_box > div {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .crest-wordmark {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        font-family: var(--display);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        white-space: nowrap;
        margin: 0 auto;
    }
    /* Breathing room between the overview panel's stacked charts (Efficiency
       + Index in Performance view) -- they were butted directly against
       each other with no gap. */
    .st-key-player_overview_box [data-testid="stPlotlyChart"] {
        margin-bottom: 14px;
    }
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
    """Per-player background gradient (dark -> her color, bottom to top,
    matching the now-vertical name) and the jersey number pinned to the
    card's top edge, both keyed off the button's auto-generated st-key
    class. Hardcoded #181818, not var(--surface): these player cards are
    explicitly exempt from the "every box is solid black" rule
    (styles.py), so they can't just track whatever --surface happens to be."""
    rules = []
    for p in pg.ALL_PLAYERS:
        color = pc.color_for(p["surname"])
        number_content = str(p["number"]) if p["number"] is not None else ""
        rules.append(
            f'[class*="st-key-playercard_{p["surname"]}"] button {{ '
            f'background: linear-gradient(0deg, #181818 0%, {rgba_from_hex(color, 0.55)} 100%) !important; '
            f'}} '
            f'[class*="st-key-playercard_{p["surname"]}"] button::after {{ '
            f'content: "{number_content}"; position: absolute; top: 4px; left: 0; right: 0; '
            f'text-align: center; font-size: 1.75rem; font-weight: 800; '
            f'color: rgba(255,255,255,0.92); text-shadow: 0 1px 4px rgba(0,0,0,0.6); '
            f'z-index: 0; line-height: 1; pointer-events: none; }}'
        )
    return f"<style>{''.join(rules)}</style>"


def _select_player(surname: str):
    st.session_state["selected_player"] = surname


def _render_player_card(player: dict, selected: str):
    """The button *is* the card (no separate image/container), so the whole
    visible surface is clickable. Surname only, set vertically by the CSS
    above -- score and appearances now live in the detail panel, which has
    the room to show them properly. The jersey number is drawn separately
    (pinned to the top edge) via the ::after in _player_card_css."""
    cap_badge = "👑 " if player.get("captain") else ""
    st.button(
        f"{cap_badge}**{player['last'].upper()}**",
        key=f"playercard_{player['surname']}",
        on_click=_select_player,
        args=(player["surname"],),
        type="primary" if player["surname"] == selected else "secondary",
        width="stretch",
    )


def _render_role_group(role: str, group_players: list[dict], selected: str):
    slug = role.lower().replace(" ", "-")
    with st.container(border=True, key=f"role_group_{slug}"):
        col_label, col_cards = st.columns([0.22, 4])
        with col_label:
            st.markdown(f'<div class="role-label role-label-{slug}">{role}</div>', unsafe_allow_html=True)
        with col_cards:
            cols = st.columns(len(group_players))
            for col, player in zip(cols, group_players):
                with col:
                    _render_player_card(player, selected)


def _scoped_matches(surname: str) -> pd.DataFrame:
    """This player's scout rows (any fundamental, palla=Totale) for the
    matches inside the sidebar's active period -- not a fixed "last N
    matches" window, so this panel moves with every other page's scope."""
    scout = dl.load_scout_data()
    in_scope = {m["date"] for m in filters.matches_in_scope()}
    return scout[
        scout["match"].isin(in_scope) & (scout["palla"] == "Totale")
        & (~scout["is_team"]) & (scout["player_name"] == surname)
    ]


def _ordered_fundamentals(present: set) -> list[str]:
    """dl.FONDAMENTALE_ORDER (the Excel sheet's own row order), restricted
    to whichever fundamentals this player actually has data for -- so the
    row order never reshuffles between players or reruns."""
    return [f for f in dl.FONDAMENTALE_ORDER if f in present]


def _recency_opacity(d: pd.DataFrame) -> pd.Series:
    """0.25 (oldest match in this fundamental) ramping up to 1.0 (most
    recent) -- "match" sorts correctly as a plain string since it's a
    fixed-width YY-MM-DD sheet name.

    Fully vectorised (rank + transform), deliberately not
    groupby().apply(): that form is deprecated in current pandas, and on
    a newer pandas than this repo pins it returned a shape that assigned
    back as NaN, which Plotly then rejected outright ("invalid element"
    for marker.opacity) rather than just drawing something odd. The
    fillna/clip at the end keeps that class of failure impossible --
    marker.opacity only ever sees a real float in [0.25, 1]."""
    rank = d.groupby("fondamentale", observed=True)["match"].rank(method="dense")
    n = rank.groupby(d["fondamentale"], observed=True).transform("max")
    # Single-match fundamentals have no range to ramp across: full opacity.
    denom = (n - 1).where(n > 1, 1.0)
    ramp = 0.25 + 0.75 * (rank - 1) / denom
    return ramp.where(n > 1, 1.0).fillna(1.0).clip(0.25, 1.0).astype(float)


# Both performance charts share these, so their rows land on exactly the
# same pixels: same height, same margins, and (passed in) the same
# category array. Anything differing here shifts one chart's rows
# relative to the other's, which is what made them look misaligned.
PERF_CHART_HEIGHT = 210
PERF_CHART_MARGIN = dict(l=0, r=10, t=25, b=10)


def _performance_bar(recent: pd.DataFrame, value_col: str, title: str, color: str, x_range: list, order_labels: list[str]):
    """Mean +/- std bars: used for Ind, which is a plain non-negative count
    per fundamental so a single mean+spread bar reads cleanly."""
    agg = recent.groupby("fondamentale", observed=True).agg(
        mean=(value_col, "mean"), std=(value_col, "std"), tot=("Tot", "sum"),
    ).reset_index()
    agg["std"] = agg["std"].fillna(0)
    agg = agg[agg["tot"] > 0]

    if agg.empty:
        st.info(f"No {title.lower()} data in this period.")
        return

    agg["Fundamental"] = agg["fondamentale"].map(dl.FONDAMENTALE_ABBR)
    # Full name carried alongside the acronym so hovering a row spells out
    # what "AAR"/"CTR"/... actually mean, without a separate legend.
    agg["FullName"] = agg["fondamentale"].map(dl.FONDAMENTALE_LABELS)

    fig = px.bar(
        agg, x="mean", y="Fundamental", orientation="h", error_x="std",
        category_orders={"Fundamental": order_labels},
        labels={"mean": "", "Fundamental": ""},
        color_discrete_sequence=[color],
        custom_data=["FullName"],
    )
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>%{x:.0f}<extra></extra>")
    fig.update_layout(
        height=PERF_CHART_HEIGHT, margin=PERF_CHART_MARGIN,
        title=dict(text=title, font=dict(size=12)),
        # None, not px.bar's labels={...: ""}: an empty-string axis title
        # still reserves its row, which shrank this chart's plot area by
        # ~28px against the scatter beside it and pushed every row out of
        # line with it.
        xaxis_title=None, yaxis_title=None,
        xaxis=dict(range=x_range),
        # Explicit range, not just categoryarray: the array fixes the row
        # ORDER, but a categorical axis still auto-ranges to only the
        # categories its own traces actually use -- so a fundamental with
        # E% data but no Index data left the two charts spanning a
        # different number of slots, i.e. rows at different pixels.
        yaxis=dict(
            categoryorder="array", categoryarray=order_labels[::-1],
            range=[-0.5, len(order_labels) - 0.5],
            # Every row labelled: at this height Plotly's automatic tick
            # selection dropped every other acronym, so the chart listed
            # SRV/ATT/CTR/DIG/SET and silently hid REC/AAR/BLK/FB.
            tickmode="linear", tick0=0, dtick=1, tickfont=dict(size=9),
        ),
    )
    fig.update_traces(error_x=dict(thickness=1, width=3))
    st.plotly_chart(fig, width="stretch")


def _performance_range(recent: pd.DataFrame, value_col: str, title: str, color: str, is_percent: bool, x_range: list, order_labels: list[str]):
    """One scatter dot per match, per fundamental -- more recent matches
    more opaque. Thin gridlines across the fixed axis range (rather than
    an outline bar) are what makes each row readable now. Rows use the
    short fundamental acronyms (dl.FONDAMENTALE_ABBR) instead of full
    names -- "Attack after Reception" alone would crowd this tight a
    chart."""
    d = recent[recent["Tot"] > 0].copy()
    if d.empty:
        st.info(f"No {title.lower()} data in this period.")
        return

    d["Fundamental"] = d["fondamentale"].map(dl.FONDAMENTALE_ABBR)
    d["FullName"] = d["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    d["opacity"] = _recency_opacity(d)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d[value_col], y=d["Fundamental"], mode="markers",
        marker=dict(color=color, opacity=d["opacity"], size=8, line=dict(width=0)),
        showlegend=False,
        # Full fundamental name first, so the acronym on the axis never
        # needs a legend of its own to be understood.
        customdata=d[["FullName", "match"]],
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}: %{x" + (":.0%" if is_percent else "") + "}<extra></extra>",
    ))
    dtick = (x_range[1] - x_range[0]) / 4
    # A tick exactly at the range's own edge (e.g. 100%) can get clipped by
    # the plot border -- padding the range slightly beyond it, while
    # keeping tickvals at the true round numbers, keeps that last label
    # fully visible without shifting the gridlines/zeroline themselves.
    pad = dtick * 0.12
    fig.update_layout(
        height=PERF_CHART_HEIGHT, margin=PERF_CHART_MARGIN,
        title=dict(text=title, font=dict(size=12)),
        xaxis=dict(
            range=[x_range[0] - pad, x_range[1] + pad],
            tickmode="linear", tick0=x_range[0], dtick=dtick,
            tickformat=".0%" if is_percent else None,
            showgrid=True, gridcolor="rgba(255,255,255,0.14)", gridwidth=1,
            zeroline=True, zerolinecolor="rgba(255,255,255,0.3)", zerolinewidth=1,
        ),
        # Explicit range, not just categoryarray: the array fixes the row
        # ORDER, but a categorical axis still auto-ranges to only the
        # categories its own traces actually use -- so a fundamental with
        # E% data but no Index data left the two charts spanning a
        # different number of slots, i.e. rows at different pixels.
        yaxis=dict(
            categoryorder="array", categoryarray=order_labels[::-1],
            range=[-0.5, len(order_labels) - 0.5],
            # Every row labelled: at this height Plotly's automatic tick
            # selection dropped every other acronym, so the chart listed
            # SRV/ATT/CTR/DIG/SET and silently hid REC/AAR/BLK/FB.
            tickmode="linear", tick0=0, dtick=1, tickfont=dict(size=9),
        ),
    )
    st.plotly_chart(fig, width="stretch")


def _render_performance(surname: str, color: str):
    recent = _scoped_matches(surname)
    if recent.empty:
        st.info("No scouting data for this player in this period.")
        return

    # One shared row list for both charts: each used to derive its own from
    # whatever it happened to have data for, so a fundamental present in one
    # and not the other shifted every row below it out of alignment with
    # its neighbour.
    order = _ordered_fundamentals(set(recent.loc[recent["Tot"] > 0, "fondamentale"]))
    order_labels = [dl.FONDAMENTALE_ABBR[f] for f in order]

    col_eff, col_ind = st.columns(2)
    with col_eff:
        _performance_range(recent, "E_pct", "Efficiency E%", color, is_percent=True, x_range=[-1, 1], order_labels=order_labels)
    with col_ind:
        _performance_bar(recent, "Ind", "Index", color, x_range=[0, 100], order_labels=order_labels)


def _render_tqr_column(tqr: float, day, color: str):
    """TQR as a vertical 6-20 track standing beside the radar.

    Drawn from shapes rather than go.Indicator: its bullet gauge is
    horizontal-only, and this needs to run vertically to sit alongside
    the radar without stealing height from it. Red below the 15 recovery
    threshold, amber straddling it, green above -- the same reading as
    every other TQR colour in the app.
    """
    fig = go.Figure()
    for lo, hi, band in ((6, 14, LOW_COLOR), (14, 16, WARN_COLOR), (16, 20, GOOD_COLOR)):
        fig.add_shape(type="rect", x0=0, x1=1, y0=lo, y1=hi, fillcolor=band, line_width=0, layer="below")
    fig.add_shape(
        type="rect", x0=0.22, x1=0.78, y0=6, y1=tqr,
        fillcolor=color, line=dict(color="#000000", width=1.5),
    )
    fig.add_annotation(
        x=0.5, y=tqr, text=f"<b>{tqr:.1f}</b>", showarrow=False, yshift=11,
        font=dict(size=13, color="#f2f2f2"),
    )
    fig.update_xaxes(visible=False, range=[0, 1], fixedrange=True)
    fig.update_yaxes(
        range=[6, 20], side="right", fixedrange=True,
        tickvals=[6, 10, 15, 20], tickfont=dict(size=9, color="#9a9a9a"),
        showgrid=False, zeroline=False,
    )
    fig.update_layout(
        height=185, margin=dict(l=2, r=2, t=18, b=6), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")
    st.markdown(
        f'<div style="text-align:center;color:var(--muted);font-size:10px;margin-top:-10px;">'
        f'TQR<br>{day.strftime("%d %b")}</div>',
        unsafe_allow_html=True,
    )


def _player_metrics(surname: str) -> pd.DataFrame:
    """This player's own Foster/Gabbett series. Computed over her entire
    history (training_load's own default) so the first days inside the
    selected period still get a valid trailing 7/28-day context, then
    sliced to the period for display."""
    rpe = dl.load_wellness_data()["rpe"]
    return training_load.metrics_frame(rpe, player_name=surname)


# Which band the athlete's current ACWR falls in, and what that band
# means in the two words the gauge has room for. Ordered low-to-high so
# the first matching upper bound wins.
ACWR_ZONES = [
    (0.8, WARN_COLOR, "Undertrained"),
    (1.3, GOOD_COLOR, "Optimal recovery"),
    (1.5, WARN_COLOR, "Load creeping up"),
    (float("inf"), LOW_COLOR, "Injury-risk spike"),
]


def _acwr_zone(acwr: float) -> tuple[str, str]:
    for upper, color, label in ACWR_ZONES:
        if acwr < upper:
            return color, label
    return ACWR_ZONES[-1][1], ACWR_ZONES[-1][2]


def _render_player_readiness(surname: str, color: str):
    """Same ACWR gauge the Home/Loads pages show for the team, for one
    athlete -- the needle stays her own color, the risk bands keep the
    shared green/amber/red meaning so they read the same everywhere, and
    the caption underneath spells out which band she's actually in."""
    metrics = _player_metrics(surname).dropna(subset=["acwr"])
    if metrics.empty:
        st.info("Not enough training history for this player yet.")
        return
    _, end = filters.period()
    in_range = metrics.index[metrics.index <= pd.Timestamp(end)]
    if in_range.empty:
        st.info("No training data at or before the end of this period.")
        return

    ref_date = in_range.max()
    acwr = float(metrics.loc[ref_date, "acwr"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=acwr,
        number=dict(font=dict(size=30, color="#f2f2f2"), valueformat=".2f"),
        gauge=dict(
            axis=dict(range=[0, 2], tickfont=dict(size=9, color="#9a9a9a")),
            bar=dict(color=color, thickness=0.3, line=dict(color="#000000", width=1.5)),
            bgcolor="rgba(0,0,0,0)",
            steps=[
                {"range": [0, 0.8], "color": WARN_COLOR},
                {"range": [0.8, 1.3], "color": GOOD_COLOR},
                {"range": [1.3, 1.5], "color": WARN_COLOR},
                {"range": [1.5, 2], "color": LOW_COLOR},
            ],
        ),
    ))
    fig.update_layout(height=150, margin=dict(l=20, r=20, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

    zone_color, zone_label = _acwr_zone(acwr)
    st.markdown(
        f'<div style="text-align:center;margin-top:-10px;">'
        f'<span style="color:{zone_color};font-weight:700;font-size:0.95rem;">{zone_label}</span>'
        f'<div style="color:var(--muted);font-size:11px;">{ref_date.strftime("%d %b %Y")}</div></div>',
        unsafe_allow_html=True,
    )


def _render_player_acwr(surname: str, color: str):
    metrics = _player_metrics(surname)
    start, end = filters.period()
    d = metrics.loc[
        (metrics.index >= pd.Timestamp(start)) & (metrics.index <= pd.Timestamp(end))
    ].dropna(subset=["acwr"])
    if d.empty:
        st.info("Not enough training history in this period (ACWR needs 28+ prior days).")
        return

    top = max(2.5, float(d["acwr"].max()) + 0.2)
    fig = go.Figure()
    # Bars are that day's own training load, not the 7-day rolling sum --
    # the ACWR line above already carries the weekly picture, so repeating
    # it in the bars just hid the day-to-day pattern.
    fig.add_trace(go.Bar(
        x=d.index, y=d["daily_tl"], name="Daily load (TL)",
        marker_color=rgba_from_hex(color, 0.45),
    ))
    fig.add_trace(go.Scatter(
        x=d.index, y=d["acwr"], name="ACWR", yaxis="y2", line=dict(color=color, width=2),
    ))
    # Just the two bands that matter at a glance: the 0.8-1.3 sweet spot
    # and the >1.5 spike zone.
    fig.add_hrect(y0=0.8, y1=1.3, yref="y2", fillcolor="rgba(84,162,75,0.18)", line_width=0)
    fig.add_hrect(y0=1.5, y1=top, yref="y2", fillcolor="rgba(228,87,86,0.14)", line_width=0)
    fig.update_layout(
        yaxis=dict(title="Daily load (TL)"),
        yaxis2=dict(title="ACWR", overlaying="y", side="right", range=[0, top]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        height=230, margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, width="stretch")


def _render_player_jumps(surname: str, color: str):
    salti = dl.load_wellness_data()["salti"]
    p = filters.filter_by_date_col(salti)
    p = p[(p["player_name"] == surname)].dropna(subset=["SALTI"])
    if p.empty:
        st.info("No jump data for this player in this period.")
        return

    daily = p.groupby("Data", as_index=False)["SALTI"].sum().sort_values("Data")
    fig = go.Figure(go.Bar(
        x=daily["Data"], y=daily["SALTI"], marker_color=color,
        hovertemplate="%{x|%d %b %Y}<br>%{y:.0f} jumps<extra></extra>",
    ))
    fig.update_layout(
        height=200, margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Jumps"), xaxis=dict(title=None),
    )
    st.plotly_chart(fig, width="stretch")


def _render_wellness_radar(surname: str, color: str):
    wellness = dl.load_wellness_data()["wellness"]
    p = wellness[wellness["player_name"] == surname]
    if p.empty:
        st.info("No wellness data for this player.")
        return

    recent = filters.filter_by_date_col(p)
    if recent.empty:
        st.info("No wellness data for this player in this period.")
        return
    icons = list(WELLNESS_ICONS.values())
    # Paired with the icons so every trace can name the item on hover --
    # the emoji axis labels carry no text of their own by design.
    names = [WELLNESS_PARAM_LABELS[param] for param in WELLNESS_ICONS]

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

    tqr_last = last_day["Tqr"].mean()

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
    # Mean shape: no fill anymore, just a thin, slightly-transparent
    # outline (thinner and fainter than the most-recent-day line below, so
    # the two don't compete). mode="lines" must be explicit -- Plotly
    # defaults an unset mode to "lines+markers" for this few a points,
    # which was silently adding unstyled default-colored dots.
    r, theta = close_polygon(values, icons)
    names_closed, _ = close_polygon(names, icons)
    fig.add_trace(go.Scatterpolar(
        r=r, theta=theta, mode="lines", line=dict(color=rgba_from_hex(color, 0.7), width=1.2),
        showlegend=False, customdata=names_closed,
        hovertemplate="<b>%{customdata}</b><br>Period average: %{r:.1f}/5<extra></extra>",
    ))
    # Most recent day: a solid outline with filled dots, drawn last so it
    # stands out over the std band.
    r_last, theta_last = close_polygon(last_values, icons)
    fig.add_trace(go.Scatterpolar(
        r=r_last, theta=theta_last, mode="lines+markers",
        line=dict(color=color, width=2), marker=dict(color=color, size=7),
        showlegend=False, customdata=names_closed,
        hovertemplate="<b>%{customdata}</b><br>Latest day: %{r:.1f}/5<extra></extra>",
    ))
    fig.update_layout(**dark_polar_layout([1, 5]))
    fig.update_layout(
        height=185, margin=dict(l=45, r=45, t=18, b=18),
        polar=dict(
            radialaxis=dict(showticklabels=False, showline=False),
            angularaxis=dict(tickfont=dict(size=20)),
        ),
    )

    # Radar and the TQR track side by side, same height, so the wellness
    # box reads as one picture rather than a chart with a bar on top of it.
    col_radar, col_tqr = st.columns([4, 1])
    with col_radar:
        st.plotly_chart(fig, width="stretch", theme=None)
    with col_tqr:
        if pd.notna(tqr_last):
            _render_tqr_column(float(tqr_last), last_date, color)


def _render_overview(surname: str):
    player = pg.PLAYERS_BY_SURNAME[surname]
    color = pc.color_for(surname)
    stats = dl.load_player_stats()

    with st.container(border=True, key="player_overview_box"):
        # Photo at a quarter of its old size -- it identifies who's
        # selected, the charts below are what the panel is actually for.
        col_photo, col_info = st.columns([0.37, 3.63])
        with col_photo:
            # Full 254px source, sized down to 64 by the CSS below rather
            # than by Streamlit: asking for width=64 hands the browser a
            # 64px-wide image, which is then upscaled again on any
            # higher-density display and looks soft. Letting the browser
            # downsample the original keeps it sharp at any DPI.
            st.image(pg.photo_path(player))
        with col_info:
            cap = "👑 " if player.get("captain") else ""
            st.markdown(f'<div class="overview-name">{cap}{player["first"]} {player["last"]}</div>', unsafe_allow_html=True)
            if surname in stats.index:
                row = stats.loc[surname]
                st.markdown(f"**{row['points']}** pts · **{row['appearances']}** matches")

        # Row 1: scouting (E% and Index side by side inside it).
        st.markdown("**Performance**")
        _render_performance(surname, color)

        # Row 2: jumps and wellness.
        col_jumps, col_well = st.columns(2)
        with col_jumps:
            st.markdown("**Jumps** over time")
            _render_player_jumps(surname, color)
        with col_well:
            st.markdown("**Wellness**")
            _render_wellness_radar(surname, color)

        # Row 3: readiness gauge (narrow) beside the load chart.
        col_gauge, col_acwr = st.columns([1, 3])
        with col_gauge:
            st.markdown("**Readiness** · ACWR, last day")
            _render_player_readiness(surname, color)
        with col_acwr:
            st.markdown("**ACWR** & daily load")
            _render_player_acwr(surname, color)


def render():
    st.markdown(BASE_CARD_CSS, unsafe_allow_html=True)
    st.markdown(_role_border_css(), unsafe_allow_html=True)
    st.markdown(_player_card_css(), unsafe_allow_html=True)

    st.session_state.setdefault("selected_player", "Orro")
    selected = st.session_state["selected_player"]
    # A plain dict-append instead of itertools.groupby -- ALL_PLAYERS is no
    # longer sorted by role (players_grid.GRID_ROWS interleaves a Libero at
    # the end of each row for the Wellness page's 3x5 grid), and groupby
    # only merges *consecutive* matching items, silently dropping all but
    # the last same-role run otherwise.
    groups: dict[str, list[dict]] = {}
    for p in pg.ALL_PLAYERS:
        groups.setdefault(p["role"], []).append(p)

    # Narrow now that the cards are vertical name strips -- the detail
    # panel gets the rest, since it carries every chart on this page.
    col_grid, col_overview = st.columns([1, 3])

    with col_grid:
        # Row 1: Setter + Opposite side by side, in separate boxes (2 cards
        # each, so equal-width columns keep every card the same size).
        col_setter, col_opposite = st.columns(2)
        with col_setter:
            _render_role_group("Setter", groups["Setter"], selected)
        with col_opposite:
            _render_role_group("Opposite", groups["Opposite"], selected)

        # Rows 2-3: Outside Hitter and Middle Blocker, 4 cards each, full width.
        _render_role_group("Outside Hitter", groups["Outside Hitter"], selected)
        _render_role_group("Middle Blocker", groups["Middle Blocker"], selected)

        # Liberos are 3 cards where the rows above are 4, so the crest sits
        # in that spare slot -- outside the role box, as its own small card.
        col_libero, col_crest = st.columns([3, 1])
        with col_libero:
            _render_role_group("Libero", groups["Libero"], selected)
        with col_crest:
            with st.container(border=True, key="player_crest_box"):
                st.image(pg.CREST_PATH, width="stretch")
                st.markdown('<div class="crest-wordmark">Vero Volley Milano</div>', unsafe_allow_html=True)

    with col_overview:
        _render_overview(selected)
