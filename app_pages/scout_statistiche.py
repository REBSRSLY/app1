import pandas as pd
import plotly.colors as pcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import match_calendar as mc
import player_colors as pc
import players_grid as pg
from ui_helpers import close_polygon, dark_polar_layout, rgba_from_hex

# Result -> color for the "Trend over time" bars, dark-to-light-to-dark
# across the 6 possible scorelines (dominant win -> tie-break win ->
# tie-break loss -> dominant loss). Distinct from RESULT_COLORS/
# result_points elsewhere in the app, which only need the coarser 4-level
# points scale (3-0 and 3-1 are both "3 points" there) -- this chart's
# whole point is to distinguish all 6 by color.
SCORE_TREND_COLORS = {
    "3-0": "#1B5E20",
    "3-1": "#54A24B",
    "3-2": "#F0C808",
    "2-3": "#F58518",
    "1-3": "#E45756",
    "0-3": "#7A1B1B",
}

# Fixed colors for set type: same color everywhere in the app, order never cycled.
# Keys are the raw (Italian) values from the source data; translated to English
# display labels only where they're plotted (see PALLA_COLORS_EN below).
PALLA_COLORS = {
    "Alta": "#4C78A8",
    "Media": "#F58518",
    "Veloce": "#54A24B",
    "Tesa": "#E45756",
    "Other": "#B0B0B0",
}
PALLA_COLORS_EN = {dl.PALLA_LABELS[k]: v for k, v in PALLA_COLORS.items()}

# Fixed worst-to-best color per outcome symbol, reused by the outcome-
# distribution chart regardless of which fundamental is selected.
OUTCOME_COLORS = {"=": "#E45756", "-": "#F58518", "!": "#B0B0B0", "+": "#54A24B", "#": "#2E7D32", "/": "#8D6E63"}
SYMBOL_TO_COL = {"=": "Err", "-": "Neg", "!": "Neutral", "+": "Pos", "#": "Perfect", "/": "Slash"}

# Column layout of the original Data Volley "by fundamental" export (see
# data_loader.SCOUT_COLS / _parse_scout_sheet), used only by the "Scout
# Sheet" section to reproduce the sheet's column order exactly. Row
# order reuses dl.FONDAMENTALE_ORDER (the same constant every other
# fundamental-breakdown chart in the app follows).
RAW_PALLA_ORDER = ["Totale", "Alta", "Media", "Veloce", "Tesa", "Other"]
RAW_COLUMN_RENAME = {
    "P": "P", "Set": "Set", "Ind": "Ind", "E_pct": "E%", "Tot": "Tot",
    "Err": "=", "Err_pct": "= %", "Err_BP": "= BP", "Err_pC": "= pC",
    "Slash": "/", "Slash_pct": "/ %", "Slash_BP": "/ BP", "Slash_pC": "/ pC",
    "Neg": "-", "Neg_pct": "- %",
    "Neutral": "!", "Neutral_pct": "! %",
    "Pos": "+", "Pos_pct": "+ %",
    "Perfect": "#", "Perfect_pct": "# %", "Perfect_BP": "# BP", "Perfect_pC": "# pC",
}
RAW_PERCENT_COLUMNS = ["E%", "= %", "/ %", "- %", "! %", "+ %", "# %"]
# Column groups the raw sheet is chunked into, a thin spacer column
# rendered between each -- mirrors the shaded column groupings of the
# original Data Volley export.
RAW_COLUMN_GROUPS = [
    ["P", "Set", "Ind", "E_pct", "Tot"],
    ["Err", "Err_pct", "Err_BP", "Err_pC"],
    ["Slash", "Slash_pct", "Slash_BP", "Slash_pC"],
    ["Neg", "Neg_pct"],
    ["Neutral", "Neutral_pct"],
    ["Pos", "Pos_pct"],
    ["Perfect", "Perfect_pct", "Perfect_BP", "Perfect_pC"],
]

SECTIONS = ["Team Profile", "General stats", "Game distribution", "Scout Sheet"]

# Which front-row zone each role attacks from -- we don't have real
# per-attack court coordinates, so this fixed assumption (given by the
# coaching staff) stands in for it. Setters aren't attackers here: their
# own "Alzata" numbers get a side table instead (see
# _render_zone_distribution) rather than being folded into P2.
ZONE_ROLES = {
    "P4": ["Outside Hitter"],
    "P3": ["Middle Blocker"],
    "P2": ["Opposite"],
}
ZONE_X = {"P4": (0, 3), "P3": (3, 6), "P2": (6, 9)}
SETTER_SURNAMES = ["Orro", "Prandi"]


def _in_scope_dates() -> set[str]:
    return {m["date"] for m in filters.matches_in_scope()}


def _scope_scout(scout: pd.DataFrame) -> pd.DataFrame:
    """Collapse every match currently in the sidebar's scope into one
    virtual sheet per (fondamentale, palla, player): action counts sum,
    rate columns (E%, Ind, outcome %s) become Tot-weighted averages across
    the scoped matches. Falls back to the season-total sheet if nothing
    is in scope."""
    d = scout[scout["match"].isin(_in_scope_dates())]
    if d.empty:
        return scout[scout["match"] == dl.SEASON_LABEL].copy()

    # dropna=False matters here: team rows have player_code=None (only
    # players get a code), and pandas groupby silently drops every row
    # whose grouping key is NaN/None unless told not to -- without this
    # every team row would vanish from the aggregate.
    group_cols = ["fondamentale", "palla", "player_code", "player_name", "is_team"]
    count_cols = ["Tot", "Err", "Slash", "Neg", "Neutral", "Pos", "Perfect"]
    out = d.groupby(group_cols, observed=True, dropna=False)[count_cols].sum().reset_index()

    weighted = d.assign(_e=d["E_pct"] * d["Tot"], _ind=d["Ind"] * d["Tot"])
    weighted = weighted.groupby(group_cols, observed=True, dropna=False)[["_e", "_ind"]].sum().reset_index()
    out = out.merge(weighted, on=group_cols)

    tot_safe = out["Tot"].replace(0, pd.NA)
    out["E_pct"] = out["_e"] / tot_safe
    out["Ind"] = out["_ind"] / tot_safe
    for symbol, col in SYMBOL_TO_COL.items():
        out[f"{col}_pct"] = out[col] / tot_safe
    return out.drop(columns=["_e", "_ind"])


# The four metrics selectable in the Team Profile bar chart: column name,
# axis label, and whether it's a 0-1 rate (percent-formatted axis) or a
# plain index value like Ind.
TEAM_PROFILE_METRICS = {
    "E%": ("E_pct", "Efficiency E%", True),
    "Ind": ("Ind", "Index", False),
    "=%": ("Err_pct", "Error %", True),
    "#%": ("Perfect_pct", "% Point / Perfect", True),
}


