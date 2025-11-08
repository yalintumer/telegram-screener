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
    """Mark that a signal was sent for this symbol and REMOVE from watchlist"""
    w = _load()
    if symbol in w:
        del w[symbol]  # Sinyal gönderildikten sonra listeden kaldır
        _save(w)


def remove_symbol(symbol: str) -> bool:
    """Remove a symbol from watchlist. Returns True if removed."""
    w = _load()
    if symbol in w:
        del w[symbol]
        _save(w)
        return True
    return False


def can_send_signal(symbol: str) -> bool:
    """Check if symbol is in watchlist (always returns True if in list since we remove after signal)"""
    w = _load()
    return symbol in w  # Basit kontrol: listede varsa sinyal gönder
