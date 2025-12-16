"""Tests for signal_tracker module."""
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

from src.signal_tracker import SignalTracker


class TestSignalTrackerInit:
    """Tests for SignalTracker initialization."""

    def test_creates_default_data_when_file_not_exists(self, tmp_path):
        """Should create default data structure when file doesn't exist."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        assert tracker.data == {
            "daily_alerts": {},
            "symbol_cooldown": {},
            "signal_history": []
        }

    def test_loads_existing_data_from_file(self, tmp_path):
        """Should load existing data from file."""
        data_file = tmp_path / "signals.json"
        existing_data = {
            "daily_alerts": {"2024-01-01": 3},
            "symbol_cooldown": {"AAPL": "2024-01-01T10:00:00"},
            "signal_history": [{"symbol": "AAPL", "date": "2024-01-01T10:00:00"}]
        }
        data_file.write_text(json.dumps(existing_data))

        tracker = SignalTracker(data_file=str(data_file))

        assert tracker.data["daily_alerts"] == {"2024-01-01": 3}
        assert "AAPL" in tracker.data["symbol_cooldown"]

    def test_handles_corrupted_json_file(self, tmp_path):
        """Should return default data when JSON is corrupted."""
        data_file = tmp_path / "signals.json"
        data_file.write_text("invalid json {{{")

        tracker = SignalTracker(data_file=str(data_file))

        assert tracker.data == {
            "daily_alerts": {},
            "symbol_cooldown": {},
            "signal_history": []
        }


class TestCanSendAlert:
    """Tests for can_send_alert method."""

    def test_returns_true_when_no_limits_reached(self, tmp_path):
        """Should return True when no limits are reached."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        can_send, reason = tracker.can_send_alert("AAPL")

        assert can_send is True
        assert reason == "OK"

    def test_returns_false_when_daily_limit_reached(self, tmp_path):
        """Should return False when daily limit is reached."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        today = datetime.now().date().isoformat()
        tracker.data["daily_alerts"][today] = 5

        can_send, reason = tracker.can_send_alert("AAPL", daily_limit=5)

        assert can_send is False
        assert "Daily limit reached" in reason

    def test_returns_false_when_symbol_in_cooldown(self, tmp_path):
        """Should return False when symbol is in cooldown."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Set cooldown 3 days ago
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        tracker.data["symbol_cooldown"]["AAPL"] = three_days_ago

        can_send, reason = tracker.can_send_alert("AAPL", cooldown_days=7)

        assert can_send is False
        assert "cooldown" in reason.lower()

    def test_returns_true_when_cooldown_expired(self, tmp_path):
        """Should return True when cooldown has expired."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Set cooldown 8 days ago
        eight_days_ago = (datetime.now() - timedelta(days=8)).isoformat()
        tracker.data["symbol_cooldown"]["AAPL"] = eight_days_ago

        can_send, reason = tracker.can_send_alert("AAPL", cooldown_days=7)

        assert can_send is True
        assert reason == "OK"

    def test_custom_daily_limit(self, tmp_path):
        """Should respect custom daily limit."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        today = datetime.now().date().isoformat()
        tracker.data["daily_alerts"][today] = 10

        # Should fail with limit=10
        can_send, reason = tracker.can_send_alert("AAPL", daily_limit=10)
        assert can_send is False

        # Should pass with limit=15
        can_send, reason = tracker.can_send_alert("AAPL", daily_limit=15)
        assert can_send is True


