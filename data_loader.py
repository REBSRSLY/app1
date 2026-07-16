"""Caricamento e parsing dei dati grezzi di scouting (Data Volley) e wellness.

I fogli di ``anonymized_matches_F.xlsx`` replicano l'export "per fondamentale"
di Data Volley: blocchi ripetuti di righe (Fondamentale -> Palla -> Giocatore)
separati da righe delimitatore (-1 / 0). Questo modulo normalizza tutto in
DataFrame "long" facili da filtrare e plottare.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

MATCHES_FILE = "anonymized_matches_F.xlsx"
WELLNESS_FILE = "anonymized_wellness_file.xlsx"

SEASON_LABEL = "Stagione (Totale)"

# Ordine categorico fisso per il tipo di alzata: usato ovunque per colori/assi coerenti.
PALLA_ORDER = ["Alta", "Media", "Veloce", "Tesa", "Other", "Totale"]

FONDAMENTALI_CON_PALLA = ["Attacco", "Att dopo Ricez", "Contrattacco", "Muro"]

# Mappa colonna Excel (0-indexed) -> nome campo, replicando l'header a riga 2
# di ogni foglio scout ('Fondam.', 'Palla', 'Giocatore', 'P', 'Set', Ind, *E%, Tot, =, %, BP, pC, /, %, BP, pC, -, %, !, %, +, %, #, %, BP, pC).
# I nomi dei campi seguono il SIMBOLO Data Volley (non il suo significato, che è
# specifico per fondamentale — vedi GLOSSARIO più sotto e "istruzioni simbologia.txt").
SCOUT_COLS = {
    3: "P",
    4: "Set",
    6: "Ind",
    7: "E_pct",
    9: "Tot",
    11: "Err",  # "="
    12: "Err_pct",
    13: "Err_BP",
    14: "Err_pC",
    16: "Slash",  # "/"
    17: "Slash_pct",
    18: "Slash_BP",
    19: "Slash_pC",
    21: "Neg",  # "-"
    22: "Neg_pct",
    24: "Neutro",  # "!"
    25: "Neutro_pct",
    27: "Pos",  # "+"
    28: "Pos_pct",
    30: "Perfetto",  # "#"
    31: "Perfetto_pct",
    32: "Perfetto_BP",
    33: "Perfetto_pC",
}

NUMERIC_COLS = list(SCOUT_COLS.values())

# ---------------------------------------------------------------------------
# Glossario simbologia scout, da "istruzioni simbologia.txt".
# Stessi simboli (=, -, !, +, #, /) hanno significato diverso per fondamentale:
# qui mappiamo ogni fondamentale al nome corretto delle sue due grade "headline"
# (# = miglior esito, = = errore) più la legenda completa per i tooltip/caption.
# "Att dopo Ricez" e "Contrattacco" sono varianti di attacco e condividono la
# stessa grading table di "Attacco".
# ---------------------------------------------------------------------------
GLOSSARIO = {
    "Battuta": {
        "perfetto": "Ace",
        "errore": "Errore (rete/fuori)",
        "legenda": [
            ("=", "Errore", "Battuta in rete o fuori."),
            ("-", "Scarso", "Battuta facile che permette una ricezione perfetta all'avversario."),
            ("!", "Neutro", "Battuta normale (es. float) che mantiene il gioco in equilibrio."),
            ("+", "Buono", "Battuta insidiosa che mette in difficoltà la ricezione avversaria."),
            ("#", "Ace", "Punto diretto al servizio."),
        ],
    },
    "Ricezione": {
        "perfetto": "Ricezione eccellente",
        "errore": "Errore / Ace subìto",
        "legenda": [
            ("=", "Errore / Ace subìto", "La ricezione fallisce e l'avversario fa punto."),
            ("-", "Scarso", "Ricezione molto staccata da rete o imprecisa."),
            ("!", "Sufficiente", "Ricezione media: il palleggiatore deve correre ma la palla è rigiocabile."),
            ("+", "Buono", "Ricezione positiva che permette molteplici scelte d'attacco."),
            ("#", "Eccellente", 'Ricezione perfetta "in testa" al palleggiatore.'),
            ("/", "Slash", "Ricezione pessima che torna direttamente nel campo avversario a filo rete."),
        ],
    },
    "Attacco": {
        "perfetto": "Punto",
        "errore": "Errore",
        "legenda": [
            ("=", "Errore", "Attacco spedito direttamente fuori o in rete."),
            ("!", "Neutro", "Attacco tenuto dalla difesa avversaria (palla difesa e rigiocata)."),
            ("#", "Punto", "Attacco vincente che mette a terra la palla o fa mani-out."),
        ],
    },
    "Muro": {
        "perfetto": "Muro punto",
        "errore": "Errore",
        "legenda": [
            ("=", "Errore", "Errore al muro (es. tocco di rete o invasione)."),
            ("-", "Invasione / tocco negativo", "Muro che tocca la palla ma la devia agevolando l'avversario."),
            ("!", "Neutro", "Tocco di contenimento: il muro smorza la palla e la squadra può difenderla."),
            ("#", "Muro punto", "Blocco vincente che rispedisce la palla a terra nel campo avversario."),
        ],
    },
    "Difesa": {
        "perfetto": "Difesa eccellente",
        "errore": "Errore",
        "legenda": [
            ("=", "Errore", "Difesa fallita (la palla cade a terra o vola via senza controllo)."),
            ("-", "Scarso", "Difesa difettosa che non permette una ricostruzione pulita."),
            ("!", "Neutro", "Difesa che tiene la palla alta e rigiocabile, anche se staccata."),
            ("+", "Buono", "Ottima difesa che permette al palleggiatore di ricostruire un contrattacco."),
            ("#", "Eccellente", "Difesa perfetta posizionata direttamente nella zona del palleggiatore."),
        ],
    },
    "Free ball": {
        "perfetto": "Eccellente",
        "errore": "Errore",
        "legenda": [
            ("=", "Errore", "Clamoroso errore su palla facile (es. palla che cade per malinteso)."),
            ("+ / #", "Positivo / Eccellente", "Free ball appoggiata alla perfezione al palleggiatore."),
        ],
    },
    "Alzata": {
        "perfetto": "Alzata eccellente",
        "errore": "Errore",
        "legenda": [
            ("=", "Errore", "Fallo di palleggio (es. doppia, trattenuta) o alzata completamente fuori misura."),
            ("-", "Scarso", "Alzata imprecisa che mette in netta difficoltà l'attaccante."),
            ("#", "Eccellente", "Alzata perfetta."),
        ],
    },
}
GLOSSARIO["Att dopo Ricez"] = GLOSSARIO["Attacco"]
GLOSSARIO["Contrattacco"] = GLOSSARIO["Attacco"]


def perfetto_label(fondamentale: str) -> str:
    """Nome del miglior esito (simbolo '#') per il fondamentale dato."""
    return GLOSSARIO.get(fondamentale, {}).get("perfetto", "Perfetto")


def errore_label(fondamentale: str) -> str:
    """Nome dell'errore (simbolo '=') per il fondamentale dato."""
    return GLOSSARIO.get(fondamentale, {}).get("errore", "Errore")


