import json
from pathlib import Path
from datetime import date, timedelta
from .logger import logger
from .exceptions import WatchlistError

PATH = Path("watchlist.json")
SIGNAL_HISTORY_PATH = Path("signal_history.json")
GRACE_PERIOD_DAYS = 5  # Sinyal verdikten sonra tekrar listeye eklenebilmesi için gerekli gün sayısı
HISTORY_RETENTION_DAYS = 30  # Sinyal geçmişini ne kadar süre tutacağız


def _load() -> dict:
    """Load watchlist from JSON file"""
    if not PATH.exists():
        return {}
    try:
        content = PATH.read_text()
        if not content.strip():
            return {}
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("watchlist.load.json_error", error=str(e))
        raise WatchlistError(f"Corrupted watchlist file: {e}", {"path": str(PATH)})
    except Exception as e:
        logger.error("watchlist.load.error", error=str(e))
        raise WatchlistError(f"Failed to load watchlist: {e}", {"path": str(PATH)})


def _save(d: dict):
    """Save watchlist to JSON file"""
    try:
        PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("watchlist.save.error", error=str(e))
        raise WatchlistError(f"Failed to save watchlist: {e}", {"path": str(PATH)})


def _load_signal_history() -> dict:
    """Load signal history from separate file"""
    if not SIGNAL_HISTORY_PATH.exists():
        return {}
    try:
        content = SIGNAL_HISTORY_PATH.read_text()
        if not content.strip():
            return {}
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("signal_history.load.json_error", error=str(e))
        raise WatchlistError(f"Corrupted signal history file: {e}", {"path": str(SIGNAL_HISTORY_PATH)})
    except Exception as e:
        logger.error("signal_history.load.error", error=str(e))
        raise WatchlistError(f"Failed to load signal history: {e}", {"path": str(SIGNAL_HISTORY_PATH)})


def _save_signal_history(d: dict):
    """Save signal history to separate file"""
    try:
        SIGNAL_HISTORY_PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("signal_history.save.error", error=str(e))
        raise WatchlistError(f"Failed to save signal history: {e}", {"path": str(SIGNAL_HISTORY_PATH)})


def can_add_to_watchlist(symbol: str) -> tuple[bool, str]:
    """
    Check if a symbol can be added to watchlist (respects grace period from last signal).
    Grace period is calculated in business days (weekdays only).
    Returns (can_add: bool, reason: str)
    """
    history = _load_signal_history()
    if symbol not in history:
        return True, "No previous signal"
    
    last_signal = date.fromisoformat(history[symbol]["last_signal"])
    business_days_since = _business_days_between(last_signal, date.today())
    
    if business_days_since >= GRACE_PERIOD_DAYS:
        return True, f"Grace period expired ({business_days_since} business days since last signal)"
    
    remaining = GRACE_PERIOD_DAYS - business_days_since
    return False, f"Grace period active ({remaining} business days remaining)"


def add(symbols: list[str], skip_grace_check: bool = False) -> list[str]:
    """
    Add symbols to watchlist
    
    Args:
        symbols: List of ticker symbols to add
        skip_grace_check: If True, skip grace period validation (used when adding from local Mac)
                         If False, enforce grace period (used when VM processes signals)
    
    Returns:
        List of symbols that were actually added
    """
    w = _load()
    today = date.today().isoformat()
    added = []
    for s in symbols:
        # Only check grace period if not skipped
        if not skip_grace_check:
            can_add, reason = can_add_to_watchlist(s)
            if not can_add:
                print(f"⚠️  {s}: {reason}")
                continue
        
        if s not in w:
            w[s] = {"added": today}
            added.append(s)
    _save(w)
    return added


def _business_days_between(start_date: date, end_date: date) -> int:
    """
    Calculate business days (weekdays) between two dates.
    
    Args:
        start_date: Start date (inclusive in count)
        end_date: End date (exclusive from count)
    
    Returns:
        Number of weekdays between dates
        
    Example:
        Monday to Friday (same week) = 5 business days
        Friday to Monday (weekend) = 0 business days
        
    Edge cases:
        - If start_date >= end_date, returns 0
        - Weekends (Saturday, Sunday) are not counted
    """
    if start_date >= end_date:
        return 0
    
    business_days = 0
    current = start_date
    
    while current < end_date:
        # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if current.weekday() < 5:  # Monday to Friday
            business_days += 1
        current += timedelta(days=1)
    
    return business_days


def prune(max_days: int) -> list[str]:
    """
    Remove symbols older than max_days (business days).
    
    Logic: If a symbol was added on Monday and max_days=5:
      - Monday (day 1), Tuesday (day 2), ... Friday (day 5)
      - On Monday (day 6), it gets removed
      
    This means: business_days > max_days (not >=)
    """
    w = _load()
    removed = []
    today = date.today()
    for s, meta in list(w.items()):
        added = date.fromisoformat(meta.get("added"))
        business_days = _business_days_between(added, today)
        # Changed: > instead of >= so the symbol stays for max_days full business days
        if business_days > max_days:
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
    """
    Check if we can send a signal for this symbol (respects grace period).
    Used by scan logic to filter symbols before processing.
    
    Returns True if:
    1. Symbol is in watchlist, AND
    2. Either no previous signal OR grace period has expired
    """
    w = _load()
    if symbol not in w:
        return False
    
    history = _load_signal_history()
    if symbol not in history:
        return True  # No previous signal, can send
    
    last_signal = date.fromisoformat(history[symbol]["last_signal"])
    business_days_since = _business_days_between(last_signal, date.today())
    
    return business_days_since >= GRACE_PERIOD_DAYS


def can_send_signal_with_reason(symbol: str) -> tuple[bool, str]:
    """
    Check if we can send a signal with detailed reason.
    Returns (can_send: bool, reason: str)
    """
    w = _load()
    if symbol not in w:
        return False, "Not in watchlist"
    
    history = _load_signal_history()
    if symbol not in history:
        return True, "No previous signal"
    
    last_signal = date.fromisoformat(history[symbol]["last_signal"])
    business_days_since = _business_days_between(last_signal, date.today())
    
    if business_days_since >= GRACE_PERIOD_DAYS:
        return True, f"Grace period expired ({business_days_since} days since last signal)"
    
    remaining = GRACE_PERIOD_DAYS - business_days_since
    return False, f"Grace period active ({remaining} business days remaining)"


def cleanup_old_signals(retention_days: int = HISTORY_RETENTION_DAYS) -> int:
    """
    Remove old signal records from history.
    Uses business days for consistency with grace period logic.
    Returns count of removed records.
    """
    history = _load_signal_history()
    if not history:
        return 0
    
    today = date.today()
    removed_count = 0
    
    for symbol in list(history.keys()):
        last_signal = date.fromisoformat(history[symbol]["last_signal"])
        # Changed: Use business days instead of calendar days
        business_days_since = _business_days_between(last_signal, today)
        
        if business_days_since > retention_days:
            del history[symbol]
            removed_count += 1
    
    if removed_count > 0:
        _save_signal_history(history)
    
    return removed_count
