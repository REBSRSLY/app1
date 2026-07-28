import plotly.colors as pcolors
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from ui_helpers import close_polygon, dark_polar_layout, date_range_picker, section_header

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


def render():
    section_header(
        "Wellness",
        "Daily wellness questionnaire (Fatigue, Sleep, Doms, Stress, Mood, TQR) — for the team or an individual player.",
    )

    wellness = dl.load_wellness_data()["wellness"]

    start_d, end_d = date_range_picker("Date range", wellness["Data"], 7, "wellness_dates")
    period = wellness[(wellness["Data"].dt.date >= start_d) & (wellness["Data"].dt.date <= end_d)]
    st.caption(f"Averages over {start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')}.")

    col_team, col_player = st.columns(2)

    with col_team:
        with st.container(border=True):
            st.markdown("**Team · by parameter**")
            param = st.selectbox(
                "Parameter", list(PARAM_LABELS.keys()),
                format_func=lambda p: PARAM_LABELS[p], key="team_param",
            )
            players = sorted(period["player_name"].unique())
            team_avg = period.groupby("player_name")[param].mean().reindex(players)

            if team_avg.empty:
                st.info("No data in this date range.")
            else:
                lo, hi = PARAM_RANGE[param]
                is_negative = param in NEGATIVE_PARAMS
                # Same inversion as the individual radar below: these
                # params are 1-5 with high = worse, so plotting the raw
                # value would make a *bad* score look bigger on the
                # chart. Flip to lo+hi-x so bigger always means better,
                # like Tqr (and the individual chart) already do.
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

            if p_period.empty:
                st.info("No data for this player in this date range.")
            else:
                inverted = [6 - p_period[p].mean() for p in NEGATIVE_PARAMS]
                labels = [INVERTED_LABELS[p] for p in NEGATIVE_PARAMS]
                tqr_avg = p_period["Tqr"].mean()
                t = max(0.0, min(1.0, (tqr_avg - 6) / (20 - 6)))
                color = pcolors.sample_colorscale("RdYlGn", [t])[0]
                fill = color.replace("rgb", "rgba").replace(")", ", 0.35)")
                r, theta = close_polygon(inverted, labels)
                fig = go.Figure(go.Scatterpolar(r=r, theta=theta, fill="toself", line_color=color, fillcolor=fill))
                fig.update_layout(**dark_polar_layout([1, 5]))
                st.plotly_chart(fig, width="stretch", theme=None)
                st.caption(f"Axes inverted so bigger = feeling better. Fill color reflects average TQR: {tqr_avg:.1f}/20.")
