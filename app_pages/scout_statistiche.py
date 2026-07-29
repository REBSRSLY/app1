import pandas as pd
import plotly.colors as pcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import match_calendar as mc
import player_colors as pc

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
# data_loader.SCOUT_COLS / _parse_scout_sheet), used only by the "Excel
# Scout Sheet" section to reproduce the sheet's column order exactly. Row
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

SECTIONS = ["General stats", "Game distribution", "Court zones", "Excel Scout Sheet"]

# Which front-row zone each role attacks from -- we don't have real
# per-attack court coordinates, so this fixed assumption (given by the
# coaching staff) stands in for it.
ZONE_ROLES = {
    "P4": ["Outside Hitter"],
    "P3": ["Middle Blocker"],
    "P2": ["Setter", "Opposite"],
}


def _scope_scout(scout: pd.DataFrame) -> pd.DataFrame:
    """Collapse every match currently in the sidebar's scope into one
    virtual sheet per (fondamentale, palla, player): action counts sum,
    rate columns (E%, Ind, outcome %s) become Tot-weighted averages across
    the scoped matches. Falls back to the season-total sheet if nothing
    is in scope."""
    in_scope = {m["date"] for m in filters.matches_in_scope()}
    d = scout[scout["match"].isin(in_scope)]
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


def _render_team_profile(scoped: pd.DataFrame):
    """Team efficiency across every fundamental at once -- the "shape" of
    the team's game (strong serve, shaky reception, etc.) that the
    per-fundamental breakdown below can't show on its own."""
    team = scoped[scoped["is_team"] & (scoped["palla"] == "Totale") & (scoped["Tot"] > 0)].copy()
    if team.empty:
        return

    present = [f for f in dl.FONDAMENTALE_ORDER if f in set(team["fondamentale"])]
    order_labels = [dl.FONDAMENTALE_LABELS[f] for f in present]
    team["Fundamental"] = team["fondamentale"].map(dl.FONDAMENTALE_LABELS)

    fig = px.bar(
        team, x="E_pct", y="Fundamental", orientation="h",
        category_orders={"Fundamental": order_labels},
        color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
        labels={"E_pct": "Team efficiency E%", "Fundamental": ""},
    )
    fig.update_layout(
        coloraxis_showscale=False, xaxis_tickformat=".0%", height=260,
        yaxis=dict(categoryorder="array", categoryarray=order_labels[::-1]),
        margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Team efficiency (E%) for every fundamental in the selected scope -- where the team is strong vs. shaky.")


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
                "share": count / r["Tot"], "rank": rank,
            })
    d = pd.DataFrame(rows)
    if d.empty:
        return

    order_labels = d.sort_values("rank")["Outcome"].drop_duplicates().tolist()
    color_map = {f"{nome} ({simbolo})": OUTCOME_COLORS.get(simbolo, "#888888") for simbolo, nome, _ in legenda}

    fig = px.bar(
        d, x="share", y="player_name", color="Outcome", orientation="h",
        category_orders={"player_name": player_order[::-1], "Outcome": order_labels},
        color_discrete_map=color_map,
        labels={"share": "Share of actions", "player_name": ""},
    )
    fig.update_layout(
        barmode="stack", xaxis_tickformat=".0%", legend_title_text="Outcome",
        height=max(220, 34 * len(player_order)), margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")


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
    legenda = dl.legenda_fondamentale(fond_sel)
    if legenda:
        with st.expander(f"How to read \"{fond_label}\"", icon=":material/menu_book:"):
            for simbolo, nome, descrizione in legenda:
                st.markdown(f"**{simbolo}** · {nome} — {descrizione}")

    with st.container(border=True):
        st.markdown("**Team profile** · efficiency across every fundamental")
        _render_team_profile(scoped)

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
                color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
            )
            fig_effp.update_layout(coloraxis_showscale=False, xaxis_tickformat=".0%")
            st.plotly_chart(fig_effp, width="stretch")

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
        tabella = players[["player_name", "Tot", "E_pct", "Perfect_pct", "Err_pct"]].rename(columns={
            "player_name": "Player",
            "E_pct": "Efficiency E%",
            "Perfect_pct": col_perfetto,
            "Err_pct": col_errore,
        })
        st.dataframe(
            tabella,
            hide_index=True,
            width="stretch",
            column_config={
                "Tot": st.column_config.NumberColumn(format="%d"),
                "Efficiency E%": st.column_config.NumberColumn(format="percent"),
                col_perfetto: st.column_config.NumberColumn(format="percent"),
                col_errore: st.column_config.NumberColumn(format="percent"),
            },
        )


