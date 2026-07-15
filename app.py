import streamlit as st

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
        ["Home", "Atlete", "Partite", "Carico & Wellness", "Confronti", "Formazioni", "Inserimento dati"],
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
    section_header("Home", "Colpo d'occhio giornaliero per lo staff: cosa richiede attenzione oggi, in bozza — da definire insieme.")
    
    # Allerta recupero
    st.markdown("""
        <div class="alert-card">
            ⚠️ <b>Recupero basso</b> — Egonu (TQR 11.2), Orro (12.4), Bajema (12.3) sotto soglia questa settimana
        </div>
    """, unsafe_allow_html=True)
    
    # Bozza di lavoro
    st.markdown("""
        <div class="draft-block">
            <div class="draft-label">Bozza di lavoro</div>
            <div class="ph-line">📅 Prossimo impegno (partita/allenamento) — nessuna fonte dati calendario ancora collegata</div>
            <div class="ph-line">⚡ Accesso rapido: Atlete · Partite · Inserimento dati</div>
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
    st.info("Ogni scheda partita: statistiche per fondamentale (come nel foglio TOTALE) + possibilità di filtrare per singola atleta.")

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