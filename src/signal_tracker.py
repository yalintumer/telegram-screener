"""
Signal tracking and alert management system.

Features:
- Daily alert limit
- Symbol cooldown period
- Signal success tracking
- Performance metrics
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .logger import logger


class SignalTracker:
    """Track signals, manage alert limits, and measure performance"""

    def __init__(self, data_file: str = "signal_tracker.json"):
        self.data_file = Path(data_file)
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load signal tracking data from JSON file"""
        if not self.data_file.exists():
            return {
                "daily_alerts": {},  # date -> count
                "symbol_cooldown": {},  # symbol -> last_alert_date
                "signal_history": []  # list of signals with performance
            }

        try:
            with open(self.data_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error("signal_tracker.load_failed", error=str(e))
            return {"daily_alerts": {}, "symbol_cooldown": {}, "signal_history": []}

    def _save_data(self):
        """Save signal tracking data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error("signal_tracker.save_failed", error=str(e))

    def can_send_alert(self, symbol: str, daily_limit: int = 5, cooldown_days: int = 7) -> tuple[bool, str]:
        """
        Check if alert can be sent based on daily limit and cooldown.
        
        Args:
            symbol: Stock symbol
            daily_limit: Maximum alerts per day (default: 5)
            cooldown_days: Days to wait before alerting same symbol again (default: 7)
        
        Returns:
            (can_send, reason) tuple
        """
        today = datetime.now().date().isoformat()

        # Check daily limit
        today_count = self.data["daily_alerts"].get(today, 0)
        if today_count >= daily_limit:
            logger.warning("alert_limit_reached", date=today, count=today_count, limit=daily_limit)
            return False, f"Daily limit reached ({today_count}/{daily_limit})"

        # Check symbol cooldown
        if symbol in self.data["symbol_cooldown"]:
            last_alert = datetime.fromisoformat(self.data["symbol_cooldown"][symbol])
            days_since = (datetime.now() - last_alert).days

            if days_since < cooldown_days:
                logger.info("symbol_in_cooldown", symbol=symbol, days_since=days_since, required=cooldown_days)
                return False, f"Symbol in cooldown ({days_since}/{cooldown_days} days)"

        return True, "OK"

    def record_alert(self, symbol: str, signal_data: dict):
        """
        Record that an alert was sent.
        
        Args:
            symbol: Stock symbol
            signal_data: Dictionary with signal details (price, indicators, etc.)
        """
        today = datetime.now().date().isoformat()
        now = datetime.now().isoformat()

        # Increment daily count
        self.data["daily_alerts"][today] = self.data["daily_alerts"].get(today, 0) + 1

        # Update cooldown
        self.data["symbol_cooldown"][symbol] = now

        # Add to signal history
        signal_record = {
            "symbol": symbol,
            "date": now,
            "data": signal_data,
            "tracking_start": now
        }
        self.data["signal_history"].append(signal_record)

        # Clean old daily alerts (keep last 7 days)
        cutoff_date = (datetime.now() - timedelta(days=7)).date().isoformat()
        self.data["daily_alerts"] = {
            date: count for date, count in self.data["daily_alerts"].items()
            if date >= cutoff_date
        }

        self._save_data()
        logger.info("alert_recorded", symbol=symbol, daily_count=self.data["daily_alerts"][today])

    def get_daily_stats(self) -> dict:
        """Get daily alert statistics"""
        today = datetime.now().date().isoformat()
        return {
            "date": today,
            "alerts_sent": self.data["daily_alerts"].get(today, 0),
            "symbols_in_cooldown": len([
                s for s, date in self.data["symbol_cooldown"].items()
                if (datetime.now() - datetime.fromisoformat(date)).days < 7
            ]),
            "total_tracked_signals": len(self.data["signal_history"])
        }

    def get_symbol_cooldown_status(self, symbol: str) -> dict | None:
        """Get cooldown status for a specific symbol"""
        if symbol not in self.data["symbol_cooldown"]:
            return None

        last_alert = datetime.fromisoformat(self.data["symbol_cooldown"][symbol])
        days_since = (datetime.now() - last_alert).days

        return {
            "symbol": symbol,
            "last_alert": last_alert.isoformat(),
            "days_since": days_since,
            "can_alert_after": 7 - days_since if days_since < 7 else 0
        }

    def update_signal_performance(self, symbol: str, days_after: int = 5) -> dict | None:
        """
        Update performance for signals that are old enough to evaluate.
        
        Args:
            symbol: Stock symbol to update
            days_after: Days after signal to check performance (default: 5)
        
        Returns:
            Performance data or None if not ready
        """
        from .data_source_yfinance import daily_ohlc

        # Find signals for this symbol that are ready to evaluate
        now = datetime.now()
        updated_any = False

        for signal in self.data["signal_history"]:
            if signal["symbol"] != symbol:
                continue

            # Skip if already evaluated
            if "performance" in signal:
                continue

            # Check if enough time has passed
            signal_date = datetime.fromisoformat(signal["date"])
            days_since = (now - signal_date).days

            if days_since < days_after:
                continue

            # Get price data
            try:
                df = daily_ohlc(symbol, days=days_after + 10)
                if df is None or len(df) < days_after:
                    continue

                # Find signal price
                signal_price = signal["data"].get("price", 0)
                if signal_price == 0:
                    continue

                # Calculate performance (price change after N days)
                # Find the row closest to days_after from signal date
                target_date = signal_date + timedelta(days=days_after)

                # Convert both sides to pandas DatetimeIndex for safe comparison
                # This handles numpy.ndarray vs Timestamp incompatibility
                import pandas as pd
                target_ts = pd.Timestamp(target_date).normalize()

                # Convert index to DatetimeIndex, remove timezone, then normalize
                # This handles: DatetimeIndex, numpy.datetime64, timezone-aware
                idx = pd.DatetimeIndex(df.index)
                if idx.tz is not None:
                    idx = idx.tz_localize(None)  # Remove timezone
                idx = idx.normalize()

                # Now both are timezone-naive DatetimeIndex - comparison is safe
                future_prices = df.loc[idx >= target_ts]

                if len(future_prices) > 0:
                    future_price = float(future_prices["Close"].iloc[0])
                    price_change = ((future_price - signal_price) / signal_price) * 100

                    signal["performance"] = {
                        "days_after": days_after,
                        "entry_price": signal_price,
                        "exit_price": future_price,
                        "return_pct": round(price_change, 2),
                        "evaluated_at": now.isoformat()
                    }

                    updated_any = True
                    logger.info("signal_performance_updated",
                               symbol=symbol,
                               return_pct=price_change,
                               days_after=days_after)

            except Exception as e:
                logger.error("signal_performance_update_failed", symbol=symbol, error=str(e))

        if updated_any:
            self._save_data()

        return self.get_signal_stats(symbol)

    def get_signal_stats(self, symbol: str | None = None) -> dict:
        """
        Get performance statistics for signals.
        
        Args:
            symbol: Optional symbol to filter by
        
        Returns:
            Dictionary with performance metrics
        """
        signals = self.data["signal_history"]

        if symbol:
            signals = [s for s in signals if s["symbol"] == symbol]

        evaluated_signals = [s for s in signals if "performance" in s]

        if not evaluated_signals:
            return {
                "total_signals": len(signals),
                "evaluated": 0,
                "pending": len(signals),
                "avg_return": None,
                "win_rate": None
            }

        returns = [s["performance"]["return_pct"] for s in evaluated_signals]
        wins = len([r for r in returns if r > 0])

        return {
            "total_signals": len(signals),
            "evaluated": len(evaluated_signals),
            "pending": len(signals) - len(evaluated_signals),
            "avg_return": round(sum(returns) / len(returns), 2),
            "win_rate": round((wins / len(evaluated_signals)) * 100, 1),
            "best_return": max(returns) if returns else None,
            "worst_return": min(returns) if returns else None
        }

    def get_all_stats(self) -> dict:
        """
        Get performance statistics for all signals.

        This is a backwards-compatible alias for get_signal_stats(symbol=None).
        Used by analytics.py for weekly report generation.

        Returns:
            Dictionary with aggregate performance metrics for all signals
        """
        return self.get_signal_stats(symbol=None)
