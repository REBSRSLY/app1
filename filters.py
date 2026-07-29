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


def _on_season_change():
    """The period picker's min/max is season-bound; switching to a season
    with a different (or no) match range would otherwise leave the stored
    start/end outside the new bounds and make st.date_input raise."""
    _apply_preset(None, target_season=st.session_state["flt_season"])


LOGO_WHITE_PATH = "Volley graphic design/logo_white.png"


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

    st.selectbox("Season", mc.SEASONS, key="flt_season", on_change=_on_season_change)
    st.selectbox("Competition", [ALL_COMPETITIONS] + mc.COMPETITION_ORDER, key="flt_competition")

    st.markdown("**Period**")
    with st.container(border=True):
        start_bound, end_bound = _season_bounds(season())
        st.date_input("Start", key="flt_start", min_value=start_bound, max_value=end_bound)
        st.checkbox("Different end date", key="flt_has_end")
        st.date_input(
            "End", key="flt_end", min_value=start_bound, max_value=end_bound,
            disabled=not st.session_state["flt_has_end"],
        )

        preset_cols = st.columns(len(PRESETS) + 1)
        with preset_cols[0]:
            st.button("Full season", key="flt_preset_full", on_click=_apply_preset, args=(None,), width="stretch")
        for col, (label, days) in zip(preset_cols[1:], PRESETS.items()):
            with col:
                st.button(label.replace("Last ", ""), key=f"flt_preset_{days}", on_click=_apply_preset, args=(days,), width="stretch", help=label)

    st.caption(f":material/filter_alt: {caption()}")