class TestRecordAlert:
    """Tests for record_alert method."""

    def test_increments_daily_count(self, tmp_path):
        """Should increment daily alert count."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("AAPL", {"price": 150.0})

        today = datetime.now().date().isoformat()
        assert tracker.data["daily_alerts"][today] == 1

    def test_updates_symbol_cooldown(self, tmp_path):
        """Should update symbol cooldown timestamp."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("AAPL", {"price": 150.0})

        assert "AAPL" in tracker.data["symbol_cooldown"]

    def test_adds_to_signal_history(self, tmp_path):
        """Should add signal to history."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("AAPL", {"price": 150.0, "indicator": "WaveTrend"})

        assert len(tracker.data["signal_history"]) == 1
        signal = tracker.data["signal_history"][0]
        assert signal["symbol"] == "AAPL"
        assert signal["data"]["price"] == 150.0

    def test_persists_to_file(self, tmp_path):
        """Should save data to file."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("AAPL", {"price": 150.0})

        saved_data = json.loads(data_file.read_text())
        assert len(saved_data["signal_history"]) == 1

    def test_cleans_old_daily_alerts(self, tmp_path):
        """Should clean daily alerts older than 7 days."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Add old entry
        old_date = (datetime.now() - timedelta(days=10)).date().isoformat()
        tracker.data["daily_alerts"][old_date] = 5

        tracker.record_alert("AAPL", {"price": 150.0})

        # Old entry should be removed
        assert old_date not in tracker.data["daily_alerts"]


class TestGetDailyStats:
    """Tests for get_daily_stats method."""

    def test_returns_correct_stats(self, tmp_path):
        """Should return correct daily statistics."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        today = datetime.now().date().isoformat()
        tracker.data["daily_alerts"][today] = 3

        # Add some signals in cooldown
        now = datetime.now().isoformat()
        tracker.data["symbol_cooldown"] = {
            "AAPL": now,
            "GOOGL": now
        }
        tracker.data["signal_history"] = [
            {"symbol": "AAPL"},
            {"symbol": "GOOGL"},
            {"symbol": "MSFT"}
        ]

        stats = tracker.get_daily_stats()

        assert stats["alerts_sent"] == 3
        assert stats["symbols_in_cooldown"] == 2
        assert stats["total_tracked_signals"] == 3

    def test_handles_empty_data(self, tmp_path):
        """Should handle empty data gracefully."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        stats = tracker.get_daily_stats()

        assert stats["alerts_sent"] == 0
        assert stats["symbols_in_cooldown"] == 0
        assert stats["total_tracked_signals"] == 0


class TestGetSymbolCooldownStatus:
    """Tests for get_symbol_cooldown_status method."""

    def test_returns_none_when_symbol_not_in_cooldown(self, tmp_path):
        """Should return None when symbol has no cooldown."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        result = tracker.get_symbol_cooldown_status("AAPL")

        assert result is None

    def test_returns_cooldown_status(self, tmp_path):
        """Should return cooldown status for symbol."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        tracker.data["symbol_cooldown"]["AAPL"] = three_days_ago

        status = tracker.get_symbol_cooldown_status("AAPL")

        assert status["symbol"] == "AAPL"
        assert status["days_since"] == 3
        assert status["can_alert_after"] == 4  # 7 - 3 = 4 days left


class TestGetSignalStats:
    """Tests for get_signal_stats method."""

    def test_returns_empty_stats_when_no_signals(self, tmp_path):
        """Should return empty stats when no signals exist."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        stats = tracker.get_signal_stats()

        assert stats["total_signals"] == 0
        assert stats["evaluated"] == 0
        assert stats["pending"] == 0

    def test_returns_stats_for_specific_symbol(self, tmp_path):
        """Should return stats filtered by symbol."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.data["signal_history"] = [
            {"symbol": "AAPL", "performance": {"return_pct": 5.0}},
            {"symbol": "AAPL", "performance": {"return_pct": -2.0}},
            {"symbol": "GOOGL", "performance": {"return_pct": 10.0}}
        ]

        stats = tracker.get_signal_stats("AAPL")

        assert stats["total_signals"] == 2
        assert stats["evaluated"] == 2

    def test_calculates_avg_return_and_win_rate(self, tmp_path):
        """Should calculate average return and win rate."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.data["signal_history"] = [
            {"symbol": "AAPL", "performance": {"return_pct": 10.0}},
            {"symbol": "AAPL", "performance": {"return_pct": 5.0}},
            {"symbol": "AAPL", "performance": {"return_pct": -3.0}},
            {"symbol": "AAPL", "performance": {"return_pct": 8.0}}
        ]

        stats = tracker.get_signal_stats()

        assert stats["avg_return"] == 5.0  # (10 + 5 - 3 + 8) / 4
        assert stats["win_rate"] == 75.0  # 3/4 = 75%

    def test_returns_best_and_worst_return(self, tmp_path):
        """Should return best and worst returns."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.data["signal_history"] = [
            {"symbol": "AAPL", "performance": {"return_pct": 15.0}},
            {"symbol": "AAPL", "performance": {"return_pct": -5.0}},
            {"symbol": "AAPL", "performance": {"return_pct": 8.0}}
        ]

        stats = tracker.get_signal_stats()

        assert stats["best_return"] == 15.0
        assert stats["worst_return"] == -5.0

    def test_handles_pending_signals(self, tmp_path):
        """Should count pending (not evaluated) signals."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.data["signal_history"] = [
            {"symbol": "AAPL", "performance": {"return_pct": 5.0}},  # Evaluated
            {"symbol": "AAPL"},  # Pending (no performance)
            {"symbol": "GOOGL"}  # Pending
        ]

        stats = tracker.get_signal_stats()

        assert stats["total_signals"] == 3
        assert stats["evaluated"] == 1
        assert stats["pending"] == 2


