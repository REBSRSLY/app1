"""Data Entry: the files the app is currently reading, and how to add to them.

One file = one sheet. A scout file is a single match (or a season-total
sheet); a wellness file is one day of one kind, since that's how the staff
export them -- often only one or two of RPE / TQR / jumps exist for a
given day. Uploading writes into files/ and removing moves the file to
files/_archive/, and either way the loaders pick the change up on the next
rerun (data_loader.source_signature keys every cache on the file set).

One uploader takes everything: each workbook is inspected sheet by sheet
and routed by what it actually contains, rather than asking the staff to
pick the right box first.
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

ENTRY_CSS = """
<style>
    /* Remove buttons: outlined in the campaign magenta rather than the
       default grey, so the one destructive control on the page reads as
       one at a glance. */
    [class*="st-key-rm_"] button {
        border: 1.5px solid var(--accent-3) !important;
        color: var(--accent-3) !important;
        background: transparent !important;
        padding: 0 !important;
        min-height: 28px !important;
        height: 28px !important;
        font-weight: 700;
    }
    [class*="st-key-rm_"] button:hover {
        background: rgba(224, 21, 140, 0.16) !important;
        border-color: var(--accent-3) !important;
        color: var(--accent-3) !important;
    }
</style>
"""


def _refresh():
    """Every loader is keyed on the file set, but the small name/role
    lookups are cached without that key -- clearing wholesale is simpler
    than reasoning about which ones survive a file change."""
    st.cache_data.clear()
    st.rerun()


def _validate_score(score: str) -> str | None:
    """None if `score` is a legal best-of-5 volleyball result ("3-1"),
    otherwise an error message. Matches match_calendar.result_points'
    own assumption (winner always has exactly 3 sets) rather than
    accepting anything that merely looks like two numbers."""
    parts = score.split("-")
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        return "Score must look like \"3-1\" (Milano's sets first)."
    us, opp = int(parts[0]), int(parts[1])
    if not ((us == 3 and 0 <= opp <= 2) or (opp == 3 and 0 <= us <= 2)):
        return "Not a legal best-of-5 score (one side must reach exactly 3)."
    return None


def _build_match_entry(day: dt.date, opponent: str, competition: str, round_: str, venue: str, score: str) -> tuple[dict | None, str | None]:
    """(entry, error) -- error is set (and entry is None) if validation
    fails. Shared between the standalone Match details form and the
    upload-triggered dialog below so the two can't validate differently."""
    if not opponent.strip():
        return None, "Opponent is required."
    error = _validate_score(score.strip())
    if error:
        return None, error
    entry = {
        "date": fs.date_to_sheet_label(day),
        "competition": competition,
        "round": round_.strip(),
        "opponent": opponent.strip(),
        "home": venue == "Home",
        "score": score.strip(),
    }
    return entry, None


def _matches_missing_details() -> list[tuple[str, dt.date]]:
    """(season, date) for every uploaded scout match file whose date has
    no name attached yet -- no built-in 2023/24 record, and nothing saved
    through Data Entry either. Scans every season actually on disk, not
    just whichever one happens to be selected in the dropdown below: a
    just-uploaded match files itself by its own date's season
    (file_store.season_of), which isn't necessarily the one showing."""
    missing = []
    for season in fs.seasons_on_disk():
        for entry in fs.list_scout(season):
            if entry["kind"] != "match":
                continue
            if mc.match_by_date(fs.date_to_sheet_label(entry["date"])) is None:
                missing.append((season, entry["date"]))
    return missing


