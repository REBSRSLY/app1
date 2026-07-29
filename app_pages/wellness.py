import pandas as pd
import plotly.colors as pcolors
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import players_grid as pg
from ui_helpers import GOOD_COLOR, LOW_COLOR, RECOVERY_THRESHOLD, WELLNESS_ICONS, close_polygon, dark_polar_layout

# Wellness questionnaire items: all 1-5, high = worse (confirmed by negative
# correlation with Tqr, which is 6-20 with high = better).
NEGATIVE_PARAMS = ["Fatica", "Sonno", "Doms", "Stress", "Mood"]
PARAM_LABELS = {
    "Fatica": "Fatigue",
    "Sonno": "Sleep",
    "Doms": "Muscle soreness",
    "Stress": "Stress",
    "Mood": "Mood",
    "Tqr": "TQR",
}
INVERTED_LABELS = {
    "Fatica": "Low fatigue",
    "Sonno": "Good sleep",
    "Doms": "Low soreness",
    "Stress": "Low stress",
    "Mood": "Good mood",
}
PARAM_RANGE = {
    "Fatica": (1, 5), "Sonno": (1, 5), "Doms": (1, 5),
    "Stress": (1, 5), "Mood": (1, 5), "Tqr": (6, 20),
}


def _player_role_map() -> dict[str, str]:
    """player_name (short name) -> English role label, for the Team radar's
    role filter."""
    names = dl.load_player_names()
    roles = dl.load_player_roles()
    return {names[code]: dl.ROLE_LABELS.get(r, r) for code, r in roles.items() if code in names}


