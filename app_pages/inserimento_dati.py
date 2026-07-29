import pandas as pd
import streamlit as st

import data_loader as dl

UPLOAD_TYPES = ["Match scouting sheet", "Wellness / RPE / Jumps data"]

# Sheet name -> columns a well-formed sheet of that kind should have,
# matching anonymized_wellness_file.xlsx's own layout exactly.
EXPECTED_WELLNESS_SHEETS = {
    "Wellness F": ["Atleta", "Data", "Fatica", "Sonno", "Doms", "Stress", "Mood", "Tqr"],
    "Rpe TL F": ["Atleta", "Data", "Rpe"],
    "SALTI_F": ["Atleta", "Data", "AM-PM", "SALTI"],
    "Anagrafica": ["Atleta", "Squadra", "Ruolo"],
}


def _open_workbook(uploaded):
    try:
        return pd.ExcelFile(uploaded)
    except Exception as e:
        st.error(f"Couldn't open this as an Excel workbook: {e}")
        return None


def _render_scout_upload():
    st.caption(
        "Upload a Data Volley-style scouting workbook -- same layout as the app's own "
        "anonymized_matches_F.xlsx (one sheet per match: Fondam. / Palla / Giocatore in the "
        "first three columns, then the P / Set / Ind / E% / Tot / outcome block). Parsed with "
        "the exact same logic the app uses to load its own bundled data."
    )
    uploaded = st.file_uploader("Scouting workbook (.xlsx)", type=["xlsx"], key="scout_upload")
    if uploaded is None:
        return

    xl = _open_workbook(uploaded)
    if xl is None:
        return

    sheet_names = xl.sheet_names
    all_rows: list[dict] = []
    per_sheet_counts: dict[str, int] = {}
    for sheet in sheet_names:
        raw = xl.parse(sheet, header=None)
        rows = dl.parse_scout_sheet(raw, sheet)
        per_sheet_counts[sheet] = len(rows)
        all_rows.extend(rows)

    empty_sheets = [s for s, n in per_sheet_counts.items() if n == 0]
    if empty_sheets:
        st.warning(
            f"No recognizable rows in: {', '.join(empty_sheets)}. These sheets likely don't "
            "match the expected layout (Fondam. / Palla / Giocatore in the first three columns)."
        )

    if not all_rows:
        st.error("Nothing could be parsed from this file -- check it matches the expected scouting sheet layout.")
        return

    parsed = pd.DataFrame(all_rows)
    parsed[dl.NUMERIC_COLS] = parsed[dl.NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")

    st.success(f"Parsed {len(parsed)} rows from {len(sheet_names)} sheet(s): {', '.join(sheet_names)}.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows parsed", len(parsed), border=True)
    col2.metric("Fundamentals found", parsed["fondamentale"].nunique(), border=True)
    col3.metric("Players found", parsed[~parsed["is_team"]]["player_code"].nunique(), border=True)

    with st.container(border=True):
        st.markdown("**Preview** · first 50 parsed rows")
        preview = parsed.head(50).rename(columns={
            "match": "Sheet", "fondamentale": "Fundamental", "palla": "Set type",
            "is_team": "Is team", "player_code": "Player code",
        })
        st.dataframe(preview, hide_index=True, width="stretch")

    st.caption(
        "This confirms the app can correctly read this file's layout. It doesn't feed into the "
        "rest of the dashboard for this session yet -- ask if you'd like that wired up next."
    )


def _render_wellness_upload():
    st.caption(
        "Upload a wellness/RPE/jumps workbook -- same layout as the app's own "
        "anonymized_wellness_file.xlsx. The app looks for sheets named 'Wellness F', "
        "'Rpe TL F', 'SALTI_F' or 'Anagrafica' and previews whichever it finds."
    )
    uploaded = st.file_uploader("Wellness workbook (.xlsx)", type=["xlsx"], key="wellness_upload")
    if uploaded is None:
        return

    xl = _open_workbook(uploaded)
    if xl is None:
        return

    matched = [s for s in xl.sheet_names if s in EXPECTED_WELLNESS_SHEETS]
    unmatched = [s for s in xl.sheet_names if s not in EXPECTED_WELLNESS_SHEETS]
    if not matched:
        st.error(
            f"None of this workbook's sheets ({', '.join(xl.sheet_names)}) match an expected "
            f"name ({', '.join(EXPECTED_WELLNESS_SHEETS)})."
        )
        return
    if unmatched:
        st.caption(f"Ignoring unrecognized sheet(s): {', '.join(unmatched)}")

    for sheet in matched:
        df = xl.parse(sheet)
        expected_cols = EXPECTED_WELLNESS_SHEETS[sheet]
        missing = [c for c in expected_cols if c not in df.columns]
        with st.container(border=True):
            st.markdown(f"**{sheet}** · {len(df)} rows")
            if missing:
                st.warning(f"Missing expected column(s): {', '.join(missing)}")
            st.dataframe(df.head(20), hide_index=True, width="stretch")

    st.caption(
        "This confirms the app can correctly read this file's layout. It doesn't feed into the "
        "rest of the dashboard for this session yet -- ask if you'd like that wired up next."
    )


def render():
    st.caption(
        "Upload an Excel file shaped like the app's own data and see exactly what it can read "
        "from it, using the same parsing logic as everywhere else in the app."
    )
    upload_type = st.segmented_control(
        "What are you uploading?", UPLOAD_TYPES, default=UPLOAD_TYPES[0], required=True, key="entry_type",
    )
    if upload_type == UPLOAD_TYPES[0]:
        _render_scout_upload()
    else:
        _render_wellness_upload()