@st.dialog("Match details required", dismissible=False)
def _match_details_dialog(season: str, day: dt.date):
    """Blocking pop-up (dismissible=False -- no X, no click-outside-to-
    close) for a match that was just uploaded but has no opponent/
    competition/score yet: every other screen that names a match
    (Matches, the sidebar's Match picker, Scout Sheet) reads that context
    from here, not from the scout file itself, so an unnamed match
    reads as blank everywhere until this is filled in."""
    st.caption(
        f"A scout file for **{day.strftime('%d %B %Y')}** was uploaded, but this match has no "
        "opponent, competition or score yet. Fill it in to continue."
    )
    with st.form("match_details_dialog_form"):
        opponent = st.text_input("Opponent", key="dlg_match_opponent")
        competition = st.selectbox("Competition", mc.COMPETITION_ORDER, key="dlg_match_competition")
        col_round, col_home, col_score = st.columns([1, 1, 1])
        with col_round:
            round_ = st.text_input(
                "Round", key="dlg_match_round",
                help="Free text, e.g. \"andata\"/\"ritorno\"/\"girone\" — leave blank if it doesn't apply.",
            )
        with col_home:
            venue = st.radio("Venue", ["Home", "Away"], key="dlg_match_venue", horizontal=True)
        with col_score:
            score = st.text_input("Score", key="dlg_match_score", placeholder="3-1", help="Milano's sets first.")

        if st.form_submit_button("Save match"):
            entry, error = _build_match_entry(day, opponent, competition, round_, venue, score)
            if error:
                st.error(error)
            else:
                fs.save_match_entry(season, entry)
                _refresh()


def _render_match_details(season: str):
    """Opponent, competition and score for a match live in match_calendar's
    built-in history for 2023/24, but nowhere for any season entered
    through this page -- without this, an uploaded scout sheet for a new
    match shows up on the Matches page and the sidebar's own Match picker
    with no name attached to it. One form to add or correct a match
    (saving again on the same date overwrites that entry, so filling in
    the score after the built-in "Serie A1" placeholder is just an edit),
    and the list below it to remove one. A match with no details at all
    is instead caught by the mandatory dialog above, right after upload --
    this form is for editing/correcting afterwards, or for backfilling
    matches that predate a scout file (fixtures not yet played, say)."""
    with st.container(border=True):
        st.markdown("**Match details** · opponent, competition, score")
        st.caption(
            "Attaches the details a scout file's own filename can't carry (just its date). "
            "Saving again on a date that's already here replaces that entry."
        )
        with st.form("match_entry_form", clear_on_submit=False):
            col_date, col_opp, col_comp = st.columns([1, 1.4, 1.2])
            with col_date:
                day = st.date_input("Date", key="match_entry_date")
            with col_opp:
                opponent = st.text_input("Opponent", key="match_entry_opponent")
            with col_comp:
                competition = st.selectbox(
                    "Competition", mc.COMPETITION_ORDER, key="match_entry_competition",
                )
            col_round, col_home, col_score = st.columns([1, 1, 1])
            with col_round:
                round_ = st.text_input(
                    "Round", key="match_entry_round",
                    help="Free text, e.g. \"andata\"/\"ritorno\"/\"girone\" — leave blank if it doesn't apply.",
                )
            with col_home:
                venue = st.radio("Venue", ["Home", "Away"], key="match_entry_venue", horizontal=True)
            with col_score:
                score = st.text_input("Score", key="match_entry_score", placeholder="3-1", help="Milano's sets first.")

            if st.form_submit_button("Save match"):
                entry, error = _build_match_entry(day, opponent, competition, round_, venue, score)
                if error:
                    st.error(error)
                else:
                    fs.save_match_entry(fs.season_of(day), entry)
                    st.success(f"Saved {entry['opponent']} · {entry['date']}")
                    _refresh()

        entries = fs.list_match_entries(season)
        if entries:
            st.caption(f"{len(entries)} match(es) entered for {season}:")
            for entry in entries:
                col_info, col_x = st.columns([5, 1], vertical_alignment="center")
                with col_info:
                    venue_txt = "Home" if entry["home"] else "Away"
                    st.markdown(
                        f'<span style="font-size:0.85rem;">{entry["date"]} · <b>{entry["opponent"]}</b> '
                        f'· {entry["competition"]} · {venue_txt} · {entry["score"]}</span>',
                        unsafe_allow_html=True,
                    )
                with col_x:
                    if st.button("✕", key=f"rm_match_{entry['date']}", help="Remove this match entry"):
                        fs.remove_match_entry(season, entry["date"])
                        _refresh()