def _render_distribution(scoped: pd.DataFrame, palla_tipi_en: list[str]):
    st.caption(
        "For each player: how many times she attacks on each set type and with what effectiveness. "
        "Reflects the game distribution set by the setter."
    )

    col_fond, col_metrica = st.columns(2)
    with col_fond:
        fond_sel2 = st.selectbox(
            "Fundamental", dl.FONDAMENTALI_CON_PALLA,
            format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f),
            key="dist_fond",
        )
    with col_metrica:
        metrica_label = st.segmented_control(
            "Effectiveness metric",
            ["Efficiency (E%)", "% Point (#)"],
            default="Efficiency (E%)",
            required=True,
            key="dist_metrica",
        )
    metrica_col = "E_pct" if metrica_label == "Efficiency (E%)" else "Perfect_pct"
    fond2_label = dl.FONDAMENTALE_LABELS.get(fond_sel2, fond_sel2)
    # The "#" symbol has a different name per fundamental (Point for attack, Block point for block).
    metrica_display = "Efficiency (E%)" if metrica_col == "E_pct" else f"% {dl.perfetto_label(fond_sel2)} (#)"
    st.caption(f"For **{fond2_label}**: \"#\" = {dl.perfetto_label(fond_sel2)}, \"=\" = {dl.errore_label(fond_sel2)}.")

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

    ordine_giocatrici = (
        dist.groupby("player_name")["Tot"].sum().sort_values(ascending=False).index.tolist()
    )

    st.markdown("#### Chart 1 · Game map — volume of actions per set type")
    fig1 = px.bar(
        dist, x="player_name", y="Tot", color="palla_en",
        category_orders={"player_name": ordine_giocatrici, "palla_en": palla_tipi_en},
        color_discrete_map=PALLA_COLORS_EN,
        labels={"player_name": "", "Tot": "Number of actions", "palla_en": "Set type"},
        barmode="stack",
    )
    fig1.update_layout(legend_title_text="Set type")
    st.plotly_chart(fig1, width="stretch")

    st.markdown("#### Chart 2 · Effectiveness per set type")
    default_players = ordine_giocatrici[: min(5, len(ordine_giocatrici))]
    giocatrici_sel = st.multiselect(
        "Players to compare", ordine_giocatrici, default=default_players, key="dist_giocatrici"
    )
    dist_line = dist[dist["player_name"].isin(giocatrici_sel)]
    if giocatrici_sel and not dist_line.empty:
        fig2 = px.line(
            dist_line.sort_values("palla"), x="palla_en", y=metrica_col, color="player_name",
            category_orders={"palla_en": palla_tipi_en},
            markers=True,
            labels={"palla_en": "Set type", metrica_col: metrica_display, "player_name": "Player"},
        )
        fig2.update_layout(yaxis_tickformat=".0%", legend_title_text="Player")
        st.plotly_chart(fig2, width="stretch")
    else:
        st.info("Select at least one player to compare.")

    st.markdown("#### Heatmap · Volume and effectiveness per player and set type")
    pivot_tot = dist.pivot_table(index="player_name", columns="palla_en", values="Tot", aggfunc="sum", observed=True)
    pivot_metrica = dist.pivot_table(index="player_name", columns="palla_en", values=metrica_col, aggfunc="mean", observed=True)
    colonne_ordinate = [p for p in palla_tipi_en if p in pivot_metrica.columns]
    pivot_tot = pivot_tot.reindex(index=ordine_giocatrici, columns=colonne_ordinate)
    pivot_metrica = pivot_metrica.reindex(index=ordine_giocatrici, columns=colonne_ordinate)

    testo = pivot_tot.copy().astype(object)
    for r in pivot_tot.index:
        for c in pivot_tot.columns:
            tot_v = pivot_tot.loc[r, c]
            eff_v = pivot_metrica.loc[r, c]
            if pd.isna(tot_v):
                testo.loc[r, c] = ""
            elif pd.isna(eff_v):
                testo.loc[r, c] = f"{int(tot_v)}<br>—"
            else:
                testo.loc[r, c] = f"{int(tot_v)}<br>{eff_v * 100:.0f}%"

    if metrica_col == "E_pct":
        # Efficiency can be negative: diverging scale centered on 0.
        heat_kwargs = dict(colorscale="RdBu", zmid=0, zmin=-0.5, zmax=0.5)
    else:
        # % Point (#) is always >= 0: single-hue sequential scale.
        heat_kwargs = dict(colorscale="Blues", zmin=0, zmax=1)

    fig_heat = go.Figure(data=go.Heatmap(
        z=pivot_metrica.values,
        x=pivot_metrica.columns.tolist(),
        y=pivot_metrica.index.tolist(),
        text=testo.values,
        texttemplate="%{text}",
        colorbar=dict(title=metrica_display, tickformat=".0%"),
        hovertemplate="%{y} · %{x}<br>" + metrica_display + ": %{z:.0%}<extra></extra>",
        **heat_kwargs,
    ))
    fig_heat.update_layout(
        xaxis_title="Set type", yaxis_title="", yaxis_autorange="reversed",
        height=max(320, 40 * len(pivot_metrica.index)),
    )
    st.plotly_chart(fig_heat, width="stretch")
    st.caption(f"In each cell: total number of actions and {metrica_display.lower()}.")


