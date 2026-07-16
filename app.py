"""Punto di ingresso configurato su Streamlit Cloud (Main file path: app.py).

La struttura reale dell'app vive in Main_activity.py: questo file esiste solo
per non dover cambiare il "Main file path" nelle impostazioni di deploy.

Nota: usiamo runpy invece di un semplice `import Main_activity` perché Python
importa un modulo una sola volta per processo. Streamlit invece deve
rieseguire l'intero script ad ogni interazione (ogni rerun): con un import
semplice, Main_activity si eseguirebbe solo al primo caricamento e le
interazioni successive risulterebbero in una pagina vuota.
"""

import runpy

runpy.run_path("Main_activity.py", run_name="__main__")
