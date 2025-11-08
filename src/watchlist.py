import json
from pathlib import Path
from datetime import date, timedelta

PATH = Path("watchlist.json")
GRACE_PERIOD_DAYS = 5  # Aynı sembol için tekrar sinyal göndermeme süresi


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


def mark_signal_sent(symbol: str):
    """Mark that a signal was sent for this symbol today"""
    w = _load()
    if symbol in w:
        w[symbol]["last_signal"] = date.today().isoformat()
        _save(w)


def can_send_signal(symbol: str) -> bool:
    """Check if we can send a signal for this symbol (grace period check)"""
    w = _load()
    if symbol not in w:
        return False
    
    last_signal = w[symbol].get("last_signal")
    if not last_signal:
        return True  # Hiç sinyal gönderilmemiş
    
    last_date = date.fromisoformat(last_signal)
    days_since = (date.today() - last_date).days
    
    return days_since >= GRACE_PERIOD_DAYS
