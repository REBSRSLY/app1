import streamlit as st

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import data_loader as dl

# Colori fissi per tipo di alzata: stesso colore ovunque nell'app, ordine mai ciclico.
PALLA_COLORS = {
    "Alta": "#4C78A8",
    "Media": "#F58518",
    "Veloce": "#54A24B",
    "Tesa": "#E45756",
    "Other": "#B0B0B0",
}

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="Vero Volley Milano - Staff Tecnico",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# CSS Personalizzato per replicare lo stile pulito del mockup React
# ---------------------------------------------------------------------------
st.markdown("""
    <style>
        /* Variabili e stili generali */
        :root {
            --accent: #c0392b;
            --accent-bg: #fbeceb;
            --muted: #8a8a8a;
            --line: #e6e6e6;
        }
        
        /* Stile sidebar */
        .css-1d391kg { padding-top: 2rem; }
        .brand-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0px;
        }
        .brand-subtitle {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 1.5rem;
        }
        
        /* Box Bozze di lavoro */
        .draft-block {
            border: 1px dashed #c6c6c6;
            border-radius: 10px;
            padding: 16px;
            background-color: #fcfcfc;
            margin-bottom: 15px;
        }
        .draft-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #8a8a8a;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .ph-line {
            color: #555555;
            font-size: 13.5px;
            margin-bottom: 8px;
        }
        .ph-line:last-child { margin-bottom: 0; }

        /* Card di Allerta (TQR) */
        .alert-card {
            background-color: #fff6ea;
            border: 1px solid #f0dcb4;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            color: #1a1a1a;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Badge di Capitano */
        .cap-tag {
            display: inline-block;
            margin-left: 8px;
            font-size: 10px;
            font-style: normal;
            text-transform: uppercase;
            color: #c0392b;
            border: 1px solid #e6bdb8;
            border-radius: 4px;
            padding: 1px 5px;
            font-weight: bold;
        }

        /* Chips per le date delle partite */
        .chip-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .date-chip {
            border: 1px solid #e6e6e6;
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 12.5px;
            font-family: monospace;
            color: #444;
            background-color: #ffffff;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dati reali di riferimento (Vero Volley Milano, A1 Femminile 23/24)
# ---------------------------------------------------------------------------

titolari = [
    {"pos": "P1", "role": "Palleggio", "name": "Orro", "code": "TS3H", "tag": "Capitano"},
    {"pos": "P2", "role": "Opposto", "name": "Egonu", "code": "3GS4"},
    {"pos": "P3", "role": "Centro", "name": "Folie", "code": "8EZC", "alt": "Heyrman (Z4SY)"},
    {"pos": "P4", "role": "Banda", "name": "Sylla", "code": "09RI"},
    {"pos": "P5", "role": "Banda", "name": "Cazaute", "code": "62DH", "alt": "Daalderop (II9W)"},
    {"pos": "P6", "role": "Centro", "name": "Rettke", "code": "XPN2"},
    {"pos": "L", "role": "Libero", "name": "Castillo", "code": "W0GU"},
]

panchina = [
    {"role": "Opposto", "name": "Malual", "code": "P4T5"},
    {"role": "Centro", "name": "Candi", "code": "NEMC"},
    {"role": "Palleggio", "name": "Prandi", "code": "LC8Z"},
    {"role": "Banda", "name": "Bajema", "code": "1L4C"},
    {"role": "Libero", "name": "Parrocchiale", "code": "M9TM"},
    {"role": "Libero", "name": "Pusic", "code": "BWR1"},
]

partite = [
    "24-05-05", "24-04-10", "24-04-06", "24-03-31", "24-03-27", "24-03-24",
    "24-03-19", "24-03-16", "24-03-12", "24-03-09", "...", "23-10-14", "23-10-08"
]

# ---------------------------------------------------------------------------
# Sidebar & Navigazione
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="brand-title">Vero Volley Milano</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Staff tecnico · A1 Femminile</div>', unsafe_allow_html=True)
    
    # Menu di navigazione nativo di Streamlit
    menu = st.radio(
        "Menu Navigazione",
        ["Home", "Atlete", "Partite", "Scout & Statistiche", "Carico & Wellness", "Confronti", "Formazioni", "Inserimento dati"],
        label_visibility="collapsed"
    )

# Funzione Shell di Sezione
def section_header(title, purpose):
    st.title(title)
    st.caption(purpose)
    st.write("---")

# ---------------------------------------------------------------------------
# Rendering Sezioni
# ---------------------------------------------------------------------------

# --- HOME ---
if menu == "Home":
    section_header("Home", "Colpo d'occhio sulla stagione: numeri chiave da scouting e wellness.")

    matches = dl.load_match_list()
    wellness = dl.load_wellness_data()["wellness"]

    with st.container(horizontal=True):
        st.metric("Partite analizzate", len(matches), border=True)
        st.metric("Atlete monitorate", len(dl.load_player_names()) - 1, border=True)
        st.metric("Prima partita", min(matches), border=True)
        st.metric("Ultima partita", max(matches), border=True)

    # Allerta recupero: TQR più basso registrato nell'ultimo giorno di rilevazione disponibile
    ultima_data = wellness["Data"].max()
    ultimo_giorno = wellness[wellness["Data"] == ultima_data].sort_values("Tqr")
    soglia = 15
    sotto_soglia = ultimo_giorno[ultimo_giorno["Tqr"] < soglia]

    if not sotto_soglia.empty:
        atlete_str = " · ".join(f"{r.player_name} (TQR {r.Tqr:.1f})" for r in sotto_soglia.itertuples())
        st.markdown(f"""
            <div class="alert-card">
                ⚠️ <b>Recupero basso</b> — {atlete_str} sotto soglia {soglia} il {ultima_data.strftime('%d/%m/%Y')}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="alert-card">
                ✅ <b>Recupero nella norma</b> — nessuna atleta sotto soglia {soglia} il {ultima_data.strftime('%d/%m/%Y')}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Accesso rapido</div>
            <div class="ph-line">📊 <b>Scout & Statistiche</b> — statistiche per fondamentale e distribuzione del gioco in attacco</div>
            <div class="ph-line">💤 <b>Carico & Wellness</b> — trend TQR, RPE e salti (in bozza, da definire insieme)</div>
            <div class="ph-line">📅 Prossimo impegno (partita/allenamento) — nessuna fonte dati calendario ancora collegata</div>
        </div>
    """, unsafe_allow_html=True)

# --- ATLETE ---
elif menu == "Atlete":
    section_header("Atlete", "Rosa completa. Ogni riga apre la scheda individuale con wellness + rendimento incrociati.")
    
    search_query = st.text_input("🔍 Cerca atleta...", placeholder="Inserisci il nome...")
    
    # Funzione helper per filtrare e visualizzare le atlete
    def render_atleta_row(p, is_titolare=True):
        pos_str = f"**{p['pos']}**" if is_titolare else "—"
        tag_html = f'<span class="cap-tag">{p["tag"]}</span>' if "tag" in p else ""
        alt_str = f" *(alterna con {p['alt']})*" if "alt" in p else ""
        
        col1, col2, col3, col4 = st.columns([1, 4, 3, 2])
        with col1:
            st.markdown(pos_str)
        with col2:
            st.markdown(f"**{p['name']}** {tag_html}", unsafe_allow_html=True)
        with col3:
            st.write(p['role'])
        with col4:
            st.code(p['code'])
        
        if alt_str:
            st.caption(alt_str)
        st.write("---")

    st.subheader("Titolari")
    st.write("---")
    for p in titolari:
        if not search_query or search_query.lower() in p['name'].lower():
            render_atleta_row(p, is_titolare=True)
            
    st.subheader("Panchina")
    st.write("---")
    for p in panchina:
        if not search_query or search_query.lower() in p['name'].lower():
            render_atleta_row(p, is_titolare=False)

# --- PARTITE ---
elif menu == "Partite":
    section_header("Partite", "Elenco partite stagione (45 rilevate). Ogni partita apre lo scouting per fondamentale.")
    
    st.text_input("🔍 Filtra per data...", placeholder="Es. 24-03")
    
    # Rendering dei chip delle date delle partite in HTML
    chips_html = "".join([f'<span class="date-chip">{d}</span>' for d in partite])
    st.markdown(f'<div class="chip-container">{chips_html}</div>', unsafe_allow_html=True)
    
    st.write("")
    st.info("Per le statistiche per fondamentale di ogni partita (come nel foglio TOTALE), filtrabili per singola atleta, vai su **Scout & Statistiche**.")

# --- CARICO & WELLNESS ---
elif menu == "Carico & Wellness":
    section_header("Carico & Wellness", "Monitoraggio giornaliero: questionario wellness (Fatica, Sonno, Doms, Stress, Mood, TQR), RPE/Training Load, conteggio salti — per squadra o singola atleta.")
    
    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">📈 <b>Vista squadra:</b> trend TQR medio nel tempo (già in bozza nel primo mockup)</div>
            <div class="ph-line">👤 <b>Vista atleta:</b> stesso trend filtrato + confronto con carico (RPE × durata) e salti giornalieri</div>
            <div class="ph-line">⚙️ Soglie di allerta configurabili (es. TQR sotto una certa media)</div>
        </div>
    """, unsafe_allow_html=True)

