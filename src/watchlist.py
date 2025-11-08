import json
from pathlib import Path
from datetime import date, timedelta

PATH = Path("watchlist.json")
SIGNAL_HISTORY_PATH = Path("signal_history.json")
GRACE_PERIOD_DAYS = 5  # Sinyal verdikten sonra tekrar listeye eklenebilmesi için gerekli gün sayısı
HISTORY_RETENTION_DAYS = 30  # Sinyal geçmişini ne kadar süre tutacağız


def _load() -> dict:
    if not PATH.exists():
        return {}
    return json.loads(PATH.read_text())


def _save(d: dict):
    PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def _load_signal_history() -> dict:
    """Load signal history from separate file"""
    if not SIGNAL_HISTORY_PATH.exists():
        return {}
    return json.loads(SIGNAL_HISTORY_PATH.read_text())


def _save_signal_history(d: dict):
    """Save signal history to separate file"""
    SIGNAL_HISTORY_PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def can_add_to_watchlist(symbol: str) -> tuple[bool, str]:
    """
    Check if a symbol can be added to watchlist (respects grace period from last signal).
    Returns (can_add: bool, reason: str)
    """
    history = _load_signal_history()
    if symbol not in history:
        return True, "No previous signal"
    
    last_signal = date.fromisoformat(history[symbol]["last_signal"])
    days_since = (date.today() - last_signal).days
    
    if days_since >= GRACE_PERIOD_DAYS:
        return True, f"Grace period expired ({days_since} days since last signal)"
    
    remaining = GRACE_PERIOD_DAYS - days_since
    return False, f"Grace period active ({remaining} days remaining)"


def add(symbols: list[str]) -> list[str]:
    w = _load()
    today = date.today().isoformat()
    added = []
    for s in symbols:
        can_add, reason = can_add_to_watchlist(s)
        if not can_add:
            print(f"⚠️  {s}: {reason}")
            continue
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
    # Remove from watchlist
    w = _load()
    if symbol in w:
        del w[symbol]
        _save(w)
    
    # Add to signal history for grace period tracking
    history = _load_signal_history()
    history[symbol] = {
        "last_signal": date.today().isoformat(),
        "count": history.get(symbol, {}).get("count", 0) + 1
    }
    _save_signal_history(history)


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


def cleanup_old_signals(retention_days: int = HISTORY_RETENTION_DAYS) -> int:
    """
    Remove old signal records from history.
    Returns count of removed records.
    """
    history = _load_signal_history()
    if not history:
        return 0
    
    today = date.today()
    removed_count = 0
    
    for symbol in list(history.keys()):
        last_signal = date.fromisoformat(history[symbol]["last_signal"])
        days_since = (today - last_signal).days
        
        if days_since >= retention_days:
            del history[symbol]
            removed_count += 1
    
    if removed_count > 0:
        _save_signal_history(history)
    
    return removed_count
