import pandas as pd
import plotly.colors as pcolors
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import filters
import player_colors as pc
import players_grid as pg
from ui_helpers import GOOD_COLOR, LOW_COLOR, RECOVERY_THRESHOLD, WELLNESS_ICONS, close_polygon, dark_polar_layout, tqr_yaxis_ticks

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
# Short description of each of the 5 daily self-reported items -- all rated
# 1-5 with high = worse (see NEGATIVE_PARAMS above), shown in the intro
# expander so a new reader doesn't have to guess what each icon/label means.
PARAM_DESCRIPTIONS = {
    "Fatica": "Overall tiredness reported that day. 1 = fresh, 5 = exhausted.",
    "Sonno": "Sleep quality the night before. 1 = great sleep, 5 = poor/disturbed sleep.",
    "Doms": "Delayed-onset muscle soreness from recent training. 1 = none, 5 = severe.",
    "Stress": "Perceived mental/emotional stress. 1 = relaxed, 5 = very stressed.",
    "Mood": "General mood. 1 = great mood, 5 = very low mood.",
}


def _render_how_to():
    with st.expander("How to read this page", icon=":material/menu_book:"):
        st.markdown(
            "**TQR (Total Quality Recovery)** is a self-reported recovery score on a "
            f"6–20 scale, higher = better recovered. The club treats **{RECOVERY_THRESHOLD} "
            f"and above as optimal recovery** — a value below {RECOVERY_THRESHOLD} means the "
            "player hasn't bounced back enough since her last session, and is the trigger "
            "for the Home page's low-recovery alert."
        )
        st.markdown("**The 5 daily wellness items** (each rated 1–5 by the player):")
        for p in NEGATIVE_PARAMS:
            st.markdown(f"**{WELLNESS_ICONS[p]} {PARAM_LABELS[p]}** — {PARAM_DESCRIPTIONS[p]}")
        st.caption(
            "All 5 items are \"high = worse\" as reported, but every chart on this page "
            "inverts them so bigger always reads as better, consistent with TQR."
        )


def _player_role_map() -> dict[str, str]:
    """player_name (short name) -> English role label, for the Team radar's
    role filter."""
    names = dl.load_player_names()
    roles = dl.load_player_roles()
    return {names[code]: dl.ROLE_LABELS.get(r, r) for code, r in roles.items() if code in names}


def _render_player_radar(p_period, use_icons=False, height=None, show_header=True, key=None):
    """Same enriched radar as the Players page overview: a faint mean
    shape, a shaded +/-1 std dev band around it, and a solid outline for
    the most recent day in range layered on top -- instead of one flat
    shape, this shows both the period's overall picture and how the latest
    check-in compares to it. Renders the chart itself (and, unless the
    caller builds its own header, a colored TQR header above it); returns
    the average TQR, or None if there's no data."""
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

    if show_header:
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
    # Radial ring numbers (1, 1.5, 2 ... 5) are just clutter here -- the
    # shape/color/recency already carry the meaning, and the axis range is
    # explained in the caption instead.
    fig.update_layout(polar=dict(radialaxis=dict(showticklabels=False)))
    if height is not None:
        # The icon labels need more breathing room than a plain text label
        # would -- tight 10px margins were clipping them at the card edge.
        margin = dict(l=30, r=30, t=26, b=26) if use_icons else dict(l=10, r=10, t=10, b=10)
        fig.update_layout(height=height, margin=margin)
    if use_icons:
        fig.update_layout(polar=dict(angularaxis=dict(tickfont=dict(size=18))))
    st.plotly_chart(fig, width="stretch", theme=None, key=key)

    return tqr_avg


def _render_team_tqr_trend(period: pd.DataFrame):
    """Team-average TQR per day against the recovery threshold -- the y-axis
    ticks themselves are colored (red below, yellow at, green above the
    threshold) so the read doesn't depend on spotting the dashed line."""
    daily = period.groupby("Data")["Tqr"].mean().reset_index().dropna(subset=["Tqr"]).sort_values("Data")
    if daily.empty:
        st.info("No wellness data in this date range.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["Data"], y=daily["Tqr"], mode="lines+markers", name="Team average TQR",
        line=dict(color="#2ecc71", width=2),
    ))
    fig.add_hline(y=RECOVERY_THRESHOLD, line_dash="dash", line_color=LOW_COLOR)
    fig.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="TQR", range=[6, 20], **tqr_yaxis_ticks()), xaxis_title=None,
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")


