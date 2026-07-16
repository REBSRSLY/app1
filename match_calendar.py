"""Static match calendar for the 2023/24 season (Vero Volley Milano, women's A1).

Sourced from the public season record (Serie A1, Coppa Italia, Supercoppa,
CEV Champions League, playoffs) and cross-checked date-by-date against the
45 match sheets in anonymized_matches_F.xlsx — every date lines up exactly.
Score is always written as Milano-Opponent sets.
"""

MATCHES = [
    {"date": "23-10-08", "competition": "Serie A1", "round": "andata", "opponent": "Busto Arsizio", "home": True, "score": "3-0"},
    {"date": "23-10-14", "competition": "Serie A1", "round": "andata", "opponent": "Trentino", "home": False, "score": "1-3"},
    {"date": "23-10-22", "competition": "Serie A1", "round": "andata", "opponent": "Scandicci", "home": True, "score": "3-2"},
    {"date": "23-10-28", "competition": "Supercoppa Italiana", "round": "finale", "opponent": "Conegliano", "home": False, "score": "1-3"},
    {"date": "23-11-01", "competition": "Serie A1", "round": "andata", "opponent": "Bergamo", "home": False, "score": "1-3"},
    {"date": "23-11-05", "competition": "Serie A1", "round": "andata", "opponent": "Conegliano", "home": False, "score": "1-3"},
    {"date": "23-11-09", "competition": "Champions League", "round": "girone", "opponent": "Jedinstvo Stara Pazova", "home": True, "score": "3-0"},
    {"date": "23-11-12", "competition": "Serie A1", "round": "andata", "opponent": "Novara", "home": False, "score": "1-3"},
    {"date": "23-11-14", "competition": "Champions League", "round": "girone", "opponent": "Mulhouse", "home": False, "score": "0-3"},
    {"date": "23-11-19", "competition": "Serie A1", "round": "andata", "opponent": "Pinerolo", "home": True, "score": "3-0"},
    {"date": "23-11-22", "competition": "Serie A1", "round": "andata", "opponent": "Chieri", "home": False, "score": "3-0"},
    {"date": "23-11-26", "competition": "Serie A1", "round": "andata", "opponent": "Roma", "home": False, "score": "0-3"},
    {"date": "23-11-29", "competition": "Champions League", "round": "girone", "opponent": "VakıfBank", "home": False, "score": "0-3"},
    {"date": "23-12-03", "competition": "Serie A1", "round": "andata", "opponent": "Casalmaggiore", "home": False, "score": "3-2"},
    {"date": "23-12-06", "competition": "Champions League", "round": "girone", "opponent": "Mulhouse", "home": True, "score": "3-1"},
    {"date": "23-12-10", "competition": "Serie A1", "round": "andata", "opponent": "Cuneo", "home": False, "score": "0-3"},
    {"date": "23-12-17", "competition": "Serie A1", "round": "andata", "opponent": "Firenze", "home": False, "score": "0-3"},
    {"date": "23-12-23", "competition": "Serie A1", "round": "andata", "opponent": "Megavolley", "home": True, "score": "3-0"},
    {"date": "23-12-26", "competition": "Serie A1", "round": "ritorno", "opponent": "Busto Arsizio", "home": False, "score": "1-3"},
    {"date": "24-01-07", "competition": "Serie A1", "round": "ritorno", "opponent": "Trentino", "home": True, "score": "3-0"},
    {"date": "24-01-10", "competition": "Champions League", "round": "girone", "opponent": "Jedinstvo Stara Pazova", "home": False, "score": "0-3"},
    {"date": "24-01-13", "competition": "Serie A1", "round": "ritorno", "opponent": "Scandicci", "home": False, "score": "0-3"},
    {"date": "24-01-16", "competition": "Champions League", "round": "girone", "opponent": "VakıfBank", "home": True, "score": "2-3"},
    {"date": "24-01-21", "competition": "Serie A1", "round": "ritorno", "opponent": "Chieri", "home": False, "score": "2-3"},
    {"date": "24-01-24", "competition": "Coppa Italia", "round": "quarti", "opponent": "Roma", "home": True, "score": "3-0"},
    {"date": "24-01-28", "competition": "Serie A1", "round": "ritorno", "opponent": "Bergamo", "home": True, "score": "3-1"},
    {"date": "24-02-04", "competition": "Serie A1", "round": "ritorno", "opponent": "Conegliano", "home": False, "score": "3-0"},
    {"date": "24-02-10", "competition": "Serie A1", "round": "ritorno", "opponent": "Novara", "home": True, "score": "2-3"},
    {"date": "24-02-17", "competition": "Coppa Italia", "round": "semifinale", "opponent": "Scandicci", "home": True, "score": "3-2"},
    {"date": "24-02-18", "competition": "Coppa Italia", "round": "finale", "opponent": "Conegliano", "home": False, "score": "2-3"},
    {"date": "24-02-20", "competition": "Champions League", "round": "quarti andata", "opponent": "ŁKS Łódź", "home": False, "score": "1-3"},
    {"date": "24-02-25", "competition": "Serie A1", "round": "ritorno", "opponent": "Pinerolo", "home": False, "score": "2-3"},
    {"date": "24-02-29", "competition": "Champions League", "round": "quarti ritorno", "opponent": "ŁKS Łódź", "home": True, "score": "3-0"},
    {"date": "24-03-03", "competition": "Serie A1", "round": "ritorno", "opponent": "Roma", "home": False, "score": "3-2"},
    {"date": "24-03-06", "competition": "Serie A1", "round": "ritorno", "opponent": "Casalmaggiore", "home": False, "score": "3-2"},
    {"date": "24-03-09", "competition": "Serie A1", "round": "ritorno", "opponent": "Cuneo", "home": False, "score": "3-0"},
    {"date": "24-03-12", "competition": "Champions League", "round": "semifinale andata", "opponent": "Fenerbahçe", "home": True, "score": "3-0"},
    {"date": "24-03-16", "competition": "Serie A1", "round": "ritorno", "opponent": "Firenze", "home": True, "score": "3-1"},
    {"date": "24-03-19", "competition": "Champions League", "round": "semifinale ritorno", "opponent": "Fenerbahçe", "home": False, "score": "3-1"},
    {"date": "24-03-24", "competition": "Serie A1", "round": "ritorno", "opponent": "Megavolley", "home": False, "score": "3-0"},
    {"date": "24-03-27", "competition": "Playoff scudetto", "round": "quarti gara 1", "opponent": "Pinerolo", "home": True, "score": "3-2"},
    {"date": "24-03-31", "competition": "Playoff scudetto", "round": "quarti gara 2", "opponent": "Pinerolo", "home": False, "score": "1-3"},
    {"date": "24-04-06", "competition": "Playoff scudetto", "round": "semifinale gara 1", "opponent": "Scandicci", "home": False, "score": "0-3"},
    {"date": "24-04-10", "competition": "Playoff scudetto", "round": "semifinale gara 2", "opponent": "Scandicci", "home": True, "score": "0-3"},
    {"date": "24-05-05", "competition": "Champions League", "round": "finale", "opponent": "Conegliano", "home": False, "score": "2-3"},
]

MATCH_BY_DATE = {m["date"]: m for m in MATCHES}
