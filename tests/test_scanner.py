"""Tests for scanner module."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.scanner import (
    run_continuous,
    run_market_scan,
    run_wavetrend_scan,
    update_signal_performance,
)


class TestUpdateSignalPerformance:
    """Tests for update_signal_performance function."""

    def test_returns_dict_with_updated_and_failed(self):
        """Should return dict with updated and failed counts."""
        mock_tracker = Mock()
        mock_tracker.data = {"signal_history": []}

        result = update_signal_performance(mock_tracker)

        assert isinstance(result, dict)
        assert 'updated' in result
        assert 'failed' in result

    def test_skips_signals_with_performance(self):
        """Should skip signals that already have performance data."""
        mock_tracker = Mock()
        mock_tracker.data = {
            "signal_history": [
                {"symbol": "AAPL", "performance": {"return": 5.0}}
            ]
        }

        result = update_signal_performance(mock_tracker)

        assert result['updated'] == 0
        mock_tracker.update_signal_performance.assert_not_called()

    def test_skips_recent_signals(self):
        """Should skip signals that are less than lookback_days old."""
        today = datetime.now().isoformat()
        mock_tracker = Mock()
        mock_tracker.data = {
            "signal_history": [
                {"symbol": "AAPL", "date": today}
            ]
        }

        result = update_signal_performance(mock_tracker, lookback_days=7)

        assert result['updated'] == 0


class TestRunMarketScan:
    """Tests for run_market_scan function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        cfg = Mock()
        cfg.notion.api_token = "test_token"
        cfg.notion.database_id = "db_id"
        cfg.notion.signals_database_id = "signals_id"
        cfg.notion.buy_database_id = "buy_id"
        cfg.telegram.bot_token = "bot_token"
        cfg.telegram.chat_id = "chat_id"
        return cfg

    def test_returns_dict_on_success(self, mock_config):
        """Should return dict with scan statistics."""
        with patch('src.scanner.MarketCapCache') as mock_cache, \
             patch('src.scanner.NotionClient') as mock_notion, \
             patch('src.scanner.get_sp500_symbols', return_value=['AAPL', 'MSFT']), \
             patch('src.scanner.check_market_filter', return_value=None), \
             patch('src.scanner.SignalTracker'), \
             patch('src.scanner.Analytics'), \
             patch('src.scanner.NotionBackup') as mock_backup:

            mock_notion.return_value.get_all_symbols.return_value = []
            mock_cache.return_value.get_stats.return_value = {'valid_entries': 0}
            mock_backup.return_value.cleanup_old_backups.return_value = 0
            mock_backup.return_value.get_backup_stats.return_value = {'total_backups': 0, 'total_size_mb': 0}

            result = run_market_scan(mock_config)

        assert result is not None
        assert 'symbols_checked' in result
        assert 'added' in result

    def test_skips_existing_symbols(self, mock_config):
        """Should skip symbols already in signals/buy database."""
        with patch('src.scanner.MarketCapCache') as mock_cache, \
             patch('src.scanner.NotionClient') as mock_notion, \
             patch('src.scanner.get_sp500_symbols', return_value=['AAPL', 'MSFT']), \
             patch('src.scanner.check_market_filter') as mock_filter, \
             patch('src.scanner.SignalTracker'), \
             patch('src.scanner.Analytics'), \
             patch('src.scanner.NotionBackup') as mock_backup:

            # AAPL already exists
            mock_notion.return_value.get_all_symbols.return_value = ['AAPL']
            mock_cache.return_value.get_stats.return_value = {'valid_entries': 0}
            mock_backup.return_value.cleanup_old_backups.return_value = 0
            mock_backup.return_value.get_backup_stats.return_value = {'total_backups': 0, 'total_size_mb': 0}
            mock_filter.return_value = None

            result = run_market_scan(mock_config)

        # AAPL should be skipped, MSFT should be checked
        assert result['skipped'] == 1


class TestRunWavetrendScan:
    """Tests for run_wavetrend_scan function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        cfg = Mock()
        cfg.notion.api_token = "test_token"
        cfg.notion.database_id = "db_id"
        cfg.notion.signals_database_id = "signals_id"
        cfg.notion.buy_database_id = "buy_id"
        cfg.telegram.bot_token = "bot_token"
        cfg.telegram.chat_id = "chat_id"
        return cfg

    def test_returns_dict_when_empty(self, mock_config):
        """Should return dict even when signals database is empty."""
        with patch('src.scanner.NotionClient') as mock_notion, \
             patch('src.scanner.TelegramClient'), \
             patch('src.scanner.SignalTracker') as mock_tracker:

            mock_notion.return_value.cleanup_old_signals.return_value = 0
            mock_notion.return_value.get_signals.return_value = ([], {})
            mock_tracker.return_value.get_daily_stats.return_value = {
                'alerts_sent': 0,
                'symbols_in_cooldown': 0
            }

            result = run_wavetrend_scan(mock_config)

        assert result is not None
        assert result['checked'] == 0
        assert result['confirmed'] == 0

    def test_skips_symbols_in_buy_database(self, mock_config):
        """Should skip symbols already in buy database."""
        with patch('src.scanner.NotionClient') as mock_notion, \
             patch('src.scanner.TelegramClient'), \
             patch('src.scanner.SignalTracker') as mock_tracker, \
             patch('src.scanner.check_wavetrend_signal') as mock_wt, \
             patch('src.scanner.Analytics'):

            mock_notion.return_value.cleanup_old_signals.return_value = 0
            mock_notion.return_value.get_signals.return_value = (['AAPL', 'MSFT'], {'AAPL': 'page1', 'MSFT': 'page2'})
            mock_notion.return_value._get_symbols_from_database.return_value = ['AAPL']  # Already in buy
            mock_tracker.return_value.get_daily_stats.return_value = {
                'alerts_sent': 0,
                'symbols_in_cooldown': 0
            }
            mock_wt.return_value = False

            result = run_wavetrend_scan(mock_config)

        assert result['skipped'] == 1


class TestRunContinuous:
    """Tests for run_continuous function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        cfg = Mock()
        cfg.notion.api_token = "test_token"
        cfg.notion.database_id = "db_id"
        cfg.notion.signals_database_id = "signals_id"
        cfg.notion.buy_database_id = "buy_id"
        cfg.telegram.bot_token = "bot_token"
        cfg.telegram.chat_id = "chat_id"
        return cfg

    def test_stops_on_keyboard_interrupt(self, mock_config):
        """Should stop gracefully on KeyboardInterrupt."""
        with patch('src.scanner.get_health') as mock_health, \
             patch('src.scanner.set_correlation_id'), \
             patch('src.scanner.run_market_scan', side_effect=KeyboardInterrupt), \
             patch('src.scanner.logger'):

            mock_health.return_value.scan_started = Mock()

            # Should not raise, just return
            run_continuous(mock_config, interval=1)


class TestModuleImports:
    """Test that module exports work correctly."""

    def test_can_import_from_main(self):
        """Should be able to import scanner functions from main."""
        from src.main import run_continuous, run_market_scan, run_wavetrend_scan

        assert callable(run_market_scan)
        assert callable(run_wavetrend_scan)
        assert callable(run_continuous)

    def test_backwards_compatibility_alias(self):
        """check_symbol_wavetrend should be alias for check_wavetrend_signal."""
        from src.main import check_symbol_wavetrend, check_wavetrend_signal

        assert check_symbol_wavetrend is check_wavetrend_signal
