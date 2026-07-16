"""CSS personalizzato per replicare lo stile pulito del mockup React."""

import streamlit as st

CUSTOM_CSS = """
    <style>
        /* Variabili e stili generali */
        :root {
            --accent: #c0392b;
            --accent-bg: #fbeceb;
            --muted: #8a8a8a;
            --line: #e6e6e6;
        }

        /* Stile sidebar */
        .css-1d391kg { padding-top: 2rem; }
        .brand-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0px;
        }
        .brand-subtitle {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 1.5rem;
        }

        /* Box Bozze di lavoro */
        .draft-block {
            border: 1px dashed #c6c6c6;
            border-radius: 10px;
            padding: 16px;
            background-color: #fcfcfc;
            margin-bottom: 15px;
        }
        .draft-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #8a8a8a;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .ph-line {
            color: #555555;
            font-size: 13.5px;
            margin-bottom: 8px;
        }
        .ph-line:last-child { margin-bottom: 0; }

        /* Card di Allerta (TQR) */
        .alert-card {
            background-color: #fff6ea;
            border: 1px solid #f0dcb4;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            color: #1a1a1a;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Badge di Capitano */
        .cap-tag {
            display: inline-block;
            margin-left: 8px;
            font-size: 10px;
            font-style: normal;
            text-transform: uppercase;
            color: #c0392b;
            border: 1px solid #e6bdb8;
            border-radius: 4px;
            padding: 1px 5px;
            font-weight: bold;
        }

        /* Chips per le date delle partite */
        .chip-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .date-chip {
            border: 1px solid #e6e6e6;
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 12.5px;
            font-family: monospace;
            color: #444;
            background-color: #ffffff;
        }
    </style>
"""


def inject():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