def _render_player_radar(p_period, use_icons=False, height=None, show_caption=False, key=None):
    """Same enriched radar as the Players page overview: a faint mean
    shape, a shaded +/-1 std dev band around it, and a solid outline for
    the most recent day in range layered on top -- instead of one flat
    shape, this shows both the period's overall picture and how the latest
    check-in compares to it. Renders the chart itself (and a colored TQR
    header above it); returns the average TQR, or None if there's no data."""
    if p_period.empty:
        return None

    icons = list(WELLNESS_ICONS.values())
    labels = icons if use_icons else [INVERTED_LABELS[p] for p in NEGATIVE_PARAMS]

    means = [p_period[p].mean() for p in NEGATIVE_PARAMS]
    stds = [p_period[p].std() for p in NEGATIVE_PARAMS]
    values = [6 - m for m in means]
    # Inversion (6 - x) is a shift, so std is unaffected -- upper/lower
    # bounds just add/subtract it around the already-inverted mean, clipped
    # to the 1-5 axis.
    upper = [min(5.0, v + (s if pd.notna(s) else 0)) for v, s in zip(values, stds)]
    lower = [max(1.0, v - (s if pd.notna(s) else 0)) for v, s in zip(values, stds)]

    last_date = p_period["Data"].max()
    last_day = p_period[p_period["Data"] == last_date]
    last_values = [6 - last_day[p].mean() for p in NEGATIVE_PARAMS]

    tqr_avg = p_period["Tqr"].mean()
    t = max(0.0, min(1.0, (tqr_avg - 6) / (20 - 6)))
    color = pcolors.sample_colorscale("RdYlGn", [t])[0]
    fill_faint = color.replace("rgb", "rgba").replace(")", ",0.18)")
    line_faint = color.replace("rgb", "rgba").replace(")", ",0.7)")

    tqr_color = LOW_COLOR if tqr_avg < RECOVERY_THRESHOLD else GOOD_COLOR
    font_size = "0.95rem" if use_icons else "1.15rem"
    st.markdown(
        f'<div style="text-align:center; font-size:{font_size}; font-weight:700; color:{tqr_color};">TQR {tqr_avg:.1f}</div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    # ±1 std dev band: filled only between the lower and upper polygons
    # (fill="tonext" on the second trace), heavily transparent since it's
    # just context around the mean shape.
    r_lower, theta_lower = close_polygon(lower, labels)
    fig.add_trace(go.Scatterpolar(
        r=r_lower, theta=theta_lower, mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    r_upper, theta_upper = close_polygon(upper, labels)
    fig.add_trace(go.Scatterpolar(
        r=r_upper, theta=theta_upper, mode="lines", fill="tonext",
        line=dict(width=0), fillcolor=fill_faint,
        showlegend=False, hoverinfo="skip",
    ))
    # Mean shape: thin, slightly-transparent outline, fainter than the
    # most-recent-day line below so the two don't compete.
    r, theta = close_polygon(values, labels)
    fig.add_trace(go.Scatterpolar(
        r=r, theta=theta, mode="lines", line=dict(color=line_faint, width=1.2),
        showlegend=False,
    ))
    # Most recent day in range: a solid outline with filled dots, drawn
    # last so it stands out over the std band.
    r_last, theta_last = close_polygon(last_values, labels)
    fig.add_trace(go.Scatterpolar(
        r=r_last, theta=theta_last, mode="lines+markers",
        line=dict(color=color, width=2), marker=dict(color=color, size=5 if use_icons else 7),
        showlegend=False,
    ))
    fig.update_layout(**dark_polar_layout([1, 5]))
    if height is not None:
        fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10))
    if use_icons:
        fig.update_layout(polar=dict(angularaxis=dict(tickfont=dict(size=22))))
    st.plotly_chart(fig, width="stretch", theme=None, key=key)

    if show_caption:
        st.caption("Bigger = feeling better. Faint band = ±1 std dev over this period · solid line = most recent day in range.")

    return tqr_avg


def render():
    wellness = dl.load_wellness_data()["wellness"]
    period = filters.filter_by_date_col(wellness)

    col_team, col_player = st.columns(2)

    role_map = _player_role_map()

    with col_team:
        with st.container(border=True):
            st.markdown("**Team · by parameter**")
            col_param, col_role = st.columns(2)
            with col_param:
                param = st.selectbox(
                    "Parameter", list(PARAM_LABELS.keys()),
                    format_func=lambda p: PARAM_LABELS[p], key="team_param",
                )
            with col_role:
                role_sel = st.selectbox(
                    "Role", ["All roles"] + sorted(set(role_map.values())), key="team_role",
                )
            players = sorted(period["player_name"].unique())
            if role_sel != "All roles":
                players = [p for p in players if role_map.get(p) == role_sel]
            team_avg = period.groupby("player_name")[param].mean().reindex(players)

            if team_avg.empty:
                st.info("No data in this date range.")
            else:
                lo, hi = PARAM_RANGE[param]
                is_negative = param in NEGATIVE_PARAMS
                # Same inversion as the individual radars below: these
                # params are 1-5 with high = worse, so plotting the raw
                # value would make a *bad* score look bigger on the
                # chart. Flip to lo+hi-x so bigger always means better,
                # like Tqr (and the individual charts) already do.
                values = [lo + hi - v for v in team_avg.values] if is_negative else list(team_avg.values)
                r, theta = close_polygon(values, list(team_avg.index))
                fig = go.Figure(go.Scatterpolar(
                    r=r, theta=theta, fill="toself",
                    line_color="#2ecc71", fillcolor="rgba(46,204,113,0.25)",
                ))
                fig.update_layout(**dark_polar_layout([lo, hi]))
                st.plotly_chart(fig, width="stretch", theme=None)
                if is_negative:
                    st.caption("Axis inverted so bigger = better.")

    with col_player:
        with st.container(border=True):
            st.markdown("**Individual player**")
            all_players = sorted(wellness["player_name"].unique())
            player_sel = st.selectbox("Player", all_players, key="wellness_player")
            p_period = period[period["player_name"] == player_sel]

            tqr_avg = _render_player_radar(p_period, show_caption=True)
            if tqr_avg is None:
                st.info("No data for this player in this date range.")

    st.write("---")
    st.markdown("**All players**")
    for row in pg.GRID_ROWS:
        cols = st.columns(4)
        for col, player in zip(cols, row):
            with col:
                if player is None:
                    with st.container(border=True):
                        st.image(pg.CREST_PATH, width="stretch")
                    continue
                with st.container(border=True):
                    st.caption(player["last"])
                    p_period = period[period["player_name"] == player["surname"]]
                    tqr_avg = _render_player_radar(
                        p_period, use_icons=True, height=170, key=f"radar_{player['surname']}",
                    )
                    if tqr_avg is None:
                        st.caption("No data")
