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


# Serie A1's box matches Playoff's own default height (rather than the
# standings table's taller natural size) so the two stay aligned, same
# height, side by side -- the standings table scrolls internally at this
# height like the results view already does.
SERIE_A_BOX_HEIGHT = 520
# Coppa Italia + Supercoppa stack in Champions League's column, each at
# half its box height (chrome included), so the two-box stack lands at the
# same total height as the single Champions League box beside it.
MINOR_BOX_HEIGHT = 221


def _render_serie_a_box(season: str, matches: list[dict]):
    """Serie A1's results and the season's final standings share one card
    -- a plain on/off toggle (no label) floats into the box's own header,
    top-right, instead of a separate labeled widget above the box. The
    Results view's W-L record chip moves in next to the title (record_inline)
    to leave that corner free for the toggle. Both views render at the same
    fixed height (SERIE_A_BOX_HEIGHT, matching Playoff's own) so toggling
    doesn't change the box's footprint, or its alignment with Playoff."""
    color = mc.COMPETITIONS["Serie A1"]["color"]
    with st.container(key="serie_a_box"):
        # Widget first so its value is known before the CSS below picks a
        # track color from it directly -- simpler and more reliable than a
        # CSS-only :has(input:checked) rule, which doesn't reliably
        # recompute against this specific React-driven checkbox.
        standings_view = st.toggle("Standings view", key="serie_a_standings_toggle", label_visibility="collapsed")
        track_color = color if standings_view else f"{color}55"
        # CSS and the box HTML in one st.markdown call, not two -- Streamlit
        # puts a gap between every pair of in-flow children of a vertical
        # block, and a *separate* zero-height style-only markdown still
        # counts as one of that pair even though the toggle beside it is
        # position:absolute, which pushed the box 15px below Playoff's own.
        style = f"""<style>
        .st-key-serie_a_box {{ position: relative; }}
        /* st.toggle renders as a styled stCheckbox (there's no separate
           "stToggle" testid) -- its label has 3 children: a visually-
           hidden span wrapping the real <input>, the track/knob pair
           (first div, matched structurally since the emotion-hash classes
           aren't stable to target directly), then the (here, collapsed)
           text label. Floats into the box's own header, top-right --
           targets the widget's own stElementContainer (keyed via the
           widget's own `key`, not the checkbox itself) since Streamlit
           already makes that container position:relative, which would
           else intercept the checkbox's own absolute positioning before
           it reaches the box. */
        .st-key-serie_a_standings_toggle {{
            position: absolute !important; top: 15px; right: 18px; z-index: 2;
            transform: scale(1.6); transform-origin: top right;
        }}
        .st-key-serie_a_box [data-testid="stCheckbox"] label > div:first-of-type {{
            background-color: {track_color} !important;
        }}
        </style>"""
        if not standings_view:
            box_html = cv.render_competition_box(
                "Serie A1", matches, show_round=False, height_px=SERIE_A_BOX_HEIGHT, record_inline=True,
            )
            st.markdown(style + box_html, unsafe_allow_html=True)
        else:
            box_html = cv.render_standings_box(mc.SEASON_STANDINGS.get(season, []), color=color, height_px=SERIE_A_BOX_HEIGHT)
            st.markdown(style + box_html, unsafe_allow_html=True)
            # Doesn't move with the sidebar's period, unlike the results
            # view -- a league table needs every team's results, not just
            # the matches this app has (Milano's own), so there's no
            # correct way to recompute a mid-season snapshot from what's
            # scoped here. This is the season's final table.
            st.caption(f":material/info: Final {season} standings — not affected by the period filter above.")


def _render_by_competition(season: str, matches: list[dict]):
    with st.container(key="css_comp_box"):
        st.markdown(cv.BOX_CSS, unsafe_allow_html=True)

    present = [c for c in mc.COMPETITION_ORDER if any(m["competition"] == c for m in matches)]
    if not present:
        st.info("No matches for this selection.")
        return

    st.markdown("**Form** · result points, chronological")
    _render_form_chart(matches)

    # Row 1: Serie A1 (results/standings switcher) + Playoff scudetto.
    if "Serie A1" in present or "Playoff scudetto" in present:
        col_serie_a, col_playoff = st.columns(2)
        if "Serie A1" in present:
            with col_serie_a:
                _render_serie_a_box(season, matches)
        if "Playoff scudetto" in present:
            with col_playoff:
                st.markdown(cv.render_competition_box("Playoff scudetto", matches), unsafe_allow_html=True)

    # Row 2: Champions League on the left; Coppa Italia + Supercoppa
    # stacked on the right (each at half height), so the row reads at the
    # same overall height on both sides.
    if "Champions League" in present or "Coppa Italia" in present or "Supercoppa Italiana" in present:
        col_cl, col_minor = st.columns(2)
        if "Champions League" in present:
            with col_cl:
                st.markdown(cv.render_competition_box("Champions League", matches), unsafe_allow_html=True)
        with col_minor:
            if "Coppa Italia" in present:
                st.markdown(cv.render_competition_box("Coppa Italia", matches, height_px=MINOR_BOX_HEIGHT), unsafe_allow_html=True)
            if "Supercoppa Italiana" in present:
                st.markdown(cv.render_competition_box("Supercoppa Italiana", matches, height_px=MINOR_BOX_HEIGHT), unsafe_allow_html=True)


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