def _render_team_profile(scoped: pd.DataFrame, metric_label: str):
    """Team performance across every fundamental at once, for the selected
    metric -- the "shape" of the team's game (strong serve, shaky
    reception, etc.) that the per-fundamental breakdown elsewhere can't
    show on its own."""
    team = scoped[scoped["is_team"] & (scoped["palla"] == "Totale") & (scoped["Tot"] > 0)].copy()
    if team.empty:
        return

    metric_col, axis_label, is_pct = TEAM_PROFILE_METRICS[metric_label]
    present = [f for f in dl.FONDAMENTALE_ORDER if f in set(team["fondamentale"])]
    order_labels = [dl.FONDAMENTALE_ABBR[f] for f in present]
    team["Fundamental"] = team["fondamentale"].map(dl.FONDAMENTALE_ABBR)
    # Full name on hover, so the axis acronym never needs its own legend.
    team["FullName"] = team["fondamentale"].map(dl.FONDAMENTALE_LABELS)
    # Fundamentals with few actions in this scope (e.g. Block early in a
    # short period) get faded out rather than drawn as confidently as a
    # fundamental backed by hundreds of actions -- see reliability_alpha.
    team["_alpha"] = dl.reliability_alpha(team["Tot"])
    any_low = bool((team["Tot"] < dl.MIN_RELIABLE_N).any())

    if metric_col == "E_pct":
        # Only E% is a diverging (can-go-negative) measure -- the others
        # are plain 0-and-up rates/counts, so a single flat color reads
        # better there than a gradient with no natural zero to diverge from.
        fig = px.bar(
            team, x=metric_col, y="Fundamental", orientation="h",
            category_orders={"Fundamental": order_labels},
            color=metric_col, color_continuous_scale="RdBu", color_continuous_midpoint=0,
            labels={metric_col: axis_label, "Fundamental": ""},
            custom_data=["FullName", "Tot"],
        )
        fig.update_layout(coloraxis_showscale=False)
    else:
        fig = px.bar(
            team, x=metric_col, y="Fundamental", orientation="h",
            category_orders={"Fundamental": order_labels},
            labels={metric_col: axis_label, "Fundamental": ""},
            color_discrete_sequence=["#1655a5"],
            custom_data=["FullName", "Tot"],
        )
    # Opacity list must align with `team`'s own row order (what the trace's
    # x/y arrays are built from), NOT order_labels -- category_orders only
    # reorders the axis display, it doesn't reorder the underlying trace data.
    fig.update_traces(marker=dict(opacity=team["_alpha"].tolist()))
    value_fmt = ":.0%" if is_pct else ":.1f"
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>" + axis_label + ": %{x" + value_fmt
        + "}<br>%{customdata[1]:d} actions<extra></extra>"
    )
    # E_pct etc. are mathematically bounded to [-1, 1] and never actually
    # exceed 100% -- but Plotly's autorange only fits the tallest bar, so a
    # high-but-valid value (season Alzata E% = 91%) can visually run past
    # the last gridline and look like it broke the scale. Pin an explicit
    # range that always includes the full 0-100% span (and any negative
    # values, e.g. Battuta) so that's never ambiguous.
    xaxis_kwargs = dict(tickformat=".0%") if is_pct else {}
    if is_pct:
        lo = min(0.0, float(team[metric_col].min())) - 0.05
        hi = max(1.0, float(team[metric_col].max())) + 0.05
        xaxis_kwargs["range"] = [lo, hi]
    fig.update_layout(
        xaxis=xaxis_kwargs, height=280,
        yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
        margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    caption = f"Team {axis_label.lower()} for every fundamental in the selected scope."
    if any_low:
        caption += f" Faded bars are built on fewer than {dl.MIN_RELIABLE_N} actions — treat as indicative, not reliable."
    st.caption(caption)


def _render_team_outcome_mix(scoped: pd.DataFrame, fond_sel: str):
    """Team-wide outcome mix for the selected fundamental -- the share of
    every action landing in each outcome bucket (=/-/!/+/#, plus the
    slash), not just the headline E% that collapses all of that into one
    number. Follows the Trend chart's own fundamental picker rather than
    being pinned to the serve, so both boxes always describe the same
    fundamental."""
    label = dl.FONDAMENTALE_LABELS.get(fond_sel, fond_sel)
    team = scoped[
        scoped["is_team"] & (scoped["fondamentale"] == fond_sel)
        & (scoped["palla"] == "Totale") & (scoped["Tot"] > 0)
    ]
    if team.empty:
        st.info(f"No {label.lower()} data in this scope.")
        return

    row = team.iloc[0]
    legenda = dl.legenda_fondamentale(fond_sel)
    rows = []
    for simbolo, nome, _ in legenda:
        col = SYMBOL_TO_COL.get(simbolo)
        if col is None:
            continue
        count = row.get(col, 0)
        rows.append({"Outcome": f"{nome} ({simbolo})", "count": 0 if pd.isna(count) else count, "symbol": simbolo})
    d = pd.DataFrame(rows)
    if d.empty or d["count"].sum() == 0:
        st.info(f"No {label.lower()} outcome data in this scope.")
        return

    total_n = int(d["count"].sum())
    low = dl.is_low_sample(total_n)
    color_map = {f"{nome} ({simbolo})": OUTCOME_COLORS.get(simbolo, "#888888") for simbolo, nome, _ in legenda}
    fig = px.pie(d, names="Outcome", values="count", hole=0.5, color="Outcome", color_discrete_map=color_map)
    fig.update_traces(textinfo="percent+label")
    # The donut's own hole is otherwise dead space -- putting the action
    # count there means the sample size behind every slice's percentage
    # sits right at the chart's visual center, not buried in the caption
    # below where it's easy to skip past. Red when it's too thin to trust
    # (see MIN_RELIABLE_N), the same neutral white as everywhere else otherwise.
    fig.add_annotation(
        text=f"<b>{total_n}</b><br><span style='font-size:11px'>actions</span>",
        showarrow=False, font=dict(size=20, color="#E45756" if low else "#ffffff"),
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, width="stretch")
    caption = f"Share of the team's total {label.lower()} actions landing in each outcome."
    if low:
        caption += f" Only {total_n} actions in this scope — shares are indicative, not reliable."
    st.caption(caption)


def _render_team_trend(scout: pd.DataFrame) -> str:
    """Team volume (bars, colored by that match's result) and efficiency
    (line) per match for one fundamental, over the scoped matches --
    whether the team is trending up or down isn't visible from any of the
    other, single-snapshot charts below, and coloring the bars by result
    surfaces whether efficiency swings track winning/losing or move
    independently of it.

    Returns the selected fundamental: this picker drives the outcome mix
    box below as well, so the section describes one fundamental at a time
    rather than two unrelated ones.
    """
    fond_options = dl.FONDAMENTALE_ORDER
    fond_sel = st.selectbox(
        "Fundamental", fond_options, index=fond_options.index("Attacco"),
        format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f), key="team_trend_fond",
    )
    d = scout[
        scout["match"].isin(_in_scope_dates()) & (scout["fondamentale"] == fond_sel)
        & scout["is_team"] & (scout["palla"] == "Totale") & (scout["match"] != dl.SEASON_LABEL)
    ].copy()
    if d.empty:
        st.info("No data available for this fundamental in the selected scope.")
        return fond_sel

    d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
    d = d.sort_values("pdate")

    matches = d["match"].map(mc.MATCH_BY_DATE)
    scores = matches.apply(lambda m: m["score"] if m else None)
    # Semi-transparent so the E% line stays readable crossing over the bars.
    bar_colors = [rgba_from_hex(SCORE_TREND_COLORS.get(s, "#4C78A8"), 0.55) for s in scores]
    customdata = list(zip(
        d["pdate"].dt.strftime("%d/%m/%y"),
        matches.apply(lambda m: m["competition"] if m else "—"),
        matches.apply(lambda m: m["opponent"] if m else "—"),
        matches.apply(lambda m: "Home" if m and m["home"] else "Away"),
        scores.fillna("—"),
    ))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d["pdate"], y=d["Tot"], name="Actions", marker_color=bar_colors, yaxis="y2",
        customdata=customdata, showlegend=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
            "vs %{customdata[2]} (%{customdata[3]}) · %{customdata[4]}<br>"
            "Actions: %{y}<extra></extra>"
        ),
    ))
    # Marker size follows that match's own action volume: a match E% built
    # on 3 actions swings wildly on nothing and shouldn't read as visually
    # equal to one built on 25 -- the bars behind it already show volume,
    # but a small dot on the line itself is what a reader's eye actually
    # tracks across matches.
    marker_sizes = 6 + 10 * dl.reliability_alpha(d["Tot"], floor=0.0)
    fig.add_trace(go.Scatter(
        x=d["pdate"], y=d["E_pct"], name="Efficiency E%", mode="lines+markers",
        line=dict(color="#29B6F6", width=2), marker=dict(size=marker_sizes),
        showlegend=False, customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
            "vs %{customdata[2]} (%{customdata[3]}) · %{customdata[4]}<br>"
            "Efficiency E%: %{y:.0%}<extra></extra>"
        ),
    ))
    # Legend-only swatches (no real data points) so the result color code
    # is the only thing shown in the chart's top legend.
    for score, color in SCORE_TREND_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", marker=dict(size=9, color=color, symbol="square"),
            name=score, hoverinfo="skip",
        ))
    fig.update_layout(
        height=340, margin=dict(l=0, r=10, t=55, b=10),
        xaxis_title="Match date",
        yaxis=dict(title="Efficiency E%", tickformat=".0%"),
        yaxis2=dict(title="Actions", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.22, font=dict(size=11)),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Dot size on the E% line follows that match's action volume — small dots are built on fewer actions.")
    return fond_sel


def _render_team_profile_section(scoped: pd.DataFrame, scout: pd.DataFrame):
    st.caption("Team-wide performance across every fundamental, from the 'Squadra' rows of the scout sheet.")

    with st.container(border=True):
        st.markdown("**Trend over time** · team efficiency per match")
        fond_sel = _render_team_trend(scout)

    fond_label = dl.FONDAMENTALE_LABELS.get(fond_sel, fond_sel)
    col_profile, col_mix = st.columns(2)
    with col_profile:
        with st.container(border=True):
            st.markdown("**Team profile** · pick a metric")
            metric_label = st.segmented_control(
                "Metric", list(TEAM_PROFILE_METRICS.keys()), default="E%", required=True, key="team_profile_metric",
            )
            _render_team_profile(scoped, metric_label)
    with col_mix:
        with st.container(border=True):
            st.markdown(f"**Outcome mix** · {fond_label.lower()}, team")
            _render_team_outcome_mix(scoped, fond_sel)


def _render_how_to_expander(fond_sel: str, fond_label: str):
    legenda = dl.legenda_fondamentale(fond_sel)
    formule = dl.formula_fondamentale(fond_sel)
    if not legenda and not formule:
        return
    with st.expander(f"How to read \"{fond_label}\"", icon=":material/menu_book:"):
        for simbolo, nome, descrizione in legenda:
            st.markdown(f"**{simbolo}** · {nome} — {descrizione}")
        if formule:
            st.markdown("---")
            st.markdown(f"**E%** = `{formule['e_pct']}`")
            if formule["ind_kind"] == "rate":
                st.markdown(
                    f"**Ind** = `{formule['ind']}` — a 0–10 rate of how often the "
                    f"outcome is perfect (#), *not* a weighted average across all grades."
                )
            else:
                st.markdown(
                    f"**Ind** = `{formule['ind']}` — a 0–100 weighted average across "
                    f"all 6 grades, higher weight = better outcome."
                )


def _render_outcome_distribution(base: pd.DataFrame, fond_sel: str, player_order: list[str]):
    """100%-stacked bar of each player's outcome mix (error/poor/neutral/
    good/perfect) for the selected fundamental -- two players can share
    the same E% while one is far more consistent than the other, which
    this shows and a single efficiency number can't."""
    legenda = dl.legenda_fondamentale(fond_sel)
    if not legenda:
        return

    rows = []
    for _, r in base.iterrows():
        if r["Tot"] <= 0:
            continue
        for rank, (simbolo, nome, _) in enumerate(legenda):
            col = SYMBOL_TO_COL.get(simbolo)
            if col is None or col not in base.columns:
                continue
            count = r.get(col, 0)
            count = 0 if pd.isna(count) else count
            rows.append({
                "player_name": r["player_name"], "Outcome": f"{nome} ({simbolo})",
                "share": count / r["Tot"], "rank": rank, "Tot": int(r["Tot"]),
            })
    d = pd.DataFrame(rows)
    if d.empty:
        return

    order_labels = d.sort_values("rank")["Outcome"].drop_duplicates().tolist()
    color_map = {f"{nome} ({simbolo})": OUTCOME_COLORS.get(simbolo, "#888888") for simbolo, nome, _ in legenda}
    any_low = bool((d.drop_duplicates("player_name")["Tot"] < dl.MIN_RELIABLE_N).any())

    fig = px.bar(
        d, x="share", y="player_name", color="Outcome", orientation="h",
        category_orders={"player_name": player_order[::-1], "Outcome": order_labels},
        color_discrete_map=color_map,
        labels={"share": "Share of actions", "player_name": ""},
        custom_data=["Tot"],
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b> · %{fullData.name}<br>Share: %{x:.0%}<br>%{customdata[0]:d} actions total<extra></extra>"
    )
    fig.update_layout(
        barmode="stack", xaxis_tickformat=".0%", legend_title_text="Outcome",
        height=max(220, 34 * len(player_order)), margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    if any_low:
        st.caption(f"Players with fewer than {dl.MIN_RELIABLE_N} total actions (hover a bar for the count) have a less reliable mix.")


def _render_volume_efficiency(base: pd.DataFrame, perfetto_lbl: str):
    """Bubble scatter (bubble size = volume): separates high-volume,
    high-efficiency go-to options from low-volume specialists and from
    players who are getting a lot of touches without producing."""
    d = base[base["Tot"] > 0]
    if d.empty:
        return

    fig = px.scatter(
        d, x="E_pct", y="Perfect_pct", size="Tot", color="player_name",
        color_discrete_map=pc.color_map(d["player_name"].unique()),
        labels={"E_pct": "Efficiency E%", "Perfect_pct": f"% {perfetto_lbl}", "player_name": "Player"},
        hover_name="player_name", size_max=32,
    )
    fig.update_layout(
        xaxis_tickformat=".0%", yaxis_tickformat=".0%", showlegend=False,
        height=320, margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Bubble size = volume of actions. Top-right = high-volume and high-quality.")


def _render_general_stats(scoped: pd.DataFrame):
    fondamentali = sorted(scoped["fondamentale"].unique())
    fond_sel = st.selectbox(
        "Fundamental", fondamentali,
        index=fondamentali.index("Attacco") if "Attacco" in fondamentali else 0,
        format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f),
        key="gen_fond",
    )
    fond_label = dl.FONDAMENTALE_LABELS.get(fond_sel, fond_sel)

    perfetto_lbl = dl.perfetto_label(fond_sel)
    errore_lbl = dl.errore_label(fond_sel)
    _render_how_to_expander(fond_sel, fond_label)

    base = scoped[(scoped["fondamentale"] == fond_sel) & (scoped["palla"] == "Totale")]
    team_row = base[base["is_team"]]
    players = base[~base["is_team"]].sort_values("Tot", ascending=False)

    if team_row.empty or players.empty:
        st.info("No data available for this fundamental in the selected scope.")
        return

    t = team_row.iloc[0]
    with st.container(horizontal=True):
        st.metric("Total actions", int(t["Tot"]), border=True)
        st.metric("Efficiency (E%)", f"{t['E_pct'] * 100:.0f}%", border=True)
        st.metric(f"% {perfetto_lbl} (#)", f"{t['Perfect_pct'] * 100:.0f}%" if pd.notna(t["Perfect_pct"]) else "—", border=True)
        st.metric(f"% {errore_lbl} (=)", f"{t['Err_pct'] * 100:.0f}%" if pd.notna(t["Err_pct"]) else "—", border=True)

    col_vol, col_eff = st.columns(2)
    with col_vol:
        with st.container(border=True):
            st.markdown(f"**Actions per player · {fond_label}**")
            fig_vol = px.bar(
                players, x="Tot", y="player_name", orientation="h",
                labels={"Tot": "Total actions", "player_name": ""},
                color="player_name", color_discrete_map=pc.color_map(players["player_name"].unique()),
            )
            fig_vol.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            st.plotly_chart(fig_vol, width="stretch")

    with col_eff:
        with st.container(border=True):
            st.markdown(f"**Efficiency (E%) per player · {fond_label}**")
            players_eff = players.sort_values("E_pct")
            fig_effp = px.bar(
                players_eff, x="E_pct", y="player_name", orientation="h",
                labels={"E_pct": "Efficiency E%", "player_name": ""},
                color="player_name", color_discrete_map=pc.color_map(players_eff["player_name"].unique()),
                custom_data=["Tot"],
            )
            # Faded for players with few actions -- their E% sits on the same
            # axis as a starter's hundreds of actions, so nothing else in this
            # chart signals it's a much shakier number.
            fig_effp.update_traces(
                marker=dict(opacity=dl.reliability_alpha(players_eff["Tot"]).tolist()),
                hovertemplate="<b>%{y}</b><br>Efficiency E%: %{x:.0%}<br>%{customdata[0]:d} actions<extra></extra>",
            )
            fig_effp.update_layout(showlegend=False, xaxis_tickformat=".0%")
            st.plotly_chart(fig_effp, width="stretch")
            if (players_eff["Tot"] < dl.MIN_RELIABLE_N).any():
                st.caption(f"Faded bars are built on fewer than {dl.MIN_RELIABLE_N} actions.")

    with st.container(border=True):
        st.markdown(f"**Outcome mix per player** · {fond_label}")
        _render_outcome_distribution(base[~base["is_team"]], fond_sel, players["player_name"].tolist())

    with st.container(border=True):
        st.markdown(f"**Volume vs. quality** · {fond_label}")
        _render_volume_efficiency(players, perfetto_lbl)

    with st.container(border=True):
        st.markdown(f"**Detail per player** · {fond_label}")
        col_perfetto = f"% {perfetto_lbl} (#)"
        col_errore = f"% {errore_lbl} (=)"
        tabella = players[["player_name", "Tot", "E_pct", "Err_pct", "Slash_pct", "Neg_pct", "Neutral_pct", "Pos_pct", "Perfect_pct"]].rename(columns={
            "player_name": "Player",
            "E_pct": "Efficiency E%",
            "Err_pct": col_errore,
            "Slash_pct": "/",
            "Neg_pct": "-",
            "Neutral_pct": "!",
            "Pos_pct": "+",
            "Perfect_pct": col_perfetto,
        })
        percent_cols = ["Efficiency E%", col_errore, "/", "-", "!", "+", col_perfetto]
        st.dataframe(
            tabella,
            hide_index=True,
            width="stretch",
            column_config={
                "Tot": st.column_config.NumberColumn(
                    format="%d",
                    help=f"Actions this row is based on. Below {dl.MIN_RELIABLE_N}, its percentages are indicative, not reliable.",
                ),
                **{c: st.column_config.NumberColumn(format="percent") for c in percent_cols},
            },
        )


def _render_cumulative_actions(scout: pd.DataFrame, fond_sel2: str, height: int = 340):
    """Running total of actions per player over the scoped matches, in
    chronological order -- shows workload building up over time rather
    than just the final tally, and who's carrying an increasing share."""
    d = scout[
        scout["match"].isin(_in_scope_dates()) & (scout["fondamentale"] == fond_sel2)
        & (~scout["is_team"]) & (scout["palla"] == "Totale") & (scout["match"] != dl.SEASON_LABEL)
    ].copy()
    if d.empty:
        st.info("No data available for this fundamental in the selected scope.")
        return

    # mc.parsed_date returns plain datetime.date objects; px.line's date-axis
    # auto-ranging gets confused by an object-dtype column of those (it
    # rendered a real bug once: a multi-month span collapsed to a
    # sub-millisecond x-axis window) -- pd.to_datetime gives it a proper
    # datetime64 column to work with instead.
    d["pdate"] = pd.to_datetime(d["match"].apply(mc.parsed_date))
    daily = d.groupby(["pdate", "player_name"], as_index=False)["Tot"].sum().sort_values("pdate")
    daily["cumulative"] = daily.groupby("player_name")["Tot"].cumsum()

    fig = px.line(
        daily, x="pdate", y="cumulative", color="player_name",
        color_discrete_map=pc.color_map(daily["player_name"].unique()),
        labels={"pdate": "Match date", "cumulative": "Cumulative actions", "player_name": "Player"},
        markers=True,
    )
    fig.update_layout(legend_title_text="Player", height=height, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")


def _add_court_shapes(fig: go.Figure):
    """Court outline, net, 3m attack line and back-row zone labels shared
    by both zone-distribution charts below."""
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=9, line=dict(color="rgba(255,255,255,0.5)", width=2))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#ffffff", width=5))
    fig.add_annotation(x=4.5, y=9.35, text="NET", showarrow=False, font=dict(color="rgba(255,255,255,0.6)", size=11))
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dash"))
    for x in (3, 6):
        fig.add_shape(type="line", x0=x, y0=0, x1=x, y1=9, line=dict(color="rgba(255,255,255,0.25)", width=1))
    for label, (x, y) in {"P5": (1.5, 3), "P6": (4.5, 3), "P1": (7.5, 3)}.items():
        fig.add_annotation(x=x, y=y, text=f"<span style='opacity:0.35'>{label}</span>", showarrow=False, font=dict(color="#ffffff", size=13))


# Coloring config per selectable court metric, same 4 metrics as the Team
# Profile chart and the Heatmap. E% is diverging (can go negative) and
# zero-centered so the scale's pale midpoint sits exactly at E%=0; the
# other three are plain 0-and-up rates/counts, so each gets a sequential
# scale instead (pale at the low end, not the middle). Ind's cmax has no
# natural fixed ceiling -- _render_zone_efficiency_court overrides it per
# call to whatever this scope's zones actually reach.
ZONE_METRIC_OPTIONS = {"E%": "E_pct", "Ind": "Ind", "=%": "Err_pct", "#%": "Perfect_pct"}
ZONE_METRIC_CONFIG = {
    "E_pct": {"colorscale": "RdYlGn", "cmin": -0.6, "cmax": 0.6, "diverging": True, "label": "E%", "is_pct": True},
    "Ind": {"colorscale": "Blues", "cmin": 0.0, "cmax": 1.0, "diverging": False, "label": "Ind", "is_pct": False},
    "Err_pct": {"colorscale": "Reds", "cmin": 0.0, "cmax": 0.6, "diverging": False, "label": "=%", "is_pct": True},
    "Perfect_pct": {"colorscale": "Greens", "cmin": 0.0, "cmax": 0.6, "diverging": False, "label": "#%", "is_pct": True},
}


def _zone_color(value, cfg: dict, alpha: float = 0.75) -> str:
    if value is None or pd.isna(value):
        return "rgba(255,255,255,0.08)"
    t = max(0.0, min(1.0, (value - cfg["cmin"]) / (cfg["cmax"] - cfg["cmin"])))
    rgb = pcolors.sample_colorscale(cfg["colorscale"], [t])[0]
    return rgb.replace("rgb", "rgba").replace(")", f",{alpha})")


def _zone_text_color(value, cfg: dict) -> str:
    """Near the scale's pale end the fill is too light for white text to
    read -- switch to black there; everywhere else (more saturated colors)
    white stays legible. Diverging scales are pale at the center; sequential
    ones are pale at the low end."""
    if value is None or pd.isna(value):
        return "#ffffff"
    if cfg["diverging"]:
        return "#000000" if abs(value) <= 0.2 else "#ffffff"
    span = cfg["cmax"] - cfg["cmin"]
    return "#000000" if (value - cfg["cmin"]) <= 0.35 * span else "#ffffff"


ZONE_TABLE_RENAME = {
    "player_name": "Player", "Tot": "Attacks", "E_pct": "E%",
    "Err_pct": "=", "Slash_pct": "/", "Neg_pct": "-", "Neutral_pct": "!", "Pos_pct": "+", "Perfect_pct": "#",
}
ZONE_TABLE_PERCENT_COLS = ["E%", "=", "/", "-", "!", "+", "#"]


def _render_zone_efficiency_court(attack_totale: pd.DataFrame, metric_col: str = "E_pct") -> dict:
    """Chart 4: each zone filled by a single color for the selected metric,
    with a real gradient colorbar (rather than the flat color patches from
    the old "Court zones" section) to read the shade against. Returns
    zone_stats -- the per-zone tables render separately (see
    _render_zone_efficiency_tables), in the column next to this one."""
    cfg = dict(ZONE_METRIC_CONFIG[metric_col])
    zone_stats = {}
    for zone, roles_in_zone in ZONE_ROLES.items():
        sub = attack_totale[attack_totale["Role"].isin(roles_in_zone) & (attack_totale["Tot"] > 0)]
        tot = sub["Tot"].sum()
        value = (sub[metric_col] * sub["Tot"]).sum() / tot if tot > 0 else None
        zone_stats[zone] = {"tot": int(tot), "value": value, "players": sub.sort_values("Tot", ascending=False)}

    if metric_col == "Ind":
        # Ind has no natural fixed ceiling (unlike the 0-1 rate metrics) --
        # scale the colorbar to whatever this scope's zones actually reach.
        vals = [s["value"] for s in zone_stats.values() if s["value"] is not None]
        cfg["cmax"] = max(vals) * 1.15 if vals else 1.0

    fig = go.Figure()
    _add_court_shapes(fig)
    any_low = False
    for zone, (x0, x1) in ZONE_X.items():
        stats = zone_stats[zone]
        # A zone with few attacks (e.g. a rotation barely used this scope)
        # fades toward the empty-cell gray instead of filling as solidly
        # as a zone backed by hundreds -- same reliability signal as the
        # rest of the app, applied on top of the usual 0.75 base alpha.
        zone_alpha = 0.75 * dl.reliability_alpha(stats["tot"], floor=0.3)
        low = dl.is_low_sample(stats["tot"])
        any_low = any_low or (low and stats["tot"] > 0)
        fig.add_shape(
            type="rect", x0=x0, y0=6, x1=x1, y1=9,
            fillcolor=_zone_color(stats["value"], cfg, alpha=zone_alpha), line=dict(color="rgba(255,255,255,0.5)", width=1),
        )
        if stats["value"] is None:
            val_txt = "—"
        elif cfg["is_pct"]:
            val_txt = f"{stats['value'] * 100:.0f}%"
        else:
            val_txt = f"{stats['value']:.0f}"
        attacks_txt = f"{stats['tot']} attacks" + (" (low sample)" if low and stats["tot"] > 0 else "")
        fig.add_annotation(
            x=(x0 + x1) / 2, y=7.5, showarrow=False, font=dict(color=_zone_text_color(stats["value"], cfg), size=17),
            text=f"<b>{zone}</b><br>{cfg['label']} {val_txt}<br>{attacks_txt}",
        )

    # Dummy invisible trace, only to host a real gradient colorbar (the
    # zones themselves are plain shapes, which have no colorbar of their
    # own) -- horizontal, below the court, out of the way of the narrower
    # column this chart now renders in.
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(
            colorscale=cfg["colorscale"], cmin=cfg["cmin"], cmax=cfg["cmax"], showscale=True, color=[0], size=0.1,
            colorbar=dict(
                title=dict(text=cfg["label"], side="top"), orientation="h",
                tickformat=".0%" if cfg["is_pct"] else None,
                thickness=15, len=0.9, x=0.5, xanchor="center", y=-0.1, yanchor="top",
            ),
        ),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_xaxes(visible=False, range=[-0.3, 9.3])
    fig.update_yaxes(visible=False, range=[-0.3, 9.3], scaleanchor="x")
    fig.update_layout(height=680, margin=dict(l=10, r=10, t=10, b=70), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    if any_low:
        st.caption(f"A paler zone had fewer than {dl.MIN_RELIABLE_N} attacks in this scope — read its color with caution.")

    return zone_stats


def _render_zone_efficiency_tables(zone_stats: dict):
    """The P4/P3/P2 detail tables for the efficiency court above, stacked
    vertically (rather than 3-abreast) so they fit their own column next to
    the court, fully readable without scrolling."""
    for zone in ["P4", "P3", "P2"]:
        with st.container(border=True):
            st.markdown(f"**{zone}** · {' / '.join(ZONE_ROLES[zone])}")
            top = zone_stats[zone]["players"][["player_name", "Tot", "E_pct", "Err_pct", "Slash_pct", "Neg_pct", "Neutral_pct", "Pos_pct", "Perfect_pct"]].head(5)
            if top.empty:
                st.caption("No attacks in this scope.")
            else:
                st.dataframe(
                    top.rename(columns=ZONE_TABLE_RENAME),
                    hide_index=True, width="stretch",
                    column_config={c: st.column_config.NumberColumn(format="percent") for c in ZONE_TABLE_PERCENT_COLS},
                )


def _render_zone_settype_court(attack_by_type: pd.DataFrame) -> dict:
    """Chart 5: same court, but each zone is split into proportional
    stripes by set type (same colors as the rest of the app's set-type
    charts) instead of a single efficiency color. Returns zone_mix -- the
    per-zone tables render separately (see _render_zone_settype_tables), in
    the column next to this one."""
    zone_mix = {}
    for zone, roles_in_zone in ZONE_ROLES.items():
        sub = attack_by_type[attack_by_type["Role"].isin(roles_in_zone) & (attack_by_type["Tot"] > 0)]
        mix = sub.groupby("palla", observed=True)["Tot"].sum()
        total = mix.sum()
        shares = (mix / total).to_dict() if total > 0 else {}
        zone_mix[zone] = {"shares": shares, "tot": int(total)}

    fig = go.Figure()
    _add_court_shapes(fig)
    for zone, (x0, x1) in ZONE_X.items():
        shares = zone_mix[zone]["shares"]
        if not shares:
            fig.add_shape(type="rect", x0=x0, y0=6, x1=x1, y1=9, fillcolor="rgba(255,255,255,0.08)", line=dict(color="rgba(255,255,255,0.5)", width=1))
        else:
            cursor = x0
            width = x1 - x0
            for palla in RAW_PALLA_ORDER[1:]:  # skip "Totale"
                share = shares.get(palla, 0)
                if share <= 0:
                    continue
                seg_w = width * share
                fig.add_shape(
                    type="rect", x0=cursor, y0=6, x1=cursor + seg_w, y1=9,
                    fillcolor=PALLA_COLORS.get(palla, "#888888"), opacity=0.85, line=dict(width=0),
                )
                cursor += seg_w
            fig.add_shape(type="rect", x0=x0, y0=6, x1=x1, y1=9, fillcolor="rgba(0,0,0,0)", line=dict(color="rgba(255,255,255,0.5)", width=1))
        fig.add_annotation(
            x=(x0 + x1) / 2, y=7.5, showarrow=False, font=dict(color="#ffffff", size=16),
            text=f"<b>{zone}</b><br>{zone_mix[zone]['tot']} attacks",
        )

    fig.update_xaxes(visible=False, range=[-0.3, 9.3])
    fig.update_yaxes(visible=False, range=[-0.3, 9.3], scaleanchor="x")
    fig.update_layout(height=680, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

    legend_html = "&nbsp;&nbsp;".join(
        f'<span style="display:inline-block;width:10px;height:10px;background:{PALLA_COLORS[p]};'
        f'border-radius:2px;margin-right:4px;"></span>'
        f'<span style="color:{PALLA_COLORS[p]};">{dl.PALLA_LABELS[p]}</span>'
        for p in RAW_PALLA_ORDER[1:]
    )
    st.markdown(legend_html, unsafe_allow_html=True)
    return zone_mix


def _render_zone_settype_tables(zone_mix: dict):
    """The P4/P3/P2 detail tables for the set-type court above, stacked
    vertically (rather than 3-abreast) so they fit their own column next to
    the court, fully readable without scrolling."""
    for zone in ["P4", "P3", "P2"]:
        with st.container(border=True):
            st.markdown(f"**{zone}** · {' / '.join(ZONE_ROLES[zone])}")
            shares = zone_mix[zone]["shares"]
            if not shares:
                st.caption("No attacks in this scope.")
            else:
                tbl = pd.DataFrame({
                    "Set type": [dl.PALLA_LABELS[p] for p in shares.keys()],
                    "Share": list(shares.values()),
                }).sort_values("Share", ascending=False)
                st.dataframe(
                    tbl, hide_index=True, width="stretch",
                    column_config={"Share": st.column_config.NumberColumn(format="percent")},
                )


def _render_zone_distribution(scoped: pd.DataFrame):
    """Charts 4 & 5 (merged behind a toggle): where the setters' sets end
    up (P4/P3/P2), either colored by efficiency or by set-type mix. Orro
    and Prandi -- the setters -- aren't attackers assigned to a zone here;
    their own setting numbers get a table beside the court instead."""
    names = dl.load_player_names()
    roles = dl.load_player_roles()
    name_to_role = {names[code]: dl.ROLE_LABELS.get(r, r) for code, r in roles.items() if code in names}

    attack = scoped[(scoped["fondamentale"] == "Attacco") & (~scoped["is_team"])].copy()
    attack["Role"] = attack["player_name"].map(name_to_role)

    setters_alzata = scoped[
        (scoped["fondamentale"] == "Alzata") & (scoped["palla"] == "Totale")
        & (scoped["player_name"].isin(SETTER_SURNAMES)) & (scoped["Tot"] > 0)
    ]

    # Court column narrower than before (was [2, 1]) -- the court itself
    # renders taller to compensate, and the P4/P3/P2 tables move into the
    # other column, stacked above the setters' table, so the whole thing
    # reads top-to-bottom without needing to scroll sideways or down past
    # the court to find them.
    col_court, col_table = st.columns([1, 1])
    with col_court:
        with st.container(border=True):
            st.markdown("**Setting distribution**")
            mode = st.segmented_control(
                "View", ["Efficiency by zone", "Set type by zone"], default="Efficiency by zone",
                required=True, key="zone_mode",
            )
            metric_col = "E_pct"
            # Only "Efficiency by zone" needs a metric to color the court by
            # -- "Set type by zone" is always the set-type mix, shown via its
            # own legend instead (see _render_zone_settype_court).
            if mode == "Efficiency by zone":
                metric_label = st.segmented_control(
                    "Effectiveness metric", list(ZONE_METRIC_OPTIONS.keys()),
                    default="E%", required=True, key="zone_metrica",
                )
                metric_col = ZONE_METRIC_OPTIONS[metric_label]
            if mode == "Efficiency by zone":
                zone_stats = _render_zone_efficiency_court(attack[attack["palla"] == "Totale"], metric_col)
            else:
                zone_mix = _render_zone_settype_court(attack[attack["palla"] != "Totale"])
    with col_table:
        if mode == "Efficiency by zone":
            _render_zone_efficiency_tables(zone_stats)
        else:
            _render_zone_settype_tables(zone_mix)

        with st.container(border=True):
            st.markdown("**Setter**")
            if setters_alzata.empty:
                st.caption("No setting data in this scope.")
            else:
                tbl = setters_alzata[["player_name", "Tot", "E_pct", "Err_pct", "Slash_pct", "Neg_pct", "Neutral_pct", "Pos_pct", "Perfect_pct"]].rename(
                    columns={**ZONE_TABLE_RENAME, "Tot": "Sets"}
                )
                st.dataframe(
                    tbl, hide_index=True, width="stretch",
                    column_config={c: st.column_config.NumberColumn(format="percent") for c in ZONE_TABLE_PERCENT_COLS},
                )


def _render_distribution(scoped: pd.DataFrame, scout: pd.DataFrame, palla_tipi_en: list[str]):
    st.caption(
        "For each player: how many times she attacks on each set type and with what effectiveness. "
        "Reflects the game distribution set by the setter."
    )

    fond_sel2 = st.selectbox(
        "Fundamental", dl.FONDAMENTALI_CON_PALLA,
        format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f),
        key="dist_fond",
    )
    fond2_label = dl.FONDAMENTALE_LABELS.get(fond_sel2, fond_sel2)
    _render_how_to_expander(fond_sel2, fond2_label)

    dist = scoped[
        (scoped["fondamentale"] == fond_sel2)
        & (~scoped["is_team"])
        & (scoped["palla"] != "Totale")
        & (scoped["Tot"] > 0)
    ].copy()
    dist["palla_en"] = dist["palla"].map(dl.PALLA_LABELS)

    if dist.empty:
        st.info("No data available for this fundamental in the selected scope.")
        return

    # Role-grouped order (Setters, Opposites, Outside Hitters, Middle
    # Blockers, Liberos -- players_grid.ALL_PLAYERS' own order) instead of
    # sorting by volume, so the same player always lands in the same row/
    # column regardless of who had the most touches this time.
    role_order = [p["surname"] for p in pg.ALL_PLAYERS]
    present = set(dist["player_name"])
    ordine_giocatrici = [s for s in role_order if s in present]

    # Order requested: Setting distribution first, then the Heatmap, then
    # the Game map / Cumulative actions pair below both.
    _render_zone_distribution(scoped)

    with st.container(border=True):
        st.markdown("**Heatmap** · Volume and effectiveness per player and set type")
        metrica_label = st.segmented_control(
            "Effectiveness metric", list(TEAM_PROFILE_METRICS.keys()),
            default="E%", required=True, key="dist_metrica",
        )
        metrica_col, _, metrica_is_pct = TEAM_PROFILE_METRICS[metrica_label]
        # "#"/"=" have a different name per fundamental (Point for attack, Block point for block).
        if metrica_col == "Perfect_pct":
            metrica_display = f"% {dl.perfetto_label(fond_sel2)} (#)"
        elif metrica_col == "Err_pct":
            metrica_display = f"% {dl.errore_label(fond_sel2)} (=)"
        elif metrica_col == "Ind":
            metrica_display = "Index"
        else:
            metrica_display = "Efficiency (E%)"

        pivot_tot = dist.pivot_table(index="player_name", columns="palla_en", values="Tot", aggfunc="sum", observed=True)
        pivot_metrica = dist.pivot_table(index="player_name", columns="palla_en", values=metrica_col, aggfunc="mean", observed=True)
        colonne_ordinate = [p for p in palla_tipi_en if p in pivot_metrica.columns]
        pivot_tot = pivot_tot.reindex(index=ordine_giocatrici, columns=colonne_ordinate)
        pivot_metrica = pivot_metrica.reindex(index=ordine_giocatrici, columns=colonne_ordinate)

        if metrica_col == "E_pct":
            # Efficiency can be negative: diverging scale centered on 0.
            heat_kwargs = dict(colorscale="RdBu", zmid=0, zmin=-0.5, zmax=0.5)
        elif metrica_col == "Ind":
            # Ind has no natural fixed ceiling (unlike the 0-1 rate metrics) --
            # scale to whatever this scope's cells actually reach.
            ind_max = pivot_metrica.max(numeric_only=True).max()
            ind_max = float(ind_max) if pd.notna(ind_max) and ind_max > 0 else 1.0
            heat_kwargs = dict(colorscale="Blues", zmin=0, zmax=ind_max)
        elif metrica_col == "Err_pct":
            # Higher error % is worse -- a "bad = more red" sequential scale,
            # as opposed to Perfect_pct's "good = more green" below.
            heat_kwargs = dict(colorscale="Reds", zmin=0, zmax=1)
        else:
            # % Point (#) is always >= 0: single-hue sequential scale.
            heat_kwargs = dict(colorscale="Blues", zmin=0, zmax=1)

        # Cell text: black on the paler part of whichever scale is active (E%
        # near 0, or the other metrics near their low end) so it stays legible
        # against a background color that can range from near-white to fully
        # saturated; white everywhere else.
        def _heat_text_color(value) -> str:
            if pd.isna(value):
                return "#ffffff"
            if metrica_col == "E_pct":
                return "#000000" if -0.2 <= value <= 0.2 else "#ffffff"
            if metrica_col == "Ind":
                return "#000000" if 0 <= value <= heat_kwargs["zmax"] / 2 else "#ffffff"
            return "#000000" if 0 <= value <= 0.5 else "#ffffff"

        # go.Heatmap's own texttemplate/textfont only take a single scalar
        # color for the whole trace -- per-cell colors aren't supported there,
        # so the cell text is drawn as individual annotations instead (same
        # technique already used for the court charts below), one per cell,
        # each with its own black/white color.
        annotations = []
        any_low = False
        for r in pivot_tot.index:
            for c in pivot_tot.columns:
                tot_v = pivot_tot.loc[r, c]
                eff_v = pivot_metrica.loc[r, c]
                if pd.isna(tot_v):
                    continue
                # A "*" after the count flags cells too thin to trust the
                # metric on -- the heatmap already prints the count, but a
                # bare number doesn't say by itself that it's too few to
                # read the color/percentage next to it with confidence.
                low = dl.is_low_sample(tot_v)
                any_low = any_low or low
                count_txt = f"{int(tot_v)}*" if low else f"{int(tot_v)}"
                text = f"{count_txt}<br>—" if pd.isna(eff_v) else (
                    f"{count_txt}<br>{eff_v * 100:.0f}%" if metrica_is_pct else f"{count_txt}<br>{eff_v:.0f}"
                )
                annotations.append(dict(
                    x=c, y=r, text=text, showarrow=False,
                    font=dict(color=_heat_text_color(eff_v), size=11),
                ))

        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot_metrica.values,
            x=pivot_metrica.columns.tolist(),
            y=pivot_metrica.index.tolist(),
            colorbar=dict(title=metrica_display, tickformat=".0%" if metrica_is_pct else None),
            hovertemplate="%{y} · %{x}<br>" + metrica_display + (": %{z:.0%}" if metrica_is_pct else ": %{z:.1f}") + "<extra></extra>",
            **heat_kwargs,
        ))
        fig_heat.update_layout(
            xaxis_title="Set type", yaxis_title="",
            # Explicit array (not the old yaxis_autorange="reversed", which was
            # tuned for the previous volume-sort order and silently flips the
            # new fixed role order upside down): puts ordine_giocatrici[0]
            # (Orro) at the top, reading top-to-bottom like the role list.
            yaxis=dict(categoryorder="array", categoryarray=ordine_giocatrici[::-1]),
            height=max(420, 50 * len(pivot_metrica.index)),
            annotations=annotations,
        )
        st.plotly_chart(fig_heat, width="stretch")
    caption = f"In each cell: total number of actions and {metrica_display.lower()}. Rows ordered by role."
    if any_low:
        caption += f" * = fewer than {dl.MIN_RELIABLE_N} actions, read with caution."
    st.caption(caption)

    col_map, col_cum = st.columns(2)
    with col_map:
        with st.container(border=True):
            st.markdown("**Game map** — volume of actions per set type")
            fig1 = px.bar(
                dist, x="player_name", y="Tot", color="palla_en",
                category_orders={"player_name": ordine_giocatrici, "palla_en": palla_tipi_en},
                color_discrete_map=PALLA_COLORS_EN,
                labels={"player_name": "", "Tot": "Number of actions", "palla_en": "Set type"},
                barmode="stack",
            )
            fig1.update_layout(legend_title_text="Set type", height=520)
            st.plotly_chart(fig1, width="stretch")

    with col_cum:
        with st.container(border=True):
            st.markdown("**Cumulative actions** over time")
            _render_cumulative_actions(scout, fond_sel2, height=520)


def _resolve_raw_match() -> str:
    """No separate picker here -- follows the sidebar's own period/season
    filter instead: the season-aggregate sheet when the period spans the
    whole season, otherwise the most recent match within the selected
    period (matches_in_scope() is already sorted most-recent-first)."""
    if filters.is_full_season():
        return dl.SEASON_LABEL
    matches = filters.matches_in_scope()
    return matches[0]["date"] if matches else dl.SEASON_LABEL


def _render_raw_sheet(scout: pd.DataFrame):
    st.caption(
        "Complete scouting sheet for one match, same rows/columns as the Data Volley export "
        "(P / Set / Ind / E% / Tot, then one box per fundamental with = / / / - / ! / + / # and "
        "their % / BP / pC) — player surnames instead of codes. Follows the sidebar's period: "
        "the season aggregate when it spans the whole season, otherwise the most recent match in range."
    )
    fond_sel = st.selectbox(
        "Fundamental", dl.FONDAMENTALE_ORDER,
        format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f), key="raw_fond",
    )
    _render_how_to_expander(fond_sel, dl.FONDAMENTALE_LABELS.get(fond_sel, fond_sel))

    partita_sel3 = _resolve_raw_match()
    match_label = partita_sel3 if partita_sel3 == dl.SEASON_LABEL else mc.match_label(partita_sel3)
    st.markdown(f"**Showing:** {match_label}")

    raw = scout[(scout["match"] == partita_sel3) & (scout["fondamentale"] == fond_sel)].copy()
    if raw.empty:
        st.info("No data available for this match.")
        return

    raw["palla"] = pd.Categorical(raw["palla"].astype(str), categories=RAW_PALLA_ORDER, ordered=True)
    raw["_team_rank"] = (~raw["is_team"]).astype(int)  # Team row before player rows, per block
    raw["Set type"] = raw["palla"].map(dl.PALLA_LABELS)
    raw["Player"] = raw["player_name"]

    block = raw.sort_values(["palla", "_team_rank"], kind="stable").reset_index(drop=True)
    with st.container(border=True):
        st.markdown(f"**{dl.FONDAMENTALE_LABELS[fond_sel]}**")
        table = pd.DataFrame({"Set type": block["Set type"], "Player": block["Player"]})
        column_config = {}
        for gi, group in enumerate(RAW_COLUMN_GROUPS):
            if gi > 0:
                spacer = " " * gi
                table[spacer] = ""
                column_config[spacer] = st.column_config.Column(label="", width="small", disabled=True)
            for col in group:
                label = RAW_COLUMN_RENAME[col]
                table[label] = block[col]
                if label in RAW_PERCENT_COLUMNS:
                    column_config[label] = st.column_config.NumberColumn(label, format="percent")
                else:
                    column_config[label] = st.column_config.NumberColumn(label, format="%d")

        # Each row's text colored by the athlete's assigned color (same
        # hue as every other chart in the app); the team row instead
        # gets black text on a white background so it stands out as
        # "not a player".
        row_styles = [
            "color:#000000;background-color:#ffffff;" if is_team else f"color:{pc.color_for(player)};"
            for is_team, player in zip(block["is_team"], block["Player"])
        ]
        styled = table.style.apply(lambda row: [row_styles[row.name]] * len(row), axis=1)
        st.dataframe(styled, hide_index=True, width="stretch", column_config=column_config)


def render():
    scout = dl.load_scout_data()
    scoped = _scope_scout(scout)
    palla_tipi_en = [dl.PALLA_LABELS[p] for p in dl.PALLA_ORDER if p != "Totale"]

    # A plain st.tabs would leave whichever section isn't shown mounted but
    # hidden (display:none); Streamlit's data-grid widget never recovers a
    # correct width once un-hidden that way (a real, reproducible Streamlit/
    # glide-data-grid limitation, not just a one-off glitch). Using a
    # segmented control with only the active section's code actually running
    # means the grid is created already-visible every time, sidestepping it.
    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="scout_section")

    if section == "Team Profile":
        _render_team_profile_section(scoped, scout)
    elif section == "General stats":
        _render_general_stats(scoped)
    elif section == "Game distribution":
        _render_distribution(scoped, scout, palla_tipi_en)
    else:
        _render_raw_sheet(scout)
