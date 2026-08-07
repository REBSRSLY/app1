"""On-disk repository of the source files the app reads.

One file = one sheet. A scout file is a single match's Data Volley sheet
(plus one season-total file per season); a wellness file is a single day
of a single kind (RPE, TQR or jumps), because that's how the staff
actually produce them -- one export per day, sometimes only one or two of
the three kinds for a given day.

Everything lives under files/<season>/, so which season a file belongs to
is simply where it sits, and the Data Entry page can list, add and
archive files without any of the loaders needing to know. Removing a file
moves it under files/_archive/ rather than deleting it, so a mistaken
removal is recoverable from disk.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

FILES_DIR = Path("files")
ARCHIVE_DIR = FILES_DIR / "_archive"
ANAGRAFICA_FILE = FILES_DIR / "anagrafica.xlsx"

# Filename stem of the season-aggregate scout sheet (the source workbook's
# own "TOTALE 23-24"), kept as its own file rather than recomputed: the
# app reads those aggregate rows directly for season-wide stats.
SEASON_TOTAL_STEM = "season-total"

# Wellness kind -> (display label, the sheet name the staff's own exports
# use for it). The sheet name is how an uploaded workbook is recognised.
WELLNESS_KINDS = {
    "rpe": ("RPE / load", "Rpe TL F"),
    "tqr": ("Wellness (TQR)", "Wellness F"),
    "jumps": ("Jumps", "SALTI_F"),
}

_MATCH_RE = re.compile(r"^match_(\d{4}-\d{2}-\d{2})$")
_WELLNESS_RE = re.compile(r"^(rpe|tqr|jumps)_(\d{4}-\d{2}-\d{2})$")


def season_of(day: dt.date) -> str:
    """Season a date belongs to, running 1 Aug -> 31 Jul ("2023-24")."""
    start_year = day.year if day.month >= 8 else day.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def sheet_label_to_date(label: str) -> dt.date | None:
    """"23-10-08" (the scout sheets' own YY-MM-DD names) -> a real date."""
    try:
        return dt.datetime.strptime(label, "%y-%m-%d").date()
    except ValueError:
        return None


def date_to_sheet_label(day: dt.date) -> str:
    """Inverse of sheet_label_to_date -- the match key the rest of the app
    uses (match_calendar, filters, every scout chart)."""
    return day.strftime("%y-%m-%d")


def scout_dir(season: str) -> Path:
    return FILES_DIR / season / "scout"


def wellness_dir(season: str) -> Path:
    return FILES_DIR / season / "wellness"


def seasons_on_disk() -> list[str]:
    if not FILES_DIR.exists():
        return []
    return sorted(
        p.name for p in FILES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def list_scout(season: str) -> list[dict]:
    """Scout files for a season, most recent match first, season total last."""
    out: list[dict] = []
    for path in sorted(scout_dir(season).glob("*.xlsx")):
        if path.stem == SEASON_TOTAL_STEM:
            out.append({"path": path, "kind": "season_total", "label": "Season total", "date": None})
            continue
        m = _MATCH_RE.match(path.stem)
        if not m:
            continue
        day = dt.date.fromisoformat(m.group(1))
        out.append({"path": path, "kind": "match", "label": "Match", "date": day})
    out.sort(key=lambda f: (f["date"] is None, f["date"] or dt.date.min), reverse=True)
    return out


def list_wellness(season: str) -> list[dict]:
    """Wellness files for a season, most recent day first."""
    out: list[dict] = []
    for path in sorted(wellness_dir(season).glob("*.xlsx")):
        m = _WELLNESS_RE.match(path.stem)
        if not m:
            continue
        kind, iso = m.group(1), m.group(2)
        out.append({
            "path": path,
            "kind": kind,
            "label": WELLNESS_KINDS[kind][0],
            "date": dt.date.fromisoformat(iso),
        })
    out.sort(key=lambda f: (f["date"], f["kind"]), reverse=True)
    return out


def scout_path(season: str, day: dt.date | None) -> Path:
    """Target path for a match's scout sheet (day=None -> season total)."""
    stem = SEASON_TOTAL_STEM if day is None else f"match_{day.isoformat()}"
    return scout_dir(season) / f"{stem}.xlsx"


def wellness_path(season: str, kind: str, day: dt.date) -> Path:
    return wellness_dir(season) / f"{kind}_{day.isoformat()}.xlsx"


def write_bytes(path: Path, data: bytes) -> Path:
    """Save a file, creating its season folder if this is the first one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def archive(path: Path) -> Path:
    """Move a file out of the app's view, keeping it on disk under
    files/_archive/<same relative path> so it can be restored by hand. A
    name already taken there gets a numeric suffix rather than being
    overwritten -- re-uploading and re-removing the same day shouldn't
    silently destroy the earlier copy."""
    path = Path(path)
    relative = path.relative_to(FILES_DIR)
    target = ARCHIVE_DIR / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        n = 2
        while (candidate := target.with_name(f"{target.stem}_{n}{target.suffix}")).exists():
            n += 1
        target = candidate
    shutil.move(str(path), str(target))
    return target
