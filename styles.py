"""Custom CSS replicating the clean style of the React mockup."""

import streamlit as st

CUSTOM_CSS = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@700&family=Oswald:wght@700&display=swap');

        /* Every chart/section title in the app follows the same
           "**Title** · subtitle" markdown convention -- the leading bold
           phrase in a markdown block is the title, so giving it a
           distinct, recognizable font (rather than the body's default)
           makes titles pop consistently everywhere without having to
           touch every individual st.markdown() call. Scoped to
           <strong>, not <b>, since raw-HTML stat displays (TQR pills,
           scores, etc.) use <b> and are deliberately left alone.

           Stays Roboto, not Oswald: this text sits next to dense data on
           every page (Wellness, Loads, Scout & Stats...), so it keeps the
           app's own "interface/data" role from Identity/brand-guidelines.md
           -- Oswald is reserved for brand chrome (nav, hero, player
           identity) where it can't compete with anything for scanability. */
        [data-testid="stMarkdownContainer"] > p > strong:first-child {
            font-family: 'Roboto', sans-serif;
            font-weight: 700;
        }

        /* General variables and styles. --accent/--accent-2 are the club
           logo's own blue/red (Identity/brand-guidelines.md's "Blu Vero" /
           "Rosso Volley"), used for the nav bar, buttons and other brand
           chrome (charts keep their own established per-role/per-player
           palettes -- these two are for app chrome only). --accent-3 is
           the campaign "energy" magenta ("Magenta Numia") -- by the
           guide's own 80/15/5 rule it appears in at most one or two small
           chrome accents, never as a data or status color. --display is
           brand chrome only (nav, hero, player identity); everything
           else -- including chart titles above -- stays on the body font. */
        :root {
            --accent: #1655a5;
            --accent-2: #f3343d;
            --accent-3: #e0158c;
            --accent-bg: rgba(22, 85, 165, 0.12);
            --surface: #181818;
            --muted: #9a9a9a;
            --line: #2a2a2a;
            --display: 'Oswald', 'Arial Narrow', sans-serif;
        }

        /* Pull page content up closer to the nav bar instead of leaving
           Streamlit's default large top gap. */
        div[data-testid="stMainBlockContainer"] {
            padding-top: 1.5rem;
        }

        /* Sidebar style */
        .brand-title {
            font-family: var(--display);
            font-size: 1.15rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            margin-bottom: 0px;
        }
        .brand-subtitle {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 0.9rem;
        }
        /* One brand moment above the functional filter controls, nowhere
           near them -- Blu Vero -> Rosso Volley -> Magenta Numia, the
           app's own accent trio in one line (Identity/brand-guidelines.md
           §3.3's 80/15/5: the magenta only ever gets a sliver like this). */
        .brand-stripe {
            height: 3px;
            border-radius: 2px;
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 60%, var(--accent-2) 85%, var(--accent-3) 100%);
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
