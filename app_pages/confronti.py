import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from ui_helpers import close_polygon, dark_polar_layout, date_range_picker, section_header

# A sensible default fundamental to open on for each role — still changeable via the selector.
DEFAULT_FONDAMENTALE_PER_ROLE = {
    "Palleggio": "Alzata",
    "Opposto": "Attacco",
    "Centro": "Muro",
    "Banda": "Attacco",
    "Libero": "Ricezione",
}

# Same wellness constants as wellness.py (kept local since this page only needs the
# team-radar piece, not the full wellness page).
NEGATIVE_PARAMS = ["Fatica", "Sonno", "Doms", "Stress", "Mood"]
PARAM_LABELS = {
    "Fatica": "Fatigue", "Sonno": "Sleep", "Doms": "Muscle soreness",
    "Stress": "Stress", "Mood": "Mood", "Tqr": "TQR",
}
PARAM_RANGE = {
    "Fatica": (1, 5), "Sonno": (1, 5), "Doms": (1, 5),
    "Stress": (1, 5), "Mood": (1, 5), "Tqr": (6, 20),
}


def render():
    section_header(
        "Comparisons",
        "Pick a role to see and compare all data for the players who play it.",
    )

    names = dl.load_player_names()
    roles = dl.load_player_roles()

    role_sel = st.selectbox(
        "Role", list(dl.ROLE_LABELS.keys()),
        format_func=lambda r: dl.ROLE_LABELS[r], key="cmp_role",
    )
    role_players = sorted(names[code] for code, r in roles.items() if r == role_sel and code in names)
    st.caption(f"Comparing: {', '.join(role_players)}" if role_players else "No players found for this role.")

    if not role_players:
        return

    tab_scout, tab_wellness, tab_jumps, tab_rpe = st.tabs(["Scouting", "Wellness", "Jumps", "RPE / Load"])

    # ------------------------------------------------------------------
    # TAB 1 — Scouting (volume + efficiency + detail, role players only)
    # ------------------------------------------------------------------
    with tab_scout:
        scout = dl.load_scout_data()
        matches = dl.load_match_list()
        partita_options = [dl.SEASON_LABEL] + matches
        fondamentali = sorted(scout["fondamentale"].unique())
        default_fond = DEFAULT_FONDAMENTALE_PER_ROLE.get(role_sel, "Attacco")

        col_partita, col_fond = st.columns(2)
        with col_partita:
            partita_sel = st.selectbox("Match", partita_options, key="cmp_partita")
        with col_fond:
            fond_sel = st.selectbox(
                "Fundamental", fondamentali,
                index=fondamentali.index(default_fond) if default_fond in fondamentali else 0,
                format_func=lambda f: dl.FONDAMENTALE_LABELS.get(f, f),
                key="cmp_fond",
            )
        fond_label = dl.FONDAMENTALE_LABELS.get(fond_sel, fond_sel)

        perfetto_lbl = dl.perfetto_label(fond_sel)
        errore_lbl = dl.errore_label(fond_sel)
        legenda = dl.legenda_fondamentale(fond_sel)
        if legenda:
            with st.expander(f"How to read \"{fond_label}\"", icon=":material/menu_book:"):
                for simbolo, nome, descrizione in legenda:
                    st.markdown(f"**{simbolo}** · {nome} — {descrizione}")

        base = scout[
            (scout["match"] == partita_sel) & (scout["fondamentale"] == fond_sel)
            & (scout["palla"] == "Totale") & (~scout["is_team"])
            & scout["player_name"].isin(role_players)
        ].sort_values("Tot", ascending=False)

        if base.empty:
            st.info("No data available for this role/match/fundamental combination.")
        else:
            col_vol, col_eff = st.columns(2)
            with col_vol:
                with st.container(border=True):
                    st.markdown(f"**Actions per player · {fond_label}**")
                    fig_vol = px.bar(
                        base, x="Tot", y="player_name", orientation="h",
                        labels={"Tot": "Total actions", "player_name": ""},
                        color_discrete_sequence=["#4C78A8"],
                    )
                    fig_vol.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig_vol, width="stretch")

            with col_eff:
                with st.container(border=True):
                    st.markdown(f"**Efficiency (E%) per player · {fond_label}**")
                    base_eff = base.sort_values("E_pct")
                    fig_eff = px.bar(
                        base_eff, x="E_pct", y="player_name", orientation="h",
                        labels={"E_pct": "Efficiency E%", "player_name": ""},
                        color="E_pct", color_continuous_scale="RdBu", color_continuous_midpoint=0,
                    )
                    fig_eff.update_layout(coloraxis_showscale=False, xaxis_tickformat=".0%")
                    st.plotly_chart(fig_eff, width="stretch")

            with st.container(border=True):
                st.markdown(f"**Detail per player · {fond_label}**")
                col_perfetto = f"% {perfetto_lbl} (#)"
                col_errore = f"% {errore_lbl} (=)"
                tabella = base[["player_name", "Tot", "E_pct", "Perfect_pct", "Err_pct"]].rename(columns={
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
    # TAB 2 — Wellness (team radar, role players only)
    # ------------------------------------------------------------------
    with tab_wellness:
        wellness = dl.load_wellness_data()["wellness"]
        wellness = wellness[wellness["player_name"].isin(role_players)]

        if wellness.empty:
            st.info("No wellness data for this role.")
        else:
            start_d, end_d = date_range_picker("Date range", wellness["Data"], 7, "cmp_wellness_dates")
            period = wellness[(wellness["Data"].dt.date >= start_d) & (wellness["Data"].dt.date <= end_d)]
            st.caption(f"Averages over {start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')}.")

            param = st.selectbox(
                "Parameter", list(PARAM_LABELS.keys()),
                format_func=lambda p: PARAM_LABELS[p], key="cmp_param",
            )
            players_with_data = sorted(period["player_name"].unique())
            team_avg = period.groupby("player_name")[param].mean().reindex(players_with_data)

            if team_avg.empty:
                st.info("No data in this date range.")
            else:
                lo, hi = PARAM_RANGE[param]
                is_negative = param in NEGATIVE_PARAMS
                r, theta = close_polygon(list(team_avg.values), list(team_avg.index))
                fig = go.Figure(go.Scatterpolar(
                    r=r, theta=theta, fill="toself",
                    line_color="#c0392b" if is_negative else "#2ecc71",
                    fillcolor="rgba(192,57,43,0.25)" if is_negative else "rgba(46,204,113,0.25)",
                ))
                fig.update_layout(**dark_polar_layout([lo, hi]))
                st.plotly_chart(fig, width="stretch", theme=None)

    # ------------------------------------------------------------------
    # TAB 3 — Jumps (stacked bar, role players only)
    # ------------------------------------------------------------------
    with tab_jumps:
        salti = dl.load_wellness_data()["salti"]
        salti_players = sorted(set(salti["player_name"].dropna().unique()) & set(role_players))

        if not salti_players:
            st.info("No jump data for this role.")
        else:
            start_d, end_d = date_range_picker("Date range", salti["Data"], 14, "cmp_jumps_dates")
            sel_players = st.multiselect("Players", salti_players, default=salti_players, key="cmp_jumps_players")

            mask = (
                (salti["Data"].dt.date >= start_d) & (salti["Data"].dt.date <= end_d)
                & salti["player_name"].isin(sel_players)
            )
            period = salti[mask].dropna(subset=["SALTI"])

            if period.empty:
                st.info("No jump data for this selection.")
            else:
                daily = period.groupby(["Data", "player_name"], as_index=False)["SALTI"].sum()
                fig = px.bar(
                    daily, x="Data", y="SALTI", color="player_name", barmode="stack",
                    labels={"Data": "Date", "SALTI": "Jumps", "player_name": "Player"},
                )
                fig.update_layout(legend_title_text="Player")
                st.plotly_chart(fig, width="stretch")

    # ------------------------------------------------------------------
    # TAB 4 — RPE / Training Load (line chart, role players only)
    # ------------------------------------------------------------------
    with tab_rpe:
        rpe = dl.load_wellness_data()["rpe"]
        rpe_players = sorted(set(rpe["player_name"].dropna().unique()) & set(role_players))

        if not rpe_players:
            st.info("No RPE/load data for this role.")
        else:
            start_d, end_d = date_range_picker("Date range", rpe["Data"], 14, "cmp_rpe_dates")

            metric_label = st.segmented_control(
                "Metric", ["RPE", "Training Load"], default="Training Load", required=True, key="cmp_rpe_metric",
            )
            metric_col = "Rpe" if metric_label == "RPE" else "TL"
            agg = "mean" if metric_col == "Rpe" else "sum"

            sel_players = st.multiselect(
                "Players to compare", rpe_players, default=rpe_players, key="cmp_rpe_players",
            )

            mask = (
                (rpe["Data"].dt.date >= start_d) & (rpe["Data"].dt.date <= end_d)
                & rpe["player_name"].isin(sel_players)
            )
            period = rpe[mask].dropna(subset=[metric_col])

            if not sel_players or period.empty:
                st.info("Select at least one player with data in this date range.")
            else:
                daily = period.groupby(["Data", "player_name"], as_index=False)[metric_col].agg(agg)
                fig = px.line(
                    daily.sort_values("Data"), x="Data", y=metric_col, color="player_name", markers=True,
                    labels={"Data": "Date", metric_col: metric_label, "player_name": "Player"},
                )
                fig.update_layout(legend_title_text="Player")
                st.plotly_chart(fig, width="stretch")
