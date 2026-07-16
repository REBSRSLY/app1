"""Custom CSS replicating the clean style of the React mockup."""

import streamlit as st

CUSTOM_CSS = """
    <style>
        /* General variables and styles */
        :root {
            --accent: #c0392b;
            --accent-bg: rgba(192, 57, 43, 0.12);
            --surface: #181818;
            --muted: #9a9a9a;
            --line: #2a2a2a;
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

        /* Match date chips */
        .chip-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .date-chip {
            border: 1px solid var(--line);
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 12.5px;
            font-family: monospace;
            color: var(--muted);
            background-color: var(--surface);
        }

        /* Dossier-style player cards (Players page) */
        .dossier-tab {
            height: 6px;
            border-radius: 6px 6px 0 0;
            margin: -1px -1px 12px -1px;
        }
        .dossier-tab.starter { background: var(--accent); }
        .dossier-tab.bench { background: var(--muted); }
        .dossier-id {
            font-family: monospace;
            font-size: 11px;
            letter-spacing: 0.08em;
            color: var(--muted);
            text-transform: uppercase;
        }
        .dossier-name {
            font-size: 1.15rem;
            font-weight: 700;
        }
        .stamp-captain {
            display: inline-block;
            margin-left: 8px;
            font-size: 10px;
            font-family: monospace;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--accent);
            border: 1.5px solid var(--accent);
            border-radius: 3px;
            padding: 1px 6px;
            font-weight: bold;
            transform: rotate(-4deg);
        }
    </style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
