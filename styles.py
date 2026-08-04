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

        /* Every Plotly chart's own text (axis ticks, legends, hover,
           big numbers) renders in Streamlit's default Inter/Source Sans
           via an inline SVG style attribute, not the page's own CSS
           cascade -- overriding it here (needs !important to beat that
           inline style) is the one global hook that reaches all of them
           without touching every chart's Python layout individually. */
        .js-plotly-plot text {
            font-family: 'Roboto', sans-serif !important;
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
            --ink: #0d0d0f;
            --surface: #181818;
            --muted: #9a9a9a;
            --line: #2a2a2a;
            --display: 'Oswald', 'Arial Narrow', sans-serif;
        }

        /* Page content's top padding lives in Main_activity.py's NAV_CSS
           now -- it has to match the fixed nav bar's own height exactly,
           so it's defined right next to it instead of split across files. */

        /* Same diagonal-ribbon + corner-glow motif as the Home hero
           (home.py's HERO_CSS), toned down and applied to the whole main
           pane so every screen -- not just Home -- carries the identity,
           and bordered boxes (opaque fill below) read as solid cards
           floating on top of it instead of a flat single-tone page. */
        [data-testid="stMain"] {
            background:
                /* Primary ribbon -- crisp, full color, the one from the
                   Home hero everyone likes. */
                linear-gradient(135deg, transparent 44%, var(--accent-3) 44%, var(--accent-3) 46.2%, transparent 46.2%),
                /* Two thinner, softer companions in the other two brand
                   colors, at different angles/positions/widths so the page
                   doesn't read as one motif copy-pasted three times. */
                linear-gradient(120deg, transparent 68%, rgba(243, 52, 61, 0.5) 68%, rgba(243, 52, 61, 0.5) 68.5%, transparent 68.5%),
                linear-gradient(150deg, transparent 15%, rgba(22, 85, 165, 0.45) 15%, rgba(22, 85, 165, 0.45) 15.9%, transparent 15.9%),
                /* Stronger corner glows -- magenta/pink top-right, blue
                   bottom-left -- so the two brand extremes read clearly. */
                radial-gradient(55% 42% at 100% 0%, rgba(224, 21, 140, 0.32), transparent 68%),
                radial-gradient(65% 50% at 0% 100%, rgba(22, 85, 165, 0.34), transparent 68%),
                var(--ink);
            background-attachment: fixed;
        }

        /* Every card-style box in the app opens with a "**Title**"
           markdown as its own first element (the same convention the
           title-font rule above relies on) -- used here as a structural
           hook to give bordered st.container(border=True) boxes an
           opaque fill, since Streamlit's own generated class for them
           is a per-instance hash with no stable name to target directly.
           Scoped with a direct-child combinator on the first level so an
           outer wrapper merely containing a titled box deeper inside
           doesn't also get painted. */
        div[data-testid="stVerticalBlock"]:has(
            > div[data-testid="stElementContainer"]:first-child
              div[data-testid="stMarkdownContainer"] > p > strong:first-child
        ) {
            background: var(--surface);
            border-radius: 10px;
        }
        /* st.button() labels can also use **bold** markdown for their own
           reasons (players_grid's player cards bold the first name) --
           that trips the rule above too, since it can't see the strong
           tag is inside a button rather than a real title. Nesting
           :not(:has(button)) inside the :has() above isn't valid CSS
           (:has() can't contain another :has()), so this resets it back
           to transparent afterward instead, keyed off the player card's
           own stable class. */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"][class*="st-key-playercard_"]) {
            background: transparent !important;
        }
        /* home.py's "Low recovery / Recovery on track" card swaps its own
           header for a status icon+pill instead of the "**Title**"
           convention above, so it needs its own key to catch the same
           opaque-fill treatment. Same story for wellness.py's per-player
           cards (custom name/TQR header, one key per player -- wildcard
           match on the shared prefix). */
        .st-key-home_low_recovery_box,
        [class*="st-key-wellness_card_"] {
            background: var(--surface) !important;
            border-radius: 10px;
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
            height: 4px;
            border-radius: 2px;
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 55%, var(--accent-2) 82%, var(--accent-3) 100%);
            box-shadow: 0 0 10px 0 rgba(224, 21, 140, 0.35);
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
