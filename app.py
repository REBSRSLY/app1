"""Entry point configured on Streamlit Cloud (Main file path: app.py).

The app's real structure lives in Main_activity.py: this file exists only so
we don't have to change the "Main file path" in the deploy settings.

Note: we use runpy instead of a plain `import Main_activity` because Python
only imports a module once per process. Streamlit, however, needs to re-run
the entire script on every interaction (every rerun): with a plain import,
Main_activity would only execute on the first load, and later interactions
would result in a blank page.
"""

import runpy

runpy.run_path("Main_activity.py", run_name="__main__")