class TestUpdateSignalPerformance:
    """Tests for update_signal_performance method."""

    def test_skips_already_evaluated_signals(self, tmp_path):
        """Should skip signals that already have performance data."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": old_date,
                "data": {"price": 150.0},
                "performance": {"return_pct": 5.0}  # Already evaluated
            }
        ]

        with patch('src.data_source_yfinance.daily_ohlc') as mock_ohlc:
            tracker.update_signal_performance("AAPL")
            mock_ohlc.assert_not_called()

    def test_skips_recent_signals(self, tmp_path):
        """Should skip signals that are too recent."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        recent_date = (datetime.now() - timedelta(days=2)).isoformat()
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": recent_date,
                "data": {"price": 150.0}
            }
        ]

        with patch('src.data_source_yfinance.daily_ohlc') as mock_ohlc:
            tracker.update_signal_performance("AAPL", days_after=5)
            mock_ohlc.assert_not_called()

    def test_updates_performance_for_ready_signals(self, tmp_path):
        """Should call daily_ohlc for signals old enough to evaluate."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": old_date,
                "data": {"price": 100.0}
            }
        ]

        # Mock daily_ohlc to verify it's called
        with patch('src.data_source_yfinance.daily_ohlc') as mock_ohlc:
            mock_ohlc.return_value = None  # Simulate no data
            tracker.update_signal_performance("AAPL", days_after=5)
            # Should have tried to fetch data
            mock_ohlc.assert_called_once()

    def test_handles_ohlc_failure_gracefully(self, tmp_path):
        """Should handle OHLC data fetch failure gracefully."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": old_date,
                "data": {"price": 100.0}
            }
        ]

        with patch('src.data_source_yfinance.daily_ohlc', return_value=None):
            # Should not raise
            tracker.update_signal_performance("AAPL", days_after=5)

        # Signal should remain without performance
        assert "performance" not in tracker.data["signal_history"][0]


class TestSaveDataErrorHandling:
    """Tests for _save_data error handling."""

    def test_handles_write_error_gracefully(self, tmp_path):
        """Should handle write errors without raising."""
        data_file = tmp_path / "nonexistent" / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # This should not raise
        tracker.record_alert("AAPL", {"price": 150.0})

        # Data should still be in memory
        assert len(tracker.data["signal_history"]) == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_zero_price(self, tmp_path):
        """Should handle zero price in signal data."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": old_date,
                "data": {"price": 0}  # Zero price
            }
        ]

        with patch('src.data_source_yfinance.daily_ohlc') as mock_ohlc:
            mock_ohlc.return_value = pd.DataFrame({'Close': [100.0]})
            tracker.update_signal_performance("AAPL", days_after=5)
            # Should not update performance because price is 0
            assert "performance" not in tracker.data["signal_history"][0]

    def test_multiple_alerts_same_day(self, tmp_path):
        """Should handle multiple alerts on same day."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("AAPL", {"price": 150.0})
        tracker.record_alert("GOOGL", {"price": 2800.0})
        tracker.record_alert("MSFT", {"price": 400.0})

        today = datetime.now().date().isoformat()
        assert tracker.data["daily_alerts"][today] == 3

    def test_special_characters_in_symbol(self, tmp_path):
        """Should handle symbols with special characters."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        tracker.record_alert("BRK.B", {"price": 350.0})

        assert "BRK.B" in tracker.data["symbol_cooldown"]
        assert tracker.data["signal_history"][0]["symbol"] == "BRK.B"


class TestGetAllStatsAlias:
    """Tests for get_all_stats backwards compatibility alias."""

    def test_get_all_stats_returns_same_as_get_signal_stats_none(self, tmp_path):
        """get_all_stats() should return identical result to get_signal_stats(None)."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Add some test signals
        tracker.record_alert("AAPL", {"price": 150.0})
        tracker.record_alert("GOOGL", {"price": 2800.0})

        all_stats = tracker.get_all_stats()
        signal_stats = tracker.get_signal_stats(symbol=None)

        assert all_stats == signal_stats

    def test_get_all_stats_with_performance_data(self, tmp_path):
        """get_all_stats() should include performance metrics when available."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Add signal with performance data
        tracker.data["signal_history"] = [
            {
                "symbol": "AAPL",
                "date": "2024-12-10T10:00:00",
                "signal_data": {"price": 150.0},
                "performance": {"return_pct": 5.2, "days_after": 5, "price_at_signal": 150.0}
            },
            {
                "symbol": "GOOGL",
                "date": "2024-12-10T10:00:00",
                "signal_data": {"price": 2800.0},
                "performance": {"return_pct": -2.1, "days_after": 5, "price_at_signal": 2800.0}
            }
        ]

        stats = tracker.get_all_stats()

        assert stats["total_signals"] == 2
        assert stats["evaluated"] == 2
        assert stats["pending"] == 0
        assert stats["avg_return"] is not None
        assert stats["win_rate"] is not None

    def test_get_all_stats_empty_history(self, tmp_path):
        """get_all_stats() should handle empty signal history."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        stats = tracker.get_all_stats()

        assert stats["total_signals"] == 0
        assert stats["evaluated"] == 0
        assert stats["pending"] == 0
        assert stats["avg_return"] is None
        assert stats["win_rate"] is None


