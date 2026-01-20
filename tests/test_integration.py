"""Integration tests - smoke tests for full system workflow."""

import json

import pandas as pd

from src.analytics import Analytics
from src.cache import MarketCapCache
from src.cli import create_parser

# Import modules to test integration
from src.health import HealthCheck
from src.signal_tracker import SignalTracker


class TestModuleImports:
    """Test that all modules can be imported without errors."""

    def test_import_all_core_modules(self):
        """Should import all core modules successfully."""
        from src import (
            analytics,
            config,
            health,
        )

        assert config is not None
        assert health is not None
        assert analytics is not None

    def test_import_data_sources(self):
        """Should import data source modules."""
        from src import data_source_yfinance

        assert data_source_yfinance is not None

    def test_import_client_modules(self):
        """Should import client modules."""
        from src import notion_client, telegram_client

        assert telegram_client is not None
        assert notion_client is not None


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_initialization(self, tmp_path):
        """Should initialize health check with default values."""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file)

        # Trigger a write
        health.scan_started(1)

        assert health_file.exists()
        data = json.loads(health_file.read_text())
        assert data["status"] == "scanning"

    def test_health_check_heartbeat(self, tmp_path):
        """Should update health file on heartbeat."""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file)

        health.scan_started(1)
        health.heartbeat()

        # Should not raise, file should exist
        assert health_file.exists()

    def test_health_check_scan_completed(self, tmp_path):
        """Should track scan completion."""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file)

        health.scan_started(1)
        health.scan_completed(symbols_scanned=100, signals_found=5, duration_seconds=10.5)

        # Verify file updated
        data = json.loads(health_file.read_text())
        assert data["status"] == "healthy"
        assert data["scan_count"] == 1


