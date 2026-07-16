import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from ui_helpers import section_header

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


def render():
    section_header("Scout & Stats", "Per-fundamental scouting statistics and attack game distribution, for a single match or the whole season.")

    scout = dl.load_scout_data()
    matches = dl.load_match_list()
    partita_options = [dl.SEASON_LABEL] + matches
    palla_tipi = [p for p in dl.PALLA_ORDER if p != "Totale"]
    palla_tipi_en = [dl.PALLA_LABELS[p] for p in palla_tipi]

    tab_generale, tab_distribuzione = st.tabs(["General stats", "Game distribution"])

    # ------------------------------------------------------------------
    # TAB 1 — General stats per fundamental
    # ------------------------------------------------------------------
    with tab_generale:
        col_partita, col_fond = st.columns(2)
        with col_partita:
            partita_sel = st.selectbox("Match", partita_options, key="gen_partita")
        with col_fond:
            fondamentali = sorted(scout["fondamentale"].unique())
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

        base = scout[(scout["match"] == partita_sel) & (scout["fondamentale"] == fond_sel) & (scout["palla"] == "Totale")]
        team_row = base[base["is_team"]]
        players = base[~base["is_team"]].sort_values("Tot", ascending=False)

        if team_row.empty or players.empty:
            st.info("No data available for this match/fundamental combination.")
        else:
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
                        color_discrete_sequence=["#4C78A8"],
                    )
                    fig_vol.update_layout(yaxis={"categoryorder": "total ascending"})
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
                st.markdown(f"**Detail per player · {fond_label}**")
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

    # ------------------------------------------------------------------
    # TAB 2 — Game distribution (who attacks on which set type)
    # ------------------------------------------------------------------
    with tab_distribuzione:
        st.caption(
            "For each player: how many times she attacks on each set type and with what effectiveness. "
            "Reflects the game distribution set by the setter."
        )

        col_partita, col_fond, col_metrica = st.columns(3)
        with col_partita:
            partita_sel2 = st.selectbox("Match", partita_options, key="dist_partita")
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

        dist = scout[
            (scout["match"] == partita_sel2)
            & (scout["fondamentale"] == fond_sel2)
            & (~scout["is_team"])
            & (scout["palla"] != "Totale")
            & (scout["Tot"] > 0)
        ].copy()
        dist["palla_en"] = dist["palla"].map(dl.PALLA_LABELS)

        if dist.empty:
            st.info("No data available for this match/fundamental combination.")
        else:
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
