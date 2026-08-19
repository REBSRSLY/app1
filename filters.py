"""Global season/competition/period filters, shared across pages.

Before this module, every page had its own date-range picker (with its own
default window) and its own "Match" selectbox, with zero communication
between screens. This is the single source of truth instead: the sidebar
tools panel (built in Main_activity.py) edits this state, and every page
reads it back via the helpers below, so picking a period or a competition
on one screen carries over to the next.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

import data_loader as dl
import match_calendar as mc

ALL_COMPETITIONS = "All competitions"
ALL_MATCHES = "All matches (use dates below)"

# Quick-period presets, in days back from the season's last match. "Full
# season" isn't a day count -- it's handled separately as "span everything".
PRESETS = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}


def _season_bounds(season: str) -> tuple[dt.date, dt.date]:
    """Full date range for the season, spanning both match days and
    training-log days -- pre-season conditioning starts weeks before the
    first match, so bounding this to match dates alone (as the app used to)
    would silently hide that early wellness/RPE data from the pickers."""
    matches = mc.matches_for_season(season)
    if not matches:
        today = dt.date.today()
        return today, today
    dates = [m["pdate"] for m in matches]

    wellness = dl.load_wellness_data()
    for df in wellness.values():
        if not df.empty:
            dates.append(df["Data"].min().date())
            dates.append(df["Data"].max().date())

    return min(dates), max(dates)


def init():
    """Set up default filter state once per session. Defaults to the whole
    season / all competitions, so nothing is hidden until the user actually
    narrows something down."""
    st.session_state.setdefault("flt_season", mc.SEASONS[0])
    st.session_state.setdefault("flt_competition", ALL_COMPETITIONS)
    st.session_state.setdefault("flt_match_pick", ALL_MATCHES)
    start, end = _season_bounds(st.session_state["flt_season"])
    st.session_state.setdefault("flt_start", start)
    st.session_state.setdefault("flt_end", end)
    st.session_state.setdefault("flt_has_end", True)


def season() -> str:
    return st.session_state["flt_season"]


def competition() -> str:
    return st.session_state["flt_competition"]


def period() -> tuple[dt.date, dt.date]:
    """(start, end) currently active. Collapses to a single day when the
    "different end date" toggle is off, and self-corrects if start > end."""
    start = st.session_state["flt_start"]
    end = st.session_state["flt_end"] if st.session_state["flt_has_end"] else start
    if end < start:
        start, end = end, start
    return start, end


def is_full_season() -> bool:
    """Whether the active period spans the entire season (e.g. right after
    the "Full season" preset), as opposed to a narrower custom range --
    pages that fall back to a single "which sheet to show" choice (like the
    raw scout sheet) use this to pick the season-aggregate sheet instead of
    a single match."""
    full_start, full_end = _season_bounds(season())
    return period() == (full_start, full_end)


def _matches_for_picker() -> list[dict]:
    """Season matches filtered by competition only (not period -- picking
    one of these from the sidebar is what sets the period), most recent
    first."""
    matches = mc.matches_for_season(season())
    comp = competition()
    if comp != ALL_COMPETITIONS:
        matches = [m for m in matches if m["competition"] == comp]
    return sorted(matches, key=lambda m: m["pdate"], reverse=True)


def matches_in_scope() -> list[dict]:
    """Season matches (with parsed `pdate`) filtered by the active period
    and competition, most recent first -- the shared source of truth for
    "which matches count right now" that every match-picking page uses."""
    start, end = period()
    matches = [m for m in mc.matches_for_season(season()) if start <= m["pdate"] <= end]
    comp = competition()
    if comp != ALL_COMPETITIONS:
        matches = [m for m in matches if m["competition"] == comp]
    return sorted(matches, key=lambda m: m["pdate"], reverse=True)


def match_options(*, include_season_total: bool = True) -> list[str]:
    """Match-sheet labels (date strings) in scope, for a "Match" selectbox --
    optionally with the season-total aggregate pinned first, since that's a
    legitimate "everything" view rather than a period-scoped one."""
    options = [m["date"] for m in matches_in_scope()]
    if include_season_total:
        options = [dl.SEASON_LABEL] + options
    return options


def ensure_valid_selection(key: str, options: list):
    """Narrowing the sidebar period/competition can drop the match a page
    had previously selected out of its options list -- st.selectbox errors
    if a key's persisted value isn't among the new options, so reset it
    before the widget renders instead of letting that happen."""
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state[key] = options[0] if options else None


def filter_by_date_col(df, date_col: str = "Data"):
    """Rows whose `date_col` falls within the active period (inclusive)."""
    start, end = period()
    return df[(df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)]


def caption() -> str:
    """One-line summary of what's currently active, e.g. for a page-top
    caption so the applied scope is never a surprise."""
    start, end = period()
    comp = competition()
    comp_txt = "" if comp == ALL_COMPETITIONS else f" · {comp}"
    when = start.strftime("%d %b %Y") if start == end else f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"
    return f"{season()}{comp_txt} · {when}"


def _apply_preset(days: int | None, target_season: str | None = None):
    start, end = _season_bounds(target_season or season())
    if days is None:
        st.session_state["flt_start"] = start
        st.session_state["flt_end"] = end
    else:
        st.session_state["flt_start"] = max(start, end - dt.timedelta(days=days - 1))
        st.session_state["flt_end"] = end
    st.session_state["flt_has_end"] = True
    # A date-range preset supersedes any single match picked from the
    # dropdown above -- clear it so the two controls don't show
    # contradictory state.
    st.session_state["flt_match_pick"] = ALL_MATCHES


def _on_season_change():
    """The period picker's min/max is season-bound; switching to a season
    with a different (or no) match range would otherwise leave the stored
    start/end outside the new bounds and make st.date_input raise."""
    _apply_preset(None, target_season=st.session_state["flt_season"])


def _apply_match_pick():
    """Picking a single match from the sidebar sets the period to exactly
    that match day (start = the match's date, no end) -- a shortcut next to
    the calendar pickers, not a replacement for them."""
    picked = st.session_state["flt_match_pick"]
    if picked == ALL_MATCHES:
        return
    match = mc.match_by_date(picked)
    if match is None:
        return
    match_date = mc.parsed_date(picked)
    st.session_state["flt_start"] = match_date
    st.session_state["flt_end"] = match_date
    st.session_state["flt_has_end"] = False


def _jump_year(state_key: str, year: int):
    """Set `state_key`'s stored date to the given year, same month/day --
    a one-click way to cross a year boundary. st.date_input's own calendar
    popup has no year shortcut of its own (no clickable header, just
    month-at-a-time arrows), so reaching, say, October from a March date a
    year apart otherwise means arrowing through every month in between.
    Clamped into the season's own bounds (day=28 fallback for a Feb 29
    that doesn't exist in the target year) so this can never push the
    stored date outside what st.date_input's min/max will accept."""
    start_bound, end_bound = _season_bounds(season())
    d = st.session_state[state_key]
    try:
        jumped = d.replace(year=year)
    except ValueError:
        jumped = d.replace(year=year, day=28)
    st.session_state[state_key] = max(start_bound, min(jumped, end_bound))


LOGO_WHITE_PATH = "Volley graphic design/image-removebg-preview (16) (1).png"


def render_sidebar_tools():
    """The sidebar's whole content: season/competition pickers, the period
    box, and quick presets -- everything that used to be scattered as local
    widgets across every page, now edited in one place."""
    col_logo, col_brand = st.columns([1, 3], vertical_alignment="center")
    with col_logo:
        st.image(LOGO_WHITE_PATH, width="stretch")
    with col_brand:
        st.markdown('<div class="brand-title">Vero Volley Milano</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-subtitle">Technical Staff · A1 Women\'s</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-stripe"></div>', unsafe_allow_html=True)

    st.selectbox("Season", mc.SEASONS, key="flt_season", on_change=_on_season_change)
    st.selectbox("Competition", [ALL_COMPETITIONS] + mc.COMPETITION_ORDER, key="flt_competition")

    match_pick_options = [ALL_MATCHES] + [m["date"] for m in _matches_for_picker()]
    ensure_valid_selection("flt_match_pick", match_pick_options)
    st.selectbox(
        "Match", match_pick_options, key="flt_match_pick", on_change=_apply_match_pick,
        format_func=lambda d: d if d == ALL_MATCHES else mc.match_label(d),
        help="Jump the period to a single match day, instead of picking dates below.",
    )

    st.markdown("**Period**")
    with st.container(border=True):
        start_bound, end_bound = _season_bounds(season())
        # Season years span at most 2 (Aug-Jul), but the calendar popup
        # can only step one month at a time with no year shortcut -- these
        # buttons are the one-click alternative, and there's no point
        # showing them when the whole season falls in a single year.
        years = list(range(start_bound.year, end_bound.year + 1))

        st.date_input("Start", key="flt_start", min_value=start_bound, max_value=end_bound)
        if len(years) > 1:
            year_cols = st.columns(len(years))
            for col, year in zip(year_cols, years):
                with col:
                    st.button(
                        str(year), key=f"flt_start_year_{year}", width="stretch",
                        on_click=_jump_year, args=("flt_start", year),
                        help=f"Jump the start date to {year}, same month/day.",
                    )
        st.checkbox("Different end date", key="flt_has_end")
        st.date_input(
            "End", key="flt_end", min_value=start_bound, max_value=end_bound,
            disabled=not st.session_state["flt_has_end"],
        )
        if len(years) > 1 and st.session_state["flt_has_end"]:
            year_cols = st.columns(len(years))
            for col, year in zip(year_cols, years):
                with col:
                    st.button(
                        str(year), key=f"flt_end_year_{year}", width="stretch",
                        on_click=_jump_year, args=("flt_end", year),
                        help=f"Jump the end date to {year}, same month/day.",
                    )

        preset_cols = st.columns(len(PRESETS) + 1)
        with preset_cols[0]:
            st.button("Full season", key="flt_preset_full", on_click=_apply_preset, args=(None,), width="stretch")
        for col, (label, days) in zip(preset_cols[1:], PRESETS.items()):
            with col:
                st.button(label.replace("Last ", ""), key=f"flt_preset_{days}", on_click=_apply_preset, args=(days,), width="stretch", help=label)

    st.caption(f":material/filter_alt: {caption()}")