class TestSignalPerformanceTimestampComparison:
    """Regression tests for numpy.ndarray vs Timestamp comparison bug."""

    def test_update_performance_with_datetime_index(self, tmp_path):
        """Should handle DatetimeIndex without numpy/Timestamp comparison error."""

        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        # Add a signal from 10 days ago
        signal_date = datetime.now() - timedelta(days=10)
        tracker.data["signal_history"] = [{
            "symbol": "TEST",
            "date": signal_date.isoformat(),
            "data": {"price": 100.0}
        }]

        # Mock daily_ohlc to return DataFrame with DatetimeIndex
        mock_df = pd.DataFrame({
            "Open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            "High": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5],
            "Volume": [1000000] * 7
        }, index=pd.DatetimeIndex([
            signal_date + timedelta(days=i) for i in range(7)
        ]))

        with patch("src.data_source_yfinance.daily_ohlc", return_value=mock_df):
            # This should NOT raise: '>=' not supported between 'numpy.ndarray' and 'Timestamp'
            tracker.update_signal_performance("TEST", days_after=5)

        # Verify performance was calculated
        assert tracker.data["signal_history"][0].get("performance") is not None
        perf = tracker.data["signal_history"][0]["performance"]
        assert "return_pct" in perf
        assert perf["days_after"] == 5

    def test_update_performance_with_numpy_datetime64_index(self, tmp_path):
        """Should handle numpy.datetime64 index without comparison error."""
        import numpy as np

        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        signal_date = datetime.now() - timedelta(days=10)
        tracker.data["signal_history"] = [{
            "symbol": "TEST",
            "date": signal_date.isoformat(),
            "data": {"price": 100.0}
        }]

        # Create DataFrame with numpy.datetime64 index (common from yfinance)
        dates = np.array([
            signal_date + timedelta(days=i) for i in range(7)
        ], dtype="datetime64[ns]")

        mock_df = pd.DataFrame({
            "Open": [100.0] * 7,
            "High": [101.0] * 7,
            "Low": [99.0] * 7,
            "Close": [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0],
            "Volume": [1000000] * 7
        }, index=dates)

        with patch("src.data_source_yfinance.daily_ohlc", return_value=mock_df):
            # Should not raise TypeError
            tracker.update_signal_performance("TEST", days_after=5)

        assert tracker.data["signal_history"][0].get("performance") is not None

    def test_update_performance_handles_timezone_aware_index(self, tmp_path):
        """Should handle timezone-aware DatetimeIndex."""
        data_file = tmp_path / "signals.json"
        tracker = SignalTracker(data_file=str(data_file))

        signal_date = datetime.now() - timedelta(days=10)
        tracker.data["signal_history"] = [{
            "symbol": "TEST",
            "date": signal_date.isoformat(),
            "data": {"price": 100.0}
        }]

        # Create timezone-aware index (like real yfinance data)
        dates = pd.date_range(
            start=signal_date,
            periods=7,
            freq="D",
            tz="America/New_York"
        )

        mock_df = pd.DataFrame({
            "Open": [100.0] * 7,
            "High": [101.0] * 7,
            "Low": [99.0] * 7,
            "Close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            "Volume": [1000000] * 7
        }, index=dates)

        with patch("src.data_source_yfinance.daily_ohlc", return_value=mock_df):
            # Should handle timezone conversion gracefully
            tracker.update_signal_performance("TEST", days_after=5)

        assert tracker.data["signal_history"][0].get("performance") is not None
