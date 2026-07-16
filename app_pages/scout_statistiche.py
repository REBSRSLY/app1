import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from ui_helpers import section_header

# Colori fissi per tipo di alzata: stesso colore ovunque nell'app, ordine mai ciclico.
PALLA_COLORS = {
    "Alta": "#4C78A8",
    "Media": "#F58518",
    "Veloce": "#54A24B",
    "Tesa": "#E45756",
    "Other": "#B0B0B0",
}


def render():
    section_header("Scout & Statistiche", "Statistiche di scouting per fondamentale e distribuzione del gioco in attacco, per singola partita o sull'intera stagione.")

    scout = dl.load_scout_data()
    matches = dl.load_match_list()
    partita_options = [dl.SEASON_LABEL] + matches
    palla_tipi = [p for p in dl.PALLA_ORDER if p != "Totale"]

    tab_generale, tab_distribuzione = st.tabs(["Statistiche generali", "Distribuzione del gioco"])

    # ------------------------------------------------------------------
    # TAB 1 — Statistiche generali per fondamentale
    # ------------------------------------------------------------------
    with tab_generale:
        col_partita, col_fond = st.columns(2)
        with col_partita:
            partita_sel = st.selectbox("Partita", partita_options, key="gen_partita")
        with col_fond:
            fondamentali = sorted(scout["fondamentale"].unique())
            fond_sel = st.selectbox(
                "Fondamentale", fondamentali,
                index=fondamentali.index("Attacco") if "Attacco" in fondamentali else 0,
                key="gen_fond",
            )

        perfetto_lbl = dl.perfetto_label(fond_sel)
        errore_lbl = dl.errore_label(fond_sel)
        legenda = dl.legenda_fondamentale(fond_sel)
        if legenda:
            with st.expander(f"Come si legge \"{fond_sel}\"", icon=":material/menu_book:"):
                for simbolo, nome, descrizione in legenda:
                    st.markdown(f"**{simbolo}** · {nome} — {descrizione}")

        base = scout[(scout["match"] == partita_sel) & (scout["fondamentale"] == fond_sel) & (scout["palla"] == "Totale")]
        team_row = base[base["is_team"]]
        players = base[~base["is_team"]].sort_values("Tot", ascending=False)

        if team_row.empty or players.empty:
            st.info("Nessun dato disponibile per questa combinazione di partita e fondamentale.")
        else:
            t = team_row.iloc[0]
            with st.container(horizontal=True):
                st.metric("Azioni totali", int(t["Tot"]), border=True)
                st.metric("Efficienza (E%)", f"{t['E_pct'] * 100:.0f}%", border=True)
                st.metric(f"% {perfetto_lbl} (#)", f"{t['Perfetto_pct'] * 100:.0f}%" if pd.notna(t["Perfetto_pct"]) else "—", border=True)
                st.metric(f"% {errore_lbl} (=)", f"{t['Err_pct'] * 100:.0f}%" if pd.notna(t["Err_pct"]) else "—", border=True)

            col_vol, col_eff = st.columns(2)
            with col_vol:
                with st.container(border=True):
                    st.markdown(f"**Volume di azioni per atleta · {fond_sel}**")
                    fig_vol = px.bar(
                        players, x="Tot", y="player_name", orientation="h",
                        labels={"Tot": "Azioni totali", "player_name": ""},
                        color_discrete_sequence=["#4C78A8"],
                    )
                    fig_vol.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig_vol, width="stretch")

            with col_eff:
                with st.container(border=True):
                    st.markdown(f"**Efficienza (E%) per atleta · {fond_sel}**")
                    players_eff = players.sort_values("E_pct")
                    fig_effp = px.bar(
                        players_eff, x="E_pct", y="player_name", orientation="h",
                        labels={"E_pct": "Efficienza E%", "player_name": ""},
                        color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
                    )
                    fig_effp.update_layout(coloraxis_showscale=False, xaxis_tickformat=".0%")
                    st.plotly_chart(fig_effp, width="stretch")

            with st.container(border=True):
                st.markdown(f"**Dettaglio per atleta · {fond_sel}**")
                col_perfetto = f"% {perfetto_lbl} (#)"
                col_errore = f"% {errore_lbl} (=)"
                tabella = players[["player_name", "Tot", "E_pct", "Perfetto_pct", "Err_pct"]].rename(columns={
                    "player_name": "Atleta",
                    "E_pct": "Efficienza E%",
                    "Perfetto_pct": col_perfetto,
                    "Err_pct": col_errore,
                })
                st.dataframe(
                    tabella,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Tot": st.column_config.NumberColumn(format="%d"),
                        "Efficienza E%": st.column_config.NumberColumn(format="percent"),
                        col_perfetto: st.column_config.NumberColumn(format="percent"),
                        col_errore: st.column_config.NumberColumn(format="percent"),
                    },
                )

    # ------------------------------------------------------------------
    # TAB 2 — Distribuzione del gioco (chi attacca su quale tipo di alzata)
    # ------------------------------------------------------------------
    with tab_distribuzione:
        st.caption(
            "Per ogni giocatrice: quante volte attacca su ciascun tipo di alzata e con quale efficacia. "
            "Riflette la distribuzione del gioco impostata dal palleggio."
        )

        col_partita, col_fond, col_metrica = st.columns(3)
        with col_partita:
            partita_sel2 = st.selectbox("Partita", partita_options, key="dist_partita")
        with col_fond:
            fond_sel2 = st.selectbox("Fondamentale", dl.FONDAMENTALI_CON_PALLA, key="dist_fond")
        with col_metrica:
            metrica_label = st.segmented_control(
                "Metrica di efficacia",
                ["Efficienza (E%)", "% Punto (#)"],
                default="Efficienza (E%)",
                required=True,
                key="dist_metrica",
            )
        metrica_col = "E_pct" if metrica_label == "Efficienza (E%)" else "Perfetto_pct"
        # Il simbolo "#" ha un nome diverso per fondamentale (Punto per l'attacco, Muro punto per il muro).
        metrica_display = "Efficienza (E%)" if metrica_col == "E_pct" else f"% {dl.perfetto_label(fond_sel2)} (#)"
        st.caption(f"Per **{fond_sel2}**: \"#\" = {dl.perfetto_label(fond_sel2)}, \"=\" = {dl.errore_label(fond_sel2)}.")

        dist = scout[
            (scout["match"] == partita_sel2)
            & (scout["fondamentale"] == fond_sel2)
            & (~scout["is_team"])
            & (scout["palla"] != "Totale")
            & (scout["Tot"] > 0)
        ].copy()

        if dist.empty:
            st.info("Nessun dato disponibile per questa combinazione di partita e fondamentale.")
        else:
            ordine_giocatrici = (
                dist.groupby("player_name")["Tot"].sum().sort_values(ascending=False).index.tolist()
            )

            st.markdown("#### Grafico 1 · Mappa del gioco — volume di azioni per tipo di alzata")
            fig1 = px.bar(
                dist, x="player_name", y="Tot", color="palla",
                category_orders={"player_name": ordine_giocatrici, "palla": palla_tipi},
                color_discrete_map=PALLA_COLORS,
                labels={"player_name": "", "Tot": "Numero di azioni", "palla": "Tipo di alzata"},
                barmode="stack",
            )
            fig1.update_layout(legend_title_text="Tipo di alzata")
            st.plotly_chart(fig1, width="stretch")

            st.markdown("#### Grafico 2 · Efficacia per tipo di alzata")
            default_players = ordine_giocatrici[: min(5, len(ordine_giocatrici))]
            giocatrici_sel = st.multiselect(
                "Giocatrici da confrontare", ordine_giocatrici, default=default_players, key="dist_giocatrici"
            )
            dist_line = dist[dist["player_name"].isin(giocatrici_sel)]
            if giocatrici_sel and not dist_line.empty:
                fig2 = px.line(
                    dist_line.sort_values("palla"), x="palla", y=metrica_col, color="player_name",
                    category_orders={"palla": palla_tipi},
                    markers=True,
                    labels={"palla": "Tipo di alzata", metrica_col: metrica_display, "player_name": "Giocatrice"},
                )
                fig2.update_layout(yaxis_tickformat=".0%", legend_title_text="Giocatrice")
                st.plotly_chart(fig2, width="stretch")
            else:
                st.info("Seleziona almeno una giocatrice da confrontare.")

            st.markdown("#### Heatmap · Volume ed efficacia per giocatrice e tipo di alzata")
            pivot_tot = dist.pivot_table(index="player_name", columns="palla", values="Tot", aggfunc="sum", observed=True)
            pivot_metrica = dist.pivot_table(index="player_name", columns="palla", values=metrica_col, aggfunc="mean", observed=True)
            colonne_ordinate = [p for p in palla_tipi if p in pivot_metrica.columns]
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
                # Efficienza può essere negativa: scala divergente centrata su 0.
                heat_kwargs = dict(colorscale="RdBu", zmid=0, zmin=-0.5, zmax=0.5)
            else:
                # % Punto (#) è sempre >= 0: scala sequenziale a tinta unica.
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
                xaxis_title="Tipo di alzata", yaxis_title="", yaxis_autorange="reversed",
                height=max(320, 40 * len(pivot_metrica.index)),
            )
            st.plotly_chart(fig_heat, width="stretch")
            st.caption(f"In ogni cella: numero di azioni totali e {metrica_display.lower()}.")
