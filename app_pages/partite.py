from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import calendar_view as cv
import filters
import match_calendar as mc

# Same 3/2/1/0 scale as mc.result_points, keyed by the raw score string --
# used to color/order the "All matches" score-pattern chart.
_SCORE_POINTS = {"3-0": 3, "3-1": 3, "3-2": 2, "2-3": 1, "1-3": 0, "0-3": 0}


def _render_form_chart(matches: list[dict]):
    """Match-by-match result points in chronological order: an at-a-glance
    form/momentum view across whatever's currently in scope. Bar height is
    the result (points), bar color is the competition -- the same colors as
    each competition's box below -- so a pattern like "we lose more in
    Champions League" is visible at a glance instead of needing the color
    to repeat what the height already shows."""
    ordered = sorted(matches, key=lambda m: m["date"])
    points = [mc.result_points(m) for m in ordered]
    labels = [m["opponent"] for m in ordered]
    hover = [
        f"{fmt}<br>{m['score']} · {m['competition']}"
        for fmt, m in zip((cv.fmt_date(m["date"]) for m in ordered), ordered)
    ]

    fig = go.Figure(go.Bar(
        x=list(range(len(ordered))), y=points,
        marker_color=[mc.COMPETITIONS[m["competition"]]["color"] for m in ordered],
        text=labels, hovertext=hover, hovertemplate="%{text}<br>%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        height=140, margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Pts", range=[0, 3.4], tickvals=[0, 1, 2, 3]),
        xaxis=dict(visible=False),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Bar height = result points · bar color = competition (see the boxes below).")


def _render_by_competition(season: str, matches: list[dict]):
    st.markdown(cv.BOX_CSS, unsafe_allow_html=True)

    present = [c for c in mc.COMPETITION_ORDER if any(m["competition"] == c for m in matches)]
    if not present:
        st.info("No matches for this selection.")
        return

    st.markdown("**Form** · result points, chronological")
    _render_form_chart(matches)

    show_standings = "Serie A1" in present
    if show_standings:
        col_results, col_standings = st.columns([1, 1.2])
        with col_results:
            st.markdown(cv.render_competition_box("Serie A1", matches, show_round=False), unsafe_allow_html=True)
        with col_standings:
            st.markdown(
                cv.render_standings_box(mc.SEASON_STANDINGS.get(season, []), color=mc.COMPETITIONS["Serie A1"]["color"]),
                unsafe_allow_html=True,
            )
        secondary = [c for c in present if c != "Serie A1"]
    else:
        secondary = present

    if len(secondary) == 1:
        st.markdown(cv.render_competition_box(secondary[0], matches), unsafe_allow_html=True)
    else:
        for i in range(0, len(secondary), 2):
            cols = st.columns(2)
            for col, comp in zip(cols, secondary[i:i + 2]):
                with col:
                    st.markdown(cv.render_competition_box(comp, matches), unsafe_allow_html=True)


def _render_month_distribution(matches: list[dict]):
    """Matches per month, stacked by competition -- scoped to the active
    period like everything else in this section (used to be the whole
    season regardless of period, back when this lived in its own "Full
    calendar" section)."""
    if not matches:
        return

    df = pd.DataFrame(matches)
    order = sorted({(d.year, d.month) for d in df["pdate"]})
    order_labels = [f"{cv.MONTH_NAMES[m][:3]} {y}" for y, m in order]
    df["month"] = df["pdate"].apply(lambda d: f"{cv.MONTH_NAMES[d.month][:3]} {d.year}")

    counts = df.groupby(["month", "competition"], observed=True).size().reset_index(name="count")
    fig = px.bar(
        counts, x="month", y="count", color="competition",
        category_orders={"month": order_labels, "competition": mc.COMPETITION_ORDER},
        color_discrete_map={k: v["color"] for k, v in mc.COMPETITIONS.items()},
        labels={"month": "", "count": "Matches", "competition": ""},
    )
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    st.plotly_chart(fig, width="stretch")


def _render_score_distribution(matches: list[dict]):
    """How often each scoreline occurred -- straight wins/losses vs.
    tie-break matches, at a glance."""
    counts = Counter(m["score"] for m in matches)
    scores = sorted(counts.keys(), key=lambda s: _SCORE_POINTS.get(s, 0))

    fig = go.Figure(go.Bar(
        x=[counts[s] for s in scores], y=scores, orientation="h",
        marker_color=[cv.RESULT_COLORS[_SCORE_POINTS.get(s, 0)] for s in scores],
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Matches", yaxis_title="")
    st.plotly_chart(fig, width="stretch")


def _render_all_matches(matches: list[dict]):
    if not matches:
        st.info("No matches for this selection.")
        return

    # Score patterns + Matches per month side by side, narrower and the
    # same height, above the search box -- Month used to be a whole
    # separate "Full calendar" section on the full season regardless of
    # period; folded in here so both charts read the same active scope.
    col_score, col_month = st.columns(2)
    with col_score:
        st.markdown("**Score patterns**")
        _render_score_distribution(matches)
    with col_month:
        st.markdown("**Matches per month**")
        _render_month_distribution(matches)

    df = pd.DataFrame(matches).sort_values("date")
    df["Date"] = df["date"].apply(cv.fmt_date)
    df["Venue"] = df["home"].map({True: "Home", False: "Away"})
    df["Round"] = df.apply(lambda r: f"{r['competition']} ({r['round']})", axis=1)
    df["Result"] = df["score"].apply(lambda s: "W" if int(s.split("-")[0]) > int(s.split("-")[1]) else "L")

    search = st.text_input("Search matches", placeholder="E.g. date, opponent or competition", icon=":material/search:")
    if search:
        s = search.lower()
        mask = df.apply(lambda r: s in r["Date"].lower() or s in r["opponent"].lower() or s in r["Round"].lower(), axis=1)
        df = df[mask]

    st.dataframe(
        df[["Date", "opponent", "Venue", "Round", "score", "Result"]].rename(columns={
            "opponent": "Opponent", "score": "Score",
        }),
        hide_index=True,
        width="stretch",
        column_config={
            "Date": st.column_config.TextColumn(width="small"),
            "Result": st.column_config.TextColumn(width="small"),
        },
    )


SECTIONS = ["By competition", "All matches"]


def render():
    season = filters.season()
    season_matches = mc.matches_for_season(season)
    scoped_matches = filters.matches_in_scope()

    if not season_matches:
        st.info(f"No matches recorded yet for the {season} season.")
        return

    section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="matches_section")

    if section == "By competition":
        _render_by_competition(season, scoped_matches)
    else:
        _render_all_matches(scoped_matches)
