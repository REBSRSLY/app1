"""Month-grid calendar + standings table renderers for the Matches page.

Plain HTML/CSS (no extra dependency), styled to match the app's dark theme
(styles.py CSS variables) rather than introducing a second design language.
"""

from __future__ import annotations

import calendar as _calendar

import match_calendar as mc

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

CALENDAR_CSS = """
<style>
    .cal-legend { display:flex; flex-wrap:wrap; gap:14px; margin-bottom:14px; font-size:12.5px; color:var(--muted); }
    .cal-legend-item { display:flex; align-items:center; gap:6px; }
    .cal-legend-swatch { width:10px; height:10px; border-radius:3px; display:inline-block; }
    .cal-grid { display:grid; grid-template-columns: repeat(7, 1fr); gap:6px; margin-bottom:4px; }
    .cal-weekday { text-align:center; font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.04em; padding-bottom:6px; }
    .cal-day { border:1px solid var(--line); border-radius:8px; min-height:92px; padding:6px; background:var(--surface); }
    .cal-day.cal-empty { border:none; background:transparent; }
    .cal-daynum { font-size:12px; color:var(--muted); margin-bottom:5px; font-weight:600; }
    .cal-event { font-size:10.5px; line-height:1.3; border-radius:5px; padding:2px 5px; margin-bottom:3px; color:#ffffff; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .cal-jump-dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-top:2px; }
</style>
"""


def render_legend() -> str:
    items = "".join(
        f'<div class="cal-legend-item"><span class="cal-legend-swatch" '
        f'style="background:{c["color"]}"></span>{c["label"]}</div>'
        for c in mc.COMPETITIONS.values()
    )
    return f'<div class="cal-legend">{items}</div>'


def _events_for_month(year: int, month: int) -> dict[int, list[dict]]:
    events: dict[int, list[dict]] = {}
    for m in mc.matches_for_year(year):
        d = m["pdate"]
        if d.month != month:
            continue
        comp = mc.COMPETITIONS[m["competition"]]
        vs = f"{'vs' if m['home'] else '@'} {m['opponent']}"
        events.setdefault(d.day, []).append({
            "color": comp["color"],
            "title": f"{vs} {m['score']}",
        })
    return events


def _jump_days(year: int, month: int, salti_dates: list) -> set[int]:
    return {d.day for d in salti_dates if d.year == year and d.month == month}


def render_month_calendar(year: int, month: int, salti_dates: list) -> str:
    events = _events_for_month(year, month)
    jump_days = _jump_days(year, month, salti_dates)

    weeks = _calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    header = "".join(f'<div class="cal-weekday">{w}</div>' for w in WEEKDAY_NAMES)

    cells = []
    for week in weeks:
        for day in week:
            if day == 0:
                cells.append('<div class="cal-day cal-empty"></div>')
                continue
            pills = "".join(
                f'<div class="cal-event" style="background:{e["color"]}" title="{e["title"]}">{e["title"]}</div>'
                for e in events.get(day, [])
            )
            jump_dot = ""
            if day in jump_days:
                jump_dot = (
                    f'<span class="cal-jump-dot" style="background:{mc.COMPETITIONS["Jump session"]["color"]}" '
                    f'title="Jump session"></span>'
                )
            cells.append(f'<div class="cal-day"><div class="cal-daynum">{day} {jump_dot}</div>{pills}</div>')

    return f'<div class="cal-grid">{header}{"".join(cells)}</div>'


def months_with_data(year: int, salti_dates: list) -> list[int]:
    """Months (1-12) with at least one match or jump session in that year."""
    months = {m["pdate"].month for m in mc.matches_for_year(year)}
    months |= {d.month for d in salti_dates if d.year == year}
    return sorted(months)


STANDINGS_CSS = """
<style>
    .std-table { width:100%; border-collapse:collapse; font-size:13.5px; }
    .std-table th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.05em;
        color:var(--muted); font-weight:600; padding:6px 8px; border-bottom:1px solid var(--line); }
    .std-table td { padding:7px 8px; border-bottom:1px solid var(--line); }
    .std-table tr.std-us { background-color:var(--accent-bg); }
    .std-table tr.std-us td { color:var(--accent); font-weight:700; }
    .std-pos { color:var(--muted); width:26px; }
    .std-dots { display:flex; gap:4px; }
    .std-dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
</style>
"""

_LAST5_COLORS = {3: "#2E7D32", 2: "#8BC34A", 1: "#FFA726", 0: "#E53935"}


def render_standings(standings: list[dict]) -> str:
    rows = []
    for row in standings:
        cls = "std-us" if row["is_us"] else ""
        dots = "".join(
            f'<span class="std-dot" style="background:{_LAST5_COLORS[p]}"></span>'
            for p in row["last5"]
        )
        rows.append(
            f'<tr class="{cls}">'
            f'<td class="std-pos">{row["pos"]}</td>'
            f'<td>{row["team"]}</td>'
            f'<td>{row["pts"]}</td>'
            f'<td>{row["p"]}</td>'
            f'<td>{row["w"]}</td>'
            f'<td>{row["l"]}</td>'
            f'<td>{row["sf"]}</td>'
            f'<td>{row["sa"]}</td>'
            f'<td>{row["sf"] - row["sa"]:+d}</td>'
            f'<td><div class="std-dots">{dots}</div></td>'
            f'</tr>'
        )
    return (
        f'{STANDINGS_CSS}<table class="std-table"><thead><tr>'
        f'<th></th><th>Team</th><th>Pts</th><th>P</th><th>W</th><th>L</th>'
        f'<th>Sets W</th><th>Sets L</th><th>+/-</th><th>Last 5</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )
