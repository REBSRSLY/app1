"""Custom CSS replicating the clean style of the React mockup."""

import streamlit as st

CUSTOM_CSS = """
    <style>
        /* General variables and styles. --accent/--accent-2 are the club
           logo's own blue/red, used for the nav bar, buttons and other
           brand chrome (charts keep their own established per-role/
           per-player palettes -- these two are for app chrome only). */
        :root {
            --accent: #1655a5;
            --accent-2: #f3343d;
            --accent-bg: rgba(22, 85, 165, 0.12);
            --surface: #181818;
            --muted: #9a9a9a;
            --line: #2a2a2a;
        }

        /* Pull page content up closer to the nav bar instead of leaving
           Streamlit's default large top gap. */
        div[data-testid="stMainBlockContainer"] {
            padding-top: 1.5rem;
        }

        /* Sidebar style */
        .brand-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0px;
        }
        .brand-subtitle {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 1.5rem;
        }

        /* Draft/work-in-progress box */
        .draft-block {
            border: 1px dashed var(--line);
            border-radius: 10px;
            padding: 16px;
            background-color: var(--surface);
            margin-bottom: 15px;
        }
        .draft-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            font-weight: bold;
            margin-bottom: 10px;
        }
        .ph-line {
            color: var(--muted);
            font-size: 13.5px;
            margin-bottom: 8px;
        }
        .ph-line:last-child { margin-bottom: 0; }

        /* Alert card (TQR) */
        .alert-card {
            background-color: rgba(240, 166, 0, 0.1);
            border: 1px solid rgba(240, 166, 0, 0.35);
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

    </style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