# --- CONFRONTI ---
elif menu == "Confronti":
    section_header("Confronti", "Mettere a confronto due o più atlete, o due periodi della stagione, sulle stesse metriche (wellness o scouting).")
    
    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">🎛️ <b>Selettore:</b> 2+ atlete oppure 2 intervalli di date</div>
            <div class="ph-line">📊 <b>Metriche disponibili:</b> qualsiasi fondamentale scouting, TQR, RPE, salti</div>
            <div class="ph-line">💡 <b>Esempio d'uso:</b> Folie vs Heyrman nel periodo di alternanza per infortunio</div>
        </div>
    """, unsafe_allow_html=True)

# --- FORMAZIONI ---
elif menu == "Formazioni":
    section_header("Formazioni", "Sestetto titolare, rotazioni e alternanze per ruolo, con lo stato di recupero di chi è in campo.")
    
    # Rappresentazione del campo da gioco (3x2 per il sestetto attivo)
    st.subheader("Disposizione in Campo (Sestetto)")
    
    campo_titolari = [p for p in titolari if p["pos"] != "L"]
    
    # Divisione in 3 colonne per simulare la griglia del campo da gioco
    cols = st.columns(3)
    for i, p in enumerate(campo_titolari):
        col_index = i % 3
        with cols[col_index]:
            alt_text = f"\n↔ {p['alt']}" if "alt" in p else ""
            st.metric(
                label=f"{p['pos']} - {p['role']}",
                value=p['name'],
                delta=alt_text if alt_text else None,
                delta_color="off"
            )
            
    st.write("---")
    libero = next(p for p in titolari if p["pos"] == "L")
    st.write(f"🛡️ **Libero:** {libero['name']} (`{libero['code']}`)")

# --- INSERIMENTO DATI ---
elif menu == "Inserimento dati":
    section_header("Inserimento dati", "Caricamento nuovi dati: wellness/RPE/salti giornalieri per atleta, oppure scouting di una nuova partita.")
    
    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">📝 <b>Form wellness giornaliero:</b> seleziona atleta + data → Fatica, Sonno, Doms, Stress, Mood (calcolo TQR automatico)</div>
            <div class="ph-line">⏱️ <b>Form RPE/salti:</b> seleziona sessione (AM/PM) → RPE, durata, numero salti</div>
            <div class="ph-line">📥 <b>Import scouting partita:</b> caricamento da file esterno (formato da definire) oppure inserimento manuale per fondamentale</div>
        </div>
    """, unsafe_allow_html=True)

# --- SCOUT & STATISTICHE ---
elif menu == "Scout & Statistiche":
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