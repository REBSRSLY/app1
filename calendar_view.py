"""Competition boxes + standings table for the Matches page.

Plain HTML/CSS (no extra dependency), styled to match the app's dark theme
(styles.py CSS variables) rather than introducing a second design language.
"""

from __future__ import annotations

import match_calendar as mc

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Same win-margin colour scale everywhere a result is shown (box rows,
# standings "last 5" dots): 3pt = clear win, 2pt = tie-break win,
# 1pt = tie-break loss, 0pt = clear loss.
RESULT_COLORS = {3: "#2E7D32", 2: "#8BC34A", 1: "#FFA726", 0: "#E53935"}

# ---------------------------------------------------------------------------
# Per-competition boxes
# ---------------------------------------------------------------------------

BOX_CSS = """
<style>
    .comp-box {
        border: 2px solid var(--box-accent, var(--accent));
        border-radius: 12px;
        background: var(--surface);
        padding: 14px 16px 12px;
        margin-bottom: 12px;
        box-sizing: border-box;
    }
    .comp-box-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; gap:10px; }
    .comp-box-title { font-size:1.05rem; font-weight:700; color:var(--box-accent, var(--accent)); }
    .comp-box-record {
        font-size:11.5px; color:var(--muted); background:rgba(255,255,255,0.05);
        border:1px solid var(--line); border-radius:20px; padding:3px 10px; white-space:nowrap;
    }
    /* Sized to roughly match the standings box's own natural height (14
       teams + header lands around ~600px) -- matches contained here are
       sorted most-recent-first (see render_competition_box), so whatever's
       most relevant right now, wins or losses, is what's visible without
       scrolling, not whatever happened to be scrolled to. */
    .comp-results { height:520px; overflow-y:auto; padding-right:6px; }
    .result-row { padding:8px 2px; border-bottom:1px solid var(--line); }
    .result-row:last-child { border-bottom:none; }
    .result-top { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:3px; }
    .result-opponent { font-weight:700; font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .result-score { font-weight:700; font-size:12.5px; flex-shrink:0; border-radius:6px; padding:2px 9px; }
    .result-bottom { display:flex; align-items:center; gap:9px; font-size:11px; color:var(--muted); white-space:nowrap; }
    .result-date { font-variant-numeric: tabular-nums; flex-shrink:0; }
    .result-venue { text-transform:uppercase; letter-spacing:0.04em; flex-shrink:0; }
    .result-round { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .comp-empty { color:var(--muted); font-size:12.5px; padding:8px 0; }
</style>
"""


def fmt_date(sheet_date: str) -> str:
    """'23-10-08' -> '08/10/23' (dd/mm/yy)."""
    yy, mm, dd = sheet_date.split("-")
    return f"{dd}/{mm}/{yy}"


def _result_row_html(m: dict, show_round: bool) -> str:
    color = RESULT_COLORS[mc.result_points(m)]
    venue = "Home" if m["home"] else "Away"
    round_html = f'<div class="result-round">· {mc.round_label(m["round"])}</div>' if show_round else ""
    # Two lines instead of five columns crammed into one row: the opponent
    # name and score (the two things worth reading at a glance) get their
    # own larger, uncontested line; date/venue/round move to a smaller
    # muted line below instead of fighting them for horizontal space.
    return (
        '<div class="result-row">'
        f'<div class="result-top">'
        f'<div class="result-opponent">{m["opponent"]}</div>'
        f'<div class="result-score" style="color:{color};background:{color}26;">{m["score"]}</div>'
        f'</div>'
        f'<div class="result-bottom">'
        f'<div class="result-date">{fmt_date(m["date"])}</div>'
        f'<div class="result-venue">{venue}</div>'
        f'{round_html}'
        f'</div>'
        '</div>'
    )


def render_box(title: str, color: str, body_html: str, record_html: str = "") -> str:
    """Generic color-bordered card (title colored to match, like the Players
    page's role boxes) with an optional record chip and a body."""
    return (
        f'<div class="comp-box" style="--box-accent:{color}">'
        f'<div class="comp-box-header">'
        f'<div class="comp-box-title">{title}</div>'
        f'{record_html}'
        f'</div>'
        f'{body_html}'
        f'</div>'
    )


def render_competition_box(comp_key: str, matches: list[dict], show_round: bool = True) -> str:
    """Self-contained box: header (name, W-L record) + scrollable results
    list, most recent match first -- the box has a capped height (roughly
    matching the standings box next to it) and scrolls for competitions
    with a lot of matches, so whatever's most recent (a loss included)
    is what's visible by default, not whatever's oldest."""
    conf = mc.COMPETITIONS[comp_key]
    comp_matches = sorted((m for m in matches if m["competition"] == comp_key), key=lambda m: m["date"], reverse=True)

    if not comp_matches:
        return render_box(comp_key, conf["color"], '<div class="comp-empty">No matches yet.</div>')

    wins = sum(1 for m in comp_matches if mc.is_win(m))
    losses = len(comp_matches) - wins
    record_html = f'<div class="comp-box-record">{wins}W – {losses}L · {len(comp_matches)} played</div>'
    rows = "".join(_result_row_html(m, show_round) for m in comp_matches)
    body = f'<div class="comp-results">{rows}</div>'
    return render_box(comp_key, conf["color"], body, record_html)


def render_standings_box(standings: list[dict], title: str = "Standings", color: str = "#4C78A8") -> str:
    # No max-height/scroll here (unlike comp-results): the standings table
    # is meant to be fully visible at a glance, not truncated.
    return render_box(title, color, render_standings(standings))


# ---------------------------------------------------------------------------
# Standings table
# ---------------------------------------------------------------------------

STANDINGS_CSS = """
<style>
    .std-table { width:100%; border-collapse:collapse; font-size:13px; }
    .std-table th { text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:0.05em;
        color:var(--muted); font-weight:600; padding:6px 7px; border-bottom:1px solid var(--line); }
    .std-table td { padding:6px 7px; border-bottom:1px solid var(--line); }
    .std-table tr.std-us { background-color:var(--accent-bg); }
    .std-table tr.std-us td { color:var(--accent); font-weight:700; }
    .std-pos { color:var(--muted); width:22px; }
    .std-dots { display:flex; gap:3px; }
    .std-dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
</style>
"""


def render_standings(standings: list[dict]) -> str:
    if not standings:
        return '<div class="comp-empty">No standings yet.</div>'

    rows = []
    for row in standings:
        cls = "std-us" if row["is_us"] else ""
        dots = "".join(
            f'<span class="std-dot" style="background:{RESULT_COLORS[p]}"></span>'
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