# Order the 5-role legend below the individual TQR trend chart is grouped
# into -- matches the role groupings used throughout the app (GRID_ROWS,
# the Team radar's role filter).
ROLE_ORDER = ["Setter", "Opposite", "Outside Hitter", "Middle Blocker", "Libero"]


def _render_individual_tqr_trends(period: pd.DataFrame):
    """Same TQR-over-time view as the team chart above, but one line per
    player in her own color -- shows who's driving the team average and who
    has been running consistently low, which the aggregate above can't.
    The legend is grouped by role (one column per role) below the chart
    instead of a single flat player list to the side."""
    daily = period.dropna(subset=["Tqr"]).groupby(["Data", "player_name"], as_index=False)["Tqr"].mean().sort_values("Data")
    if daily.empty:
        st.info("No wellness data in this date range.")
        return

    role_map = _player_role_map()
    color_map = pc.color_map(daily["player_name"].unique())

    fig = go.Figure()
    for role in ROLE_ORDER:
        players_in_role = sorted(p for p in daily["player_name"].unique() if role_map.get(p) == role)
        for i, player in enumerate(players_in_role):
            d = daily[daily["player_name"] == player]
            group_kwargs = {"legendgrouptitle_text": role} if i == 0 else {}
            fig.add_trace(go.Scatter(
                x=d["Data"], y=d["Tqr"], mode="lines", name=player,
                line=dict(color=color_map.get(player)),
                legendgroup=role, **group_kwargs,
            ))
    fig.add_hline(y=RECOVERY_THRESHOLD, line_dash="dash", line_color=LOW_COLOR)
    fig.update_layout(
        height=420, margin=dict(l=10, r=10, t=10, b=150),
        yaxis=dict(title="TQR", range=[6, 20], **tqr_yaxis_ticks()),
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, groupclick="togglegroup", tracegroupgap=15),
    )
    st.plotly_chart(fig, width="stretch")


def _player_card_border_css() -> str:
    """Colors each "All players" card border with that player's own color
    (the same hue used everywhere else in the app) via the st-key trick --
    st.container(border=True) has no color parameter of its own."""
    rules = [
        f'[class*="st-key-wellness_card_{p["surname"]}"] {{ border-color: {pc.color_for(p["surname"])} !important; }}'
        for p in pg.ALL_PLAYERS
    ]
    return f"<style>{''.join(rules)}</style>"


def _render_team_legend_box():
    """Explains the Team radar + Team TQR trend together -- placed below
    the (shorter) trend chart, in the vertical space the taller radar box
    next to it leaves empty, instead of a caption under each chart."""
    with st.container(border=True):
        st.markdown("**How to read** · Team charts")
        st.markdown(
            "**Radar** — faint shaded band = ±1 std dev across players over this period · "
            "solid outline = most recent day in range. Axis inverted where needed so bigger "
            "always means better, matching TQR."
        )
        st.markdown(
            f"**Trend** — solid line = team average TQR per day · dashed line = recovery "
            f"threshold ({RECOVERY_THRESHOLD}) · y-axis numbers colored red/yellow/green around it."
        )


def _render_individual_legend_box():
    """Same idea as the team legend box above, for the Individual player
    radar + Individual TQR trend, plus the emoji legend used on the
    per-player radars further down the page."""
    with st.container(border=True):
        st.markdown("**How to read** · Individual charts")
        st.markdown(
            "**Radar** — bigger = feeling better. Faint shaded band = ±1 std dev over this "
            "period · solid outline = most recent day in range."
        )
        st.markdown(
            f"**Trend** — one line per player, legend grouped by role below the chart · "
            f"dashed line = recovery threshold ({RECOVERY_THRESHOLD})."
        )