def legenda_fondamentale(fondamentale: str) -> list[tuple[str, str, str]]:
    """Legenda completa (simbolo, nome, descrizione) per il fondamentale dato."""
    return GLOSSARIO.get(fondamentale, {}).get("legenda", [])


def _parse_scout_sheet(df: pd.DataFrame, match_label: str) -> list[dict]:
    """Trasforma un foglio scout grezzo (header=None) in righe 'long'."""
    rows = []
    fondamentale = None
    palla = None

    for i in range(len(df)):
        c0 = df.iat[i, 0]
        c1 = df.iat[i, 1]
        c2 = df.iat[i, 2]

        if isinstance(c0, str) and c0 != "Fondam.":
            fondamentale = c0
            palla = None  # nuovo fondamentale -> si riparte dal blocco 'Totale'
        elif c0 in (-1, 0) and pd.isna(c2):
            continue  # riga delimitatore tra blocchi

        if fondamentale is None or pd.isna(c2):
            continue

        if pd.notna(c1):
            palla = c1

        if c2 == "Squadra":
            player_code = None
            is_team = True
        elif isinstance(c2, str) and c2.startswith("player "):
            player_code = c2.replace("player ", "").strip()
            is_team = False
        elif c2 == "UNKNOWN":
            player_code = "UNKNOWN"
            is_team = False
        else:
            continue

        row = {
            "match": match_label,
            "fondamentale": fondamentale,
            "palla": palla if palla is not None else "Totale",
            "is_team": is_team,
            "player_code": player_code,
        }
        for col_idx, name in SCOUT_COLS.items():
            row[name] = df.iat[i, col_idx]
        rows.append(row)
    return rows


@st.cache_data(show_spinner="Carico i dati di scouting...")
def load_player_names() -> dict[str, str]:
    """Mappa codice giocatrice -> nome reale, solo squadra A1 Femminile."""
    an = pd.read_excel(WELLNESS_FILE, sheet_name="Anagrafica")
    f = an[an["Squadra"] == "A1F"].copy()
    f["code"] = f["Atleta"].str.replace("player ", "", regex=False).str.strip()
    names = dict(zip(f["code"], f["Unnamed: 3"]))
    names["UNKNOWN"] = "Sconosciuta"
    return names


@st.cache_data(show_spinner="Carico i dati di scouting...")
def load_scout_data() -> pd.DataFrame:
    """Carica e normalizza tutti i fogli scout (Totale stagione + ogni partita)."""
    xl = pd.ExcelFile(MATCHES_FILE)
    all_rows: list[dict] = []

    for sheet in xl.sheet_names:
        label = SEASON_LABEL if sheet == "TOTALE 23-24" else sheet
        raw = xl.parse(sheet, header=None)
        all_rows.extend(_parse_scout_sheet(raw, label))

    data = pd.DataFrame(all_rows)
    data[NUMERIC_COLS] = data[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")

    names = load_player_names()
    data["player_name"] = data["player_code"].map(names)
    data.loc[data["is_team"], "player_name"] = "Squadra"

    data["palla"] = pd.Categorical(data["palla"], categories=PALLA_ORDER, ordered=True)
    return data


@st.cache_data(show_spinner="Carico il calendario partite...")
def load_match_list() -> list[str]:
    """Elenco date partita (esclusa la Stagione), ordine cronologico decrescente."""
    xl = pd.ExcelFile(MATCHES_FILE)
    dates = [s for s in xl.sheet_names if s != "TOTALE 23-24"]
    return sorted(dates, reverse=True)


@st.cache_data(show_spinner="Carico i dati wellness...")
def load_wellness_data() -> dict[str, pd.DataFrame]:
    """Carica i fogli wellness/RPE/salti della squadra femminile con nomi reali."""
    names = load_player_names()

    rpe = pd.read_excel(WELLNESS_FILE, sheet_name="Rpe TL F")
    wellness = pd.read_excel(WELLNESS_FILE, sheet_name="Wellness F")
    salti = pd.read_excel(WELLNESS_FILE, sheet_name="SALTI_F")

    for d in (rpe, wellness, salti):
        d["player_code"] = d["Atleta"].str.replace("player ", "", regex=False).str.strip()
        d["player_name"] = d["player_code"].map(names)

    return {"rpe": rpe, "wellness": wellness, "salti": salti}