def _fmt_date(day: dt.date | None) -> str:
    return day.strftime("%d %b %Y") if day else "Season total"


def _render_column(title: str, entries: list[dict], empty_msg: str):
    """One type per column: the header already names the kind, so each row
    only needs its date and the remove button."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(f"{len(entries)} file(s)")
        if not entries:
            st.caption(empty_msg)
            return
        # Scrollable: a full season is hundreds of days, which would
        # otherwise push everything else off the page.
        with st.container(height=300):
            for entry in entries:
                col_date, col_x = st.columns([3, 1], vertical_alignment="center")
                with col_date:
                    st.markdown(
                        f'<span style="font-size:0.85rem;">{_fmt_date(entry["date"])}</span>',
                        unsafe_allow_html=True,
                    )
                with col_x:
                    if st.button("✕", key=f"rm_{entry['path'].name}", help="Remove from the app"):
                        fs.archive(entry["path"])
                        _refresh()


def _route_scout_sheet(raw: pd.DataFrame, sheet: str, season: str) -> tuple[str, str]:
    """(status, detail) for one sheet of a scouting workbook. Match sheets
    are filed by their own date -- a sheet dated last season belongs to
    last season, whatever the picker says -- and only the undated
    season-total sheet follows the picker."""
    # The parser assumes the Data Volley grid (it indexes column 2 directly),
    # so anything narrower or otherwise unexpected raises rather than
    # returning nothing. Uploads are exactly where such a sheet arrives, so
    # a bad sheet has to come back as a skip, not take the page down.
    try:
        rows = dl.parse_scout_sheet(raw, sheet)
    except Exception:
        return "skip", f"'{sheet}': not a recognisable scouting sheet"
    if not rows:
        return "skip", f"'{sheet}': no scouting rows found"

    day = fs.sheet_label_to_date(sheet)
    if day is not None:
        target = fs.scout_path(fs.season_of(day), day)
    elif any(h in sheet.lower() for h in SEASON_TOTAL_HINTS):
        target = fs.scout_path(season, None)
    else:
        return "skip", f"'{sheet}': name is neither a YY-MM-DD date nor a season total"

    target.parent.mkdir(parents=True, exist_ok=True)
    # sheet_name=sheet: preserves the uploaded sheet's own name (a date, or
    # the season-total label) instead of defaulting to "Sheet1" -- without
    # this, re-uploading this exact file later (or anything else that
    # legitimately still has "Sheet1" as its tab) would silently stop
    # being recognised, since routing above depends entirely on the sheet
    # name, not the file's.
    raw.to_excel(target, sheet_name=sheet, header=False, index=False)
    return "ok", f"{target.name} ({len(rows)} rows)"


def _route_wellness_sheet(df: pd.DataFrame, sheet: str, kind: str) -> tuple[int, list[str]]:
    """Split one wellness sheet by day, one file per day -- so a workbook
    holding a single day writes a single file, and one holding a week
    writes a file per day without any special casing."""
    if "Data" not in df.columns:
        return 0, [f"'{sheet}': no 'Data' column"]

    notes: list[str] = []
    df = df.copy()
    df["_day"] = pd.to_datetime(df["Data"], errors="coerce")
    undated = int(df["_day"].isna().sum())
    if undated:
        notes.append(f"'{sheet}': {undated} row(s) with an unreadable date")
    df = df.dropna(subset=["_day"])

    written = 0
    for day, group in df.groupby(df["_day"].dt.date):
        target = fs.wellness_path(fs.season_of(day), kind, day)
        target.parent.mkdir(parents=True, exist_ok=True)
        group.drop(columns=["_day"]).to_excel(target, sheet_name=sheet, index=False)
        written += 1
    return written, notes


def _handle_uploads(uploaded_files, season: str):
    """Inspect each workbook sheet by sheet and send it wherever it
    belongs: a recognised wellness sheet name makes it wellness data, a
    date-named (or season-total) sheet makes it scouting."""
    saved: list[str] = []
    notes: list[str] = []

    for uploaded in uploaded_files:
        try:
            xl = pd.ExcelFile(uploaded)
        except Exception as e:
            notes.append(f"{uploaded.name}: couldn't open as an Excel workbook ({e})")
            continue

        for sheet in xl.sheet_names:
            kind = WELLNESS_SHEET_KINDS.get(sheet)
            if kind is not None:
                written, sheet_notes = _route_wellness_sheet(xl.parse(sheet), sheet, kind)
                notes.extend(f"{uploaded.name} — {n}" for n in sheet_notes)
                if written:
                    saved.append(f"{fs.WELLNESS_KINDS[kind][0]}: {written} day file(s)")
                continue

            status, detail = _route_scout_sheet(xl.parse(sheet, header=None), sheet, season)
            if status == "ok":
                saved.append(detail)
            else:
                notes.append(f"{uploaded.name} — {detail}")

    for n in notes:
        st.warning(f"Skipped {n}")
    if saved:
        st.success("Saved · " + " · ".join(saved))
        _refresh()


def render():
    st.markdown(ENTRY_CSS, unsafe_allow_html=True)

    # Checked on every visit, not just right after an upload -- a match
    # left unnamed in an earlier session should keep blocking here until
    # it's resolved, not just once. Only ever one at a time; the next
    # missing match (if any) is picked up on the rerun this dialog
    # triggers when the current one is saved.
    missing = _matches_missing_details()
    if missing:
        _match_details_dialog(*missing[0])

    st.caption(
        "Everything the app reads lives in files/, one file per sheet: a scout file is a single "
        "match, a wellness file is one day of one kind. Drop any mix of workbooks below — each "
        "sheet is routed by what it contains. ✕ removes a file from the app (it moves to "
        "files/_archive/ rather than being deleted)."
    )

    seasons = sorted(set(mc.SEASONS) | set(fs.seasons_on_disk()), reverse=True)
    # Default to the most recent season that actually holds files, so the
    # page doesn't open on an empty list when a later season exists in the
    # calendar but has no data yet.
    with_files = [s for s in seasons if fs.list_scout(s) or fs.list_wellness(s)]
    default_index = seasons.index(with_files[0]) if with_files else 0

    with st.container(border=True):
        st.markdown("**Upload files**")
        col_up, col_season = st.columns([3, 1])
        with col_up:
            uploaded = st.file_uploader(
                "Workbooks (.xlsx)", type=["xlsx"], accept_multiple_files=True, key="entry_upload",
                help="Scouting workbooks (sheets named YY-MM-DD, or 'TOTALE ...') and wellness "
                     "workbooks (sheets named " + ", ".join(f"'{s}'" for s in WELLNESS_SHEET_KINDS)
                     + ") can be dropped together — each sheet is routed by what it holds.",
            )
        with col_season:
            season = st.selectbox(
                "Season", seasons, index=default_index, key="entry_season",
                help="Which season's files are listed below. Uploads are filed by each sheet's "
                     "own date; this only decides where an undated season-total sheet goes.",
            )
        if uploaded:
            _handle_uploads(uploaded, season)

    _render_match_details(season)

    scout = fs.list_scout(season)
    wellness = fs.list_wellness(season)

    col_match, col_tqr, col_rpe, col_jumps = st.columns(4)
    with col_match:
        _render_column("Match", scout, "No scout files for this season yet.")
    with col_tqr:
        _render_column("Wellness (TQR)", [e for e in wellness if e["kind"] == "tqr"], "None yet.")
    with col_rpe:
        _render_column("RPE / load", [e for e in wellness if e["kind"] == "rpe"], "None yet.")
    with col_jumps:
        _render_column("Jumps", [e for e in wellness if e["kind"] == "jumps"], "None yet.")