def _zone_color(e_pct) -> str:
    if e_pct is None or pd.isna(e_pct):
        return "rgba(255,255,255,0.08)"
    t = max(0.0, min(1.0, (e_pct - (-0.2)) / (0.6 - (-0.2))))
    rgb = pcolors.sample_colorscale("RdYlGn", [t])[0]
    return rgb.replace("rgb", "rgba").replace(")", ",0.75)")


def _render_court_zones(scoped: pd.DataFrame):
    st.caption(
        "We don't have each attack's real court coordinates, so this assumes the usual front-row "
        "assignment: Setter/Opposite attack from P2, Middle Blockers from P3, Outside Hitters from P4."
    )

    names = dl.load_player_names()
    roles = dl.load_player_roles()
    name_to_role = {names[code]: dl.ROLE_LABELS.get(r, r) for code, r in roles.items() if code in names}

    attack = scoped[
        (scoped["fondamentale"] == "Attacco") & (scoped["palla"] == "Totale") & (~scoped["is_team"])
    ].copy()
    attack["Role"] = attack["player_name"].map(name_to_role)

    zone_stats = {}
    for zone, roles_in_zone in ZONE_ROLES.items():
        sub = attack[attack["Role"].isin(roles_in_zone) & (attack["Tot"] > 0)]
        tot = sub["Tot"].sum()
        e_pct = (sub["E_pct"] * sub["Tot"]).sum() / tot if tot > 0 else None
        zone_stats[zone] = {"tot": int(tot), "e_pct": e_pct, "players": sub.sort_values("Tot", ascending=False)}

    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=9, line=dict(color="rgba(255,255,255,0.5)", width=2))
    fig.add_shape(type="line", x0=0, y0=9, x1=9, y1=9, line=dict(color="#ffffff", width=5))
    fig.add_annotation(x=4.5, y=9.35, text="NET", showarrow=False, font=dict(color="rgba(255,255,255,0.6)", size=11))
    fig.add_shape(type="line", x0=0, y0=6, x1=9, y1=6, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dash"))
    for x in (3, 6):
        fig.add_shape(type="line", x0=x, y0=0, x1=x, y1=9, line=dict(color="rgba(255,255,255,0.25)", width=1))

    back_zone_labels = {"P5": (1.5, 3), "P6": (4.5, 3), "P1": (7.5, 3)}
    for label, (x, y) in back_zone_labels.items():
        fig.add_annotation(x=x, y=y, text=f"<span style='opacity:0.35'>{label}</span>", showarrow=False, font=dict(color="#ffffff", size=13))

    zone_x = {"P4": (0, 3), "P3": (3, 6), "P2": (6, 9)}
    for zone, (x0, x1) in zone_x.items():
        stats = zone_stats[zone]
        fig.add_shape(
            type="rect", x0=x0, y0=6, x1=x1, y1=9,
            fillcolor=_zone_color(stats["e_pct"]), line=dict(color="rgba(255,255,255,0.5)", width=1),
        )
        roles_txt = " / ".join(ZONE_ROLES[zone])
        e_txt = f"{stats['e_pct'] * 100:.0f}%" if stats["e_pct"] is not None else "—"
        fig.add_annotation(
            x=(x0 + x1) / 2, y=7.5, showarrow=False, font=dict(color="#ffffff", size=13),
            text=f"<b>{zone}</b> · {roles_txt}<br>E% {e_txt}<br>{stats['tot']} attacks",
        )

    fig.update_xaxes(visible=False, range=[-0.3, 9.3])
    fig.update_yaxes(visible=False, range=[-0.3, 9.3], scaleanchor="x")
    fig.update_layout(
        height=440, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch")

    cols = st.columns(3)
    for col, zone in zip(cols, ["P4", "P3", "P2"]):
        with col:
            with st.container(border=True):
                st.markdown(f"**{zone}** · {' / '.join(ZONE_ROLES[zone])}")
                top = zone_stats[zone]["players"][["player_name", "Tot", "E_pct"]].head(5)
                if top.empty:
                    st.caption("No attacks in this scope.")
                else:
                    st.dataframe(
                        top.rename(columns={"player_name": "Player", "Tot": "Attacks", "E_pct": "E%"}),
                        hide_index=True, width="stretch",
                        column_config={"E%": st.column_config.NumberColumn(format="percent")},
                    )


def _render_raw_sheet(scout: pd.DataFrame, partita_options: list[str], format_partita_option):
    st.caption(
        "Complete scouting sheet for one match, same rows/columns as the Data Volley export "
        "(P / Set / Ind / E% / Tot, then one box per fundamental with = / / / - / ! / + / # and "
        "their % / BP / pC) — player surnames instead of codes."
    )
    filters.ensure_valid_selection("raw_partita", partita_options)
    partita_sel3 = st.selectbox("Match", partita_options, key="raw_partita", format_func=format_partita_option)

    raw = scout[scout["match"] == partita_sel3].copy()
    if raw.empty:
        st.info("No data available for this match.")
        return

    raw["palla"] = pd.Categorical(raw["palla"].astype(str), categories=RAW_PALLA_ORDER, ordered=True)
    raw["_team_rank"] = (~raw["is_team"]).astype(int)  # Team row before player rows, per block
    raw["Set type"] = raw["palla"].map(dl.PALLA_LABELS)
    raw["Player"] = raw["player_name"]

    for fond in dl.FONDAMENTALE_ORDER:
        block = raw[raw["fondamentale"] == fond].sort_values(["palla", "_team_rank"], kind="stable")
        if block.empty:
            continue
        with st.container(border=True):
            st.markdown(f"**{dl.FONDAMENTALE_LABELS[fond]}**")
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
            st.dataframe(table, hide_index=True, width="stretch", column_config=column_config)


def render():
    scout = dl.load_scout_data()
    scoped = _scope_scout(scout)
    partita_options = filters.match_options()
    palla_tipi_en = [dl.PALLA_LABELS[p] for p in dl.PALLA_ORDER if p != "Totale"]

    def format_partita_option(opt: str) -> str:
        return opt if opt == dl.SEASON_LABEL else mc.match_label(opt)

    # A plain st.tabs would leave whichever section isn't shown mounted but
    # hidden (display:none); Streamlit's data-grid widget never recovers a
    # correct width once un-hidden that way (a real, reproducible Streamlit/
    # glide-data-grid limitation, not just a one-off glitch). Using a
    # segmented control with only the active section's code actually running
    # means the grid is created already-visible every time, sidestepping it.
    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="scout_section")

    if section == "General stats":
        _render_general_stats(scoped)
    elif section == "Game distribution":
        _render_distribution(scoped, palla_tipi_en)
    elif section == "Court zones":
        _render_court_zones(scoped)
    else:
        _render_raw_sheet(scout, partita_options, format_partita_option)
