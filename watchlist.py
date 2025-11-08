import json, os, datetime as dt

PATH = "watchlist.json"

def load():
    return json.load(open(PATH)) if os.path.exists(PATH) else {}

def save(data):
    with open(PATH, "w") as f: json.dump(data, f, indent=2)

def add(symbols):
    w = load()
    today = dt.date.today().isoformat()
    for s in symbols:
        if s not in w:
            w[s] = {"added": today}
    save(w)

def prune(max_days):
    w = load()
    today = dt.date.today()
    removed = []
    for s, meta in list(w.items()):
        if (today - dt.date.fromisoformat(meta["added"])).days >= max_days:
            removed.append(s)
            del w[s]
    save(w)
    return removed

def all_symbols():
    return list(load().keys())