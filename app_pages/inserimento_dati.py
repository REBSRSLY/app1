"""Data Entry: the files the app is currently reading, and how to add to them.

One file = one sheet. A scout file is a single match (or a season-total
sheet); a wellness file is one day of one kind, since that's how the staff
export them -- often only one or two of RPE / TQR / jumps exist for a
given day. Uploading writes into files/ and removing moves the file to
files/_archive/, and either way the loaders pick the change up on the next
rerun (data_loader.source_signature keys every cache on the file set).
"""

import datetime as dt

import pandas as pd
import streamlit as st

import data_loader as dl
import file_store as fs
import match_calendar as mc

# Sheet name -> the wellness kind it holds, i.e. what the staff's own
# exports call each sheet. Anything else in an uploaded workbook is
# reported back rather than silently ignored.
WELLNESS_SHEET_KINDS = {sheet: kind for kind, (_label, sheet) in fs.WELLNESS_KINDS.items()}

SEASON_TOTAL_HINTS = ("totale", "total", "season")


def _refresh():
    """Every loader is keyed on the file set, but the small name/role
    lookups are cached without that key -- clearing wholesale is simpler
    than reasoning about which ones survive a file change."""
    st.cache_data.clear()
    st.rerun()


def _fmt_date(day: dt.date | None) -> str:
    return day.strftime("%d %b %Y") if day else "—"


def _render_history(entries: list[dict], empty_msg: str, key_prefix: str):
    if not entries:
        st.caption(empty_msg)
        return
    for entry in entries:
        col_label, col_date, col_x = st.columns([2, 1.6, 0.5], vertical_alignment="center")
        with col_label:
            st.markdown(
                f'<span style="font-weight:600;font-size:0.9rem;">{entry["label"]}</span>',
                unsafe_allow_html=True,
            )
        with col_date:
            st.markdown(
                f'<span style="color:var(--muted);font-size:0.85rem;">{_fmt_date(entry["date"])}</span>',
                unsafe_allow_html=True,
            )
        with col_x:
            if st.button("✕", key=f"{key_prefix}_{entry['path'].name}", help="Remove from the app"):
                fs.archive(entry["path"])
                _refresh()


def _handle_scout_upload(uploaded, season: str):
    """Each sheet in the workbook becomes its own file. Match sheets are
    filed by their own date (a sheet dated last season belongs to last
    season, whatever the picker says); only the undated season-total sheet
    follows the picker."""
    try:
        xl = pd.ExcelFile(uploaded)
    except Exception as e:
        st.error(f"Couldn't open this as an Excel workbook: {e}")
        return

    written, skipped = [], []
    for sheet in xl.sheet_names:
        raw = xl.parse(sheet, header=None)
        rows = dl.parse_scout_sheet(raw, sheet)
        if not rows:
            skipped.append(f"{sheet} (no scouting rows found)")
            continue

        day = fs.sheet_label_to_date(sheet)
        if day is not None:
            target = fs.scout_path(fs.season_of(day), day)
        elif any(h in sheet.lower() for h in SEASON_TOTAL_HINTS):
            target = fs.scout_path(season, None)
        else:
            skipped.append(f"{sheet} (name isn't a YY-MM-DD date or a season total)")
            continue

        buf = pd.ExcelWriter(target, engine="openpyxl")
        with buf:
            raw.to_excel(buf, header=False, index=False)
        written.append(f"{target.name} ({len(rows)} rows)")

    for s in skipped:
        st.warning(f"Skipped {s}")
    if written:
        st.success("Saved: " + ", ".join(written))
        _refresh()


def _handle_wellness_upload(uploaded, season: str):
    """Split each recognised sheet by day, one file per day and kind --
    so a workbook holding a single day writes a single file, and one
    holding a week writes a file per day without any special casing."""
    try:
        xl = pd.ExcelFile(uploaded)
    except Exception as e:
        st.error(f"Couldn't open this as an Excel workbook: {e}")
        return

    written, skipped = 0, []
    for sheet in xl.sheet_names:
        kind = WELLNESS_SHEET_KINDS.get(sheet)
        if kind is None:
            skipped.append(f"{sheet} (expected one of: {', '.join(WELLNESS_SHEET_KINDS)})")
            continue

        df = xl.parse(sheet)
        if "Data" not in df.columns:
            skipped.append(f"{sheet} (no 'Data' column)")
            continue

        df["_day"] = pd.to_datetime(df["Data"], errors="coerce")
        undated = int(df["_day"].isna().sum())
        if undated:
            skipped.append(f"{undated} row(s) in {sheet} with an unreadable date")
        df = df.dropna(subset=["_day"])

        for day, group in df.groupby(df["_day"].dt.date):
            target = fs.wellness_path(fs.season_of(day), kind, day)
            target.parent.mkdir(parents=True, exist_ok=True)
            group.drop(columns=["_day"]).to_excel(target, sheet_name=sheet, index=False)
            written += 1

    for s in skipped:
        st.warning(f"Skipped {s}")
    if written:
        st.success(f"Saved {written} day file(s).")
        _refresh()


def render():
    st.caption(
        "Everything the app reads lives in files/, one file per sheet: a scout file is a single "
        "match, a wellness file is one day of one kind (RPE, TQR or jumps). Upload to add, ✕ to "
        "remove — removed files move to files/_archive/ rather than being deleted."
    )

    seasons = sorted(set(mc.SEASONS) | set(fs.seasons_on_disk()), reverse=True)
    # Default to the most recent season that actually holds files, so the
    # page doesn't open on an empty list when a later season exists in the
    # calendar but has no data yet.
    with_files = [s for s in seasons if fs.list_scout(s) or fs.list_wellness(s)]
    default_index = seasons.index(with_files[0]) if with_files else 0
    season = st.selectbox(
        "Season", seasons, index=default_index, key="entry_season",
        help="Which season's files to show. Uploads are filed by each sheet's own date; "
             "this picker only decides where an undated season-total sheet goes.",
    )

    col_scout, col_wellness = st.columns(2)

    with col_scout:
        with st.container(border=True):
            st.markdown("**Scout files** · one per match")
            up = st.file_uploader(
                "Scouting workbook (.xlsx)", type=["xlsx"], key="scout_upload",
                help="Data Volley layout: Fondam. / Palla / Giocatore in the first three columns. "
                     "Sheet named YY-MM-DD for a match, or 'TOTALE ...' for the season aggregate.",
            )
            if up is not None:
                _handle_scout_upload(up, season)

            entries = fs.list_scout(season)
            st.caption(f"{len(entries)} file(s) in {season}")
            _render_history(entries, "No scout files for this season yet.", "rm_scout")

    with col_wellness:
        with st.container(border=True):
            st.markdown("**Wellness / load files** · one per day and kind")
            up = st.file_uploader(
                "Wellness workbook (.xlsx)", type=["xlsx"], key="wellness_upload",
                help="Sheets named " + ", ".join(f"'{s}'" for s in WELLNESS_SHEET_KINDS)
                     + ". One, two or all three — whatever exists for that day.",
            )
            if up is not None:
                _handle_wellness_upload(up, season)

            entries = fs.list_wellness(season)
            st.caption(f"{len(entries)} file(s) in {season}")
            _render_history(entries, "No wellness files for this season yet.", "rm_well")