class TestCLI:
    """Test CLI argument parsing."""

    def test_parser_creates_successfully(self):
        """Should create argument parser."""
        parser = create_parser()
        assert parser is not None

    def test_once_flag(self):
        """Should parse --once flag."""
        parser = create_parser()
        args = parser.parse_args(["--once"])
        assert args.once is True

    def test_market_scan_flag(self):
        """Should parse --market-scan flag."""
        parser = create_parser()
        args = parser.parse_args(["--market-scan"])
        assert args.market_scan is True

    def test_wavetrend_flag(self):
        """Should parse --wavetrend flag."""
        parser = create_parser()
        args = parser.parse_args(["--wavetrend"])
        assert args.wavetrend is True

    def test_interval_argument(self):
        """Should parse --interval argument."""
        parser = create_parser()
        args = parser.parse_args(["--interval", "7200"])
        assert args.interval == 7200

    def test_default_values(self):
        """Should have correct default values."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.interval == 3600
        assert args.once is False


class TestSmokeTestFullCycle:
    """Smoke test for full application cycle."""

    def test_can_initialize_all_components(self, tmp_path):
        """Should initialize all components without errors."""
        # Create temp files
        health_file = tmp_path / "health.json"
        analytics_file = tmp_path / "analytics.json"
        cache_file = tmp_path / "cache.json"
        signal_file = tmp_path / "signals.json"

        # Initialize components
        _ = HealthCheck(health_file)  # noqa: F841
        analytics = Analytics(str(analytics_file))
        cache = MarketCapCache(str(cache_file))
        signals = SignalTracker(str(signal_file))

        # Verify all initialized
        assert analytics.data["market_scans"] == []
        assert cache.cache == {}
        assert signals.data["signal_history"] == []

    def test_components_work_together(self, tmp_path):
        """Should have components that work together."""
        health_file = tmp_path / "health.json"
        analytics_file = tmp_path / "analytics.json"
        cache_file = tmp_path / "cache.json"
        signal_file = tmp_path / "signals.json"

        health = HealthCheck(health_file)
        analytics = Analytics(str(analytics_file))
        cache = MarketCapCache(str(cache_file))
        signals = SignalTracker(str(signal_file))

        # Simulate workflow
        health.scan_started(1)
        analytics.record_market_scan(found=100, added=5, updated=10)
        cache.set("AAPL", 3000000000000)

        can_alert, _ = signals.can_send_alert("AAPL")
        assert can_alert is True

        signals.record_alert("AAPL", {"price": 150.0})
        health.heartbeat()

        # Verify state
        assert len(analytics.data["market_scans"]) == 1
        assert cache.get("AAPL") == 3000000000000
        assert len(signals.data["signal_history"]) == 1

    def test_scan_functions_exist(self):
        """Should have properly structured scan functions."""
        from src.scanner import run_continuous, run_market_scan, run_wavetrend_scan

        # These functions should exist and be callable
        assert callable(run_market_scan)
        assert callable(run_wavetrend_scan)
        assert callable(run_continuous)


class TestDataFlowIntegration:
    """Test data flow between components."""

    def test_signal_tracker_to_analytics(self, tmp_path):
        """Should flow data from signal tracker to analytics."""
        analytics_file = tmp_path / "analytics.json"
        signal_file = tmp_path / "signals.json"

        _ = Analytics(str(analytics_file))  # noqa: F841
        signals = SignalTracker(str(signal_file))

        # Record some signals
        signals.record_alert("AAPL", {"price": 150.0})
        signals.record_alert("GOOGL", {"price": 2800.0})

        # Analytics should be able to use signal stats
        stats = signals.get_signal_stats()

        assert stats["total_signals"] == 2

    def test_cache_persistence_across_instances(self, tmp_path):
        """Should persist cache data across instances."""
        cache_file = tmp_path / "cache.json"

        # First instance
        cache1 = MarketCapCache(str(cache_file))
        cache1.set("AAPL", 3000000000000)
        cache1.set("GOOGL", 2000000000000)

        # Second instance (simulates restart)
        cache2 = MarketCapCache(str(cache_file))

        assert cache2.get("AAPL") == 3000000000000
        assert cache2.get("GOOGL") == 2000000000000


class TestErrorHandling:
    """Test error handling across components."""

    def test_components_handle_missing_files(self, tmp_path):
        """Should handle missing files gracefully."""
        nonexistent = tmp_path / "nonexistent"

        # These should not raise
        analytics = Analytics(str(nonexistent / "analytics.json"))
        cache = MarketCapCache(str(nonexistent / "cache.json"))
        signals = SignalTracker(str(nonexistent / "signals.json"))

        # Should have default data
        assert analytics.data["market_scans"] == []
        assert cache.cache == {}
        assert signals.data["signal_history"] == []

    def test_components_handle_corrupted_files(self, tmp_path):
        """Should handle corrupted JSON files gracefully."""
        corrupted_file = tmp_path / "corrupted.json"
        corrupted_file.write_text("not valid json {{{")

        # These should not raise
        analytics = Analytics(str(corrupted_file))
        cache = MarketCapCache(str(corrupted_file))
        signals = SignalTracker(str(corrupted_file))

        # Should have default data
        assert analytics.data["market_scans"] == []
        assert cache.cache == {}
        assert signals.data["signal_history"] == []


class TestIndicatorIntegration:
    """Test indicator calculations integration."""

    def test_indicator_functions_available(self):
        """Should have indicator functions available."""
        from src.indicators import (
            mfi,
            rsi,
            stochastic_rsi,
            wavetrend,
        )

        assert callable(rsi)
        assert callable(mfi)
        assert callable(wavetrend)
        assert callable(stochastic_rsi)

    def test_indicator_with_sample_data(self):
        """Should calculate indicators with sample data."""
        from src.indicators import rsi

        # Create sample close prices
        close = pd.Series([100 + i + (i % 5) for i in range(50)])

        # Calculate RSI
        result = rsi(close)

        # Should return series with values
        assert len(result) == len(close)
        # RSI should be between 0 and 100 (after warmup period)
        valid_values = result.dropna()
        assert all(0 <= v <= 100 for v in valid_values)


class TestFiltersIntegration:
    """Test filters module integration."""

    def test_filter_functions_available(self):
        """Should have filter functions available."""
        from src.filters import (
            check_market_filter,
            check_wavetrend_signal,
        )

        assert callable(check_market_filter)
        assert callable(check_wavetrend_signal)


class TestConstantsAvailable:
    """Test that constants are properly defined."""

    def test_all_constants_available(self):
        """Should have all required constants."""
        from src.constants import (
            BATCH_SLEEP_SECONDS,
            MFI_PERIOD,
            SIGNAL_LOOKBACK_DAYS,
            STOCH_RSI_PERIOD,
        )

        assert STOCH_RSI_PERIOD > 0
        assert MFI_PERIOD > 0
        assert SIGNAL_LOOKBACK_DAYS > 0
        assert BATCH_SLEEP_SECONDS >= 0
