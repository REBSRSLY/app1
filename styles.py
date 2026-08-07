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
           scores, etc.) use <b> and are deliberately left alone. Oswald
           Bold everywhere now, chart titles included -- explicit request
           to make every title read as brand chrome, not just nav/hero. */
        [data-testid="stMarkdownContainer"] > p > strong:first-child {
            font-family: var(--display);
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

        /* Streamlit's own theming gives every plotly chart's outer <svg> a
           CSS background-color of its own (the app theme's backgroundColor,
           #0d0d0f -- separate from Plotly's paper_bgcolor, which most
           charts here already leave transparent) -- showing up as a
           visibly different-toned rectangle inside an otherwise solid
           black card. Overriding it to --surface makes the chart's plot
           area disappear into its card instead of standing out from it.

           Plotly actually stacks 2-3 <svg class="main-svg"> siblings per
           chart (bg/axes/data layer, then a legend/title/annotation
           layer on top, then a hover layer) -- targeting plain "svg"
           painted EVERY layer, so the (opaque) top layer's background
           covered the data layer underneath it and the chart looked
           empty. :first-of-type scopes this to just the bottom layer. */
        [data-testid="stPlotlyChart"] svg.main-svg:first-of-type {
            background-color: var(--surface) !important;
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
            /* Every card's fill -- solid black, deliberately flatter than
               the page's own mesh+diagonal background so content stays
               readable against it. Doesn't touch the roster grid's own
               per-role player card buttons (players_grid.ROLE_COLORS
               gradients), which never used this token. */
            --surface: #000000;
            --muted: #9a9a9a;
            --line: #2a2a2a;
            --display: 'Oswald', 'Arial Narrow', sans-serif;
        }

        /* Page content's top padding lives in Main_activity.py's NAV_CSS
           now -- it has to match the fixed nav bar's own height exactly,
           so it's defined right next to it instead of split across files. */

        /* The two real motifs from Identity/logo-presentation.html's
           "motivi grafici" board (§5) -- Diagonale doppia and Mesh
           gradient -- applied for real to the whole main pane instead of
           staying small reference tiles, so every screen carries the
           identity and bordered boxes (solid black below) read clearly
           against it. Exact colors as specified, not the app's usual
           --accent tokens: mesh is #101418/#E0158C/#0B2F6B, diagonals
           are #E0158C (both bands, second one thinner/softer so they
           still read as two distinct stripes rather than one solid slab).
           Mesh runs top-right (magenta) to bottom-left (blue); both
           corners kept smaller/more transparent than the first pass so
           #101418 -- the base -- is what actually dominates the page. */
        [data-testid="stMain"] {
            background:
                /* Diagonale doppia, extended into a fuller set of parallel
                   magenta stripes at varying widths/opacities so the motif
                   runs across the whole page rather than one corner. */
                linear-gradient(135deg, transparent 40%, #E0158C 40%, #E0158C 42.5%, transparent 42.5%),
                linear-gradient(135deg, transparent 50%, rgba(224, 21, 140, 0.55) 50%, rgba(224, 21, 140, 0.55) 51.5%, transparent 51.5%),
                linear-gradient(135deg, transparent 22%, rgba(224, 21, 140, 0.75) 22%, rgba(224, 21, 140, 0.75) 23.4%, transparent 23.4%),
                linear-gradient(135deg, transparent 31%, rgba(224, 21, 140, 0.4) 31%, rgba(224, 21, 140, 0.4) 31.8%, transparent 31.8%),
                linear-gradient(135deg, transparent 60%, rgba(224, 21, 140, 0.45) 60%, rgba(224, 21, 140, 0.45) 61.6%, transparent 61.6%),
                linear-gradient(135deg, transparent 71%, rgba(224, 21, 140, 0.3) 71%, rgba(224, 21, 140, 0.3) 71.7%, transparent 71.7%),
                linear-gradient(135deg, transparent 84%, rgba(224, 21, 140, 0.5) 84%, rgba(224, 21, 140, 0.5) 85.3%, transparent 85.3%),
                radial-gradient(90% 70% at 100% 0%, #E0158C 0%, transparent 50%),
                radial-gradient(90% 80% at 0% 100%, #0B2F6B 0%, transparent 55%),
                #101418;
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
        /* st.metric(border=True) KPI tiles (Loads' Avg TL/Avg RPE/Team
           ACWR/Weekly monotony, Scout & Stats' General stats row) and the
           "How to read" expanders draw their own border but leave the fill
           transparent, so the page's mesh/diagonal background showed
           straight through them while every other box around them is
           solid. Same black fill as the rest. */
        [data-testid="stMetric"],
        [data-testid="stExpander"] details {
            background: var(--surface);
        }
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
    # Keyed (see Main_activity.py's own .st-key-css_nav for why) so this
    # pure-CSS container can be display:none'd without also hiding markdown
    # calls elsewhere that mix a <style> tag with real visible content.
    with st.container(key="css_custom"):
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
