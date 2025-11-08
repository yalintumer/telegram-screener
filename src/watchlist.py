import json
from pathlib import Path
from datetime import date

PATH = Path("watchlist.json")


def _load() -> dict:
    if not PATH.exists():
        return {}
    return json.loads(PATH.read_text())


def _save(d: dict):
    PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def add(symbols: list[str]) -> list[str]:
    w = _load()
    today = date.today().isoformat()
    added = []
    for s in symbols:
        if s not in w:
            w[s] = {"added": today}
            added.append(s)
    _save(w)
    return added


def prune(max_days: int) -> list[str]:
    w = _load()
    removed = []
    today = date.today()
    for s, meta in list(w.items()):
        added = date.fromisoformat(meta.get("added"))
        if (today - added).days >= max_days:
            removed.append(s)
            del w[s]
    _save(w)
    return removed


def all_symbols() -> list[str]:
    return list(_load().keys())
