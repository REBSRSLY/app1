"""Split the two source workbooks into the per-sheet files/ repository.

Run once to seed files/ from anonymized_matches_F.xlsx and
anonymized_wellness_file.xlsx; kept in the repo so the split is
reproducible and its rules are readable rather than folklore.

    python tools/seed_files.py [--force]

Each match sheet becomes files/<season>/scout/match_<date>.xlsx, written
back with header=None/index=False so it is byte-for-byte the same grid
the parser already expects. Each wellness sheet is sliced by day into
files/<season>/wellness/<kind>_<date>.xlsx, keeping the sheet's own name
inside the file so a seeded file is indistinguishable from one the staff
upload themselves.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import file_store as fs  # noqa: E402

MATCHES_FILE = Path("anonymized_matches_F.xlsx")
WELLNESS_FILE = Path("anonymized_wellness_file.xlsx")
SEASON_TOTAL_SHEET = "TOTALE 23-24"

# Source sheet -> the wellness kind it holds. The male-team sheets in the
# same workbook are deliberately not seeded: nothing in the app reads them.
WELLNESS_SOURCE_SHEETS = {
    "Rpe TL F": "rpe",
    "Wellness F": "tqr",
    "SALTI_F": "jumps",
}


def seed_scout(force: bool) -> int:
    xl = pd.ExcelFile(MATCHES_FILE)
    written = 0
    for sheet in xl.sheet_names:
        raw = xl.parse(sheet, header=None)
        if sheet == SEASON_TOTAL_SHEET:
            # The aggregate sheet has no date of its own; it belongs to the
            # season its own name carries.
            season, day = "2023-24", None
        else:
            day = fs.sheet_label_to_date(sheet)
            if day is None:
                print(f"  ! skipping unrecognised sheet name: {sheet}")
                continue
            season = fs.season_of(day)

        path = fs.scout_path(season, day)
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        raw.to_excel(path, header=False, index=False)
        written += 1
    return written


def seed_wellness(force: bool) -> int:
    xl = pd.ExcelFile(WELLNESS_FILE)
    written = 0
    for sheet, kind in WELLNESS_SOURCE_SHEETS.items():
        df = xl.parse(sheet)
        df["_day"] = pd.to_datetime(df["Data"], errors="coerce")
        unparsed = int(df["_day"].isna().sum())
        if unparsed:
            print(f"  ! {sheet}: {unparsed} rows with an unreadable date, skipped")
        df = df.dropna(subset=["_day"])

        for day_ts, group in df.groupby(df["_day"].dt.date):
            day: dt.date = day_ts
            path = fs.wellness_path(fs.season_of(day), kind, day)
            if path.exists() and not force:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            group.drop(columns=["_day"]).to_excel(path, sheet_name=sheet, index=False)
            written += 1
    return written


def seed_anagrafica(force: bool) -> bool:
    if fs.ANAGRAFICA_FILE.exists() and not force:
        return False
    fs.ANAGRAFICA_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.read_excel(WELLNESS_FILE, sheet_name="Anagrafica").to_excel(
        fs.ANAGRAFICA_FILE, sheet_name="Anagrafica", index=False
    )
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="overwrite files that already exist")
    ap.add_argument("--clean", action="store_true", help="wipe files/ first (keeps _archive)")
    args = ap.parse_args()

    if args.clean:
        for season in fs.seasons_on_disk():
            shutil.rmtree(fs.FILES_DIR / season)
        print("cleaned existing season folders")

    print("roster:", "written" if seed_anagrafica(args.force) else "already present")
    print("scout files written:", seed_scout(args.force))
    print("wellness files written:", seed_wellness(args.force))

    for season in fs.seasons_on_disk():
        print(f"  {season}: {len(fs.list_scout(season))} scout, {len(fs.list_wellness(season))} wellness")


if __name__ == "__main__":
    main()