def render():
    wellness = dl.load_wellness_data()["wellness"]
    period = filters.filter_by_date_col(wellness)

    _render_how_to()

    role_map = _player_role_map()

    col_team, col_team_trend = st.columns([0.28, 0.72])
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
            players = pc.sort_by_role(period["player_name"].unique())
            if role_sel != "All roles":
                players = [p for p in players if role_map.get(p) == role_sel]
            d = period[period["player_name"].isin(players)]
            agg = d.groupby("player_name")[param].agg(["mean", "std"]).reindex(players)

            if agg["mean"].isna().all():
                st.info("No data in this date range.")
            else:
                lo, hi = PARAM_RANGE[param]
                is_negative = param in NEGATIVE_PARAMS

                def _invert(s):
                    # Same inversion as the individual radars: these params
                    # are 1-5 with high = worse, so plotting the raw value
                    # would make a *bad* score look bigger on the chart.
                    # Flip to lo+hi-x so bigger always means better, like
                    # Tqr (and the individual charts) already do.
                    return lo + hi - s if is_negative else s

                # Same enriched radar as the individual charts: a faint
                # mean shape, a +/-1 std dev band around it, and a solid
                # outline for each player's most recent day in range.
                last_per_player = d.sort_values("Data").groupby("player_name").tail(1).set_index("player_name")[param]
                last_per_player = last_per_player.reindex(players)

                values = _invert(agg["mean"]).fillna(lo).tolist()
                stds = agg["std"].fillna(0).tolist()
                last_values = _invert(last_per_player).fillna(pd.Series(values, index=players)).tolist()
                upper = [min(hi, v + s) for v, s in zip(values, stds)]
                lower = [max(lo, v - s) for v, s in zip(values, stds)]

                fig = go.Figure()
                r_lower, theta_lower = close_polygon(lower, players)
                fig.add_trace(go.Scatterpolar(
                    r=r_lower, theta=theta_lower, mode="lines", line=dict(width=0),
                    showlegend=False, hoverinfo="skip",
                ))
                r_upper, theta_upper = close_polygon(upper, players)
                fig.add_trace(go.Scatterpolar(
                    r=r_upper, theta=theta_upper, mode="lines", fill="tonext",
                    line=dict(width=0), fillcolor="rgba(46,204,113,0.18)",
                    showlegend=False, hoverinfo="skip",
                ))
                r, theta = close_polygon(values, players)
                fig.add_trace(go.Scatterpolar(
                    r=r, theta=theta, mode="lines", line=dict(color="rgba(46,204,113,0.7)", width=1.2),
                    showlegend=False,
                ))
                r_last, theta_last = close_polygon(last_values, players)
                fig.add_trace(go.Scatterpolar(
                    r=r_last, theta=theta_last, mode="lines+markers",
                    line=dict(color="#2ecc71", width=2), marker=dict(color="#2ecc71", size=6),
                    showlegend=False,
                ))
                fig.update_layout(**dark_polar_layout([lo, hi]))
                fig.update_layout(polar=dict(radialaxis=dict(showticklabels=False)))
                st.plotly_chart(fig, width="stretch", theme=None)
    with col_team_trend:
        with st.container(border=True):
            st.markdown("**Team TQR** · trend over time")
            _render_team_tqr_trend(period)
        _render_team_legend_box()

    col_player, col_ind_trend = st.columns([0.28, 0.72])
    with col_player:
        with st.container(border=True):
            st.markdown("**Individual player**")
            all_players = pc.sort_by_role(wellness["player_name"].unique())
            player_sel = st.selectbox("Player", all_players, key="wellness_player")
            p_period = period[period["player_name"] == player_sel]

            tqr_avg = _render_player_radar(p_period)
            if tqr_avg is None:
                st.info("No data for this player in this date range.")
    with col_ind_trend:
        with st.container(border=True):
            st.markdown("**Individual TQR** · trend over time")
            _render_individual_tqr_trends(period)
        _render_individual_legend_box()

    st.write("---")
    st.markdown("**All players**")
    st.markdown(_player_card_border_css(), unsafe_allow_html=True)
    for row in pg.GRID_ROWS:
        cols = st.columns(5)
        for col, player in zip(cols, row):
            with col:
                with st.container(border=True, key=f"wellness_card_{player['surname']}"):
                    p_period = period[period["player_name"] == player["surname"]]
                    tqr_avg = None if p_period.empty else p_period["Tqr"].mean()
                    name_color = pc.color_for(player["surname"])
                    if tqr_avg is None or pd.isna(tqr_avg):
                        tqr_html = '<span style="color:var(--muted);font-weight:700;">—</span>'
                    else:
                        tqr_color = LOW_COLOR if tqr_avg < RECOVERY_THRESHOLD else GOOD_COLOR
                        tqr_html = f'<span style="color:{tqr_color};font-weight:700;">{tqr_avg:.1f}</span>'
                    st.markdown(
                        '<div style="display:flex;justify-content:space-between;align-items:baseline;">'
                        f'<span style="font-family:var(--display);font-weight:700;font-size:1.05rem;'
                        f'text-transform:uppercase;letter-spacing:0.02em;'
                        f'color:{name_color};">{player["last"]}</span>{tqr_html}</div>',
                        unsafe_allow_html=True,
                    )
                    result = _render_player_radar(
                        p_period, use_icons=True, height=195, key=f"radar_{player['surname']}",
                        show_header=False,
                    )
                    if result is None:
                        st.caption("No data")
