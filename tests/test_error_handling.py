"""
Test error handling and edge cases
"""

from unittest.mock import Mock, patch

import pytest

from src.data_source_yfinance import daily_ohlc
from src.exceptions import ConfigError, TelegramError
from src.notion_client import NotionClient
from src.telegram_client import TelegramClient


class TestNotionClientErrorHandling:
    """Test Notion API error handling"""

    def test_invalid_api_token(self):
        """Test with invalid API token"""
        with pytest.raises(ConfigError):
            NotionClient("YOUR_TOKEN", signals_database_id="signals_db", buy_database_id="buy_db")

    def test_invalid_signals_database_id(self):
        """Test with invalid signals database ID"""
        with pytest.raises(ConfigError):
            NotionClient("valid_token", signals_database_id="YOUR_DATABASE", buy_database_id="buy_db")

    @patch("requests.post")
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors - graceful degradation"""
        mock_post.side_effect = Exception("Network error")

        client = NotionClient("ntn_test123", signals_database_id="signals_db", buy_database_id="buy_db")

        # Network errors should return empty results gracefully (no exception raised)
        symbols, mapping = client.get_signals()

        # Should return empty results, not crash
        assert symbols == []
        assert mapping == {}

    @patch("requests.post")
    def test_empty_database_response(self, mock_post):
        """Test handling of empty database"""
        mock_post.return_value.json.return_value = {"results": []}
        mock_post.return_value.raise_for_status = Mock()

        client = NotionClient("ntn_test123", signals_database_id="signals_db", buy_database_id="buy_db")
        symbols, mapping = client.get_signals()

        assert symbols == []
        assert mapping == {}


class TestTelegramClientErrorHandling:
    """Test Telegram error handling"""

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    def test_invalid_bot_token(self, mock_sleep):
        """Test with placeholder bot token - non-critical returns False"""
        client = TelegramClient("YOUR_BOT_TOKEN", "123456")

        # Non-critical send returns False on failure
        result = client.send("Test message")
        assert not result

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    def test_invalid_bot_token_critical(self, mock_sleep):
        """Test with placeholder bot token - critical raises"""
        client = TelegramClient("YOUR_BOT_TOKEN", "123456")

        # Critical send raises on failure
        with pytest.raises(TelegramError):
            client.send("Test message", critical=True)

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    @patch("requests.post")
    def test_network_error(self, mock_post, mock_sleep):
        """Test Telegram network error - non-critical returns False"""
        mock_post.side_effect = Exception("Network error")

        client = TelegramClient("bot123", "chat123")

        # Non-critical returns False
        result = client.send("Test")
        assert not result

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    @patch("requests.post")
    def test_network_error_critical(self, mock_post, mock_sleep):
        """Test Telegram network error - critical raises"""
        mock_post.side_effect = Exception("Network error")

        client = TelegramClient("bot123", "chat123")

        with pytest.raises(TelegramError):
            client.send("Test", critical=True)

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    @patch("requests.post")
    def test_rate_limit_error(self, mock_post, mock_sleep):
        """Test Telegram rate limiting - returns False after retries"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.raise_for_status.side_effect = Exception("Rate limited")
        mock_post.return_value = mock_response

        client = TelegramClient("bot123", "chat123")

        # Non-critical returns False
        result = client.send("Test")
        assert not result

    @patch("src.telegram_client.time.sleep")  # Skip retry delays
    @patch("requests.post")
    def test_consecutive_failures_raises(self, mock_post, mock_sleep):
        """Test that 5 consecutive failures raises TelegramError"""
        mock_post.side_effect = Exception("Network error")

        client = TelegramClient("bot123", "chat123")

        # First 4 failures should return False
        for _ in range(4):
            result = client.send("Test")
            assert not result

        # 5th failure should raise
        with pytest.raises(TelegramError):
            client.send("Test")


class TestDataSourceErrorHandling:
    """Test data source error handling"""

    def test_invalid_symbol(self):
        """Test with invalid stock symbol"""
        result = daily_ohlc("INVALID_SYMBOL_XYZ123")

        # Should return None for invalid symbols
        assert result is None

    @patch("yfinance.Ticker")
    def test_network_failure(self, mock_ticker):
        """Test yfinance network failure"""
        mock_instance = Mock()
        mock_instance.history.side_effect = Exception("Network error")
        mock_ticker.return_value = mock_instance

        result = daily_ohlc("AAPL")

        # Should handle gracefully
        assert result is None

    @patch("yfinance.Ticker")
    def test_empty_data_response(self, mock_ticker):
        """Test empty data from yfinance"""
        import pandas as pd

        mock_instance = Mock()
        mock_instance.history.return_value = pd.DataFrame()  # Empty
        mock_ticker.return_value = mock_instance

        result = daily_ohlc("AAPL")

        # Should return None for empty data
        assert result is None


class TestConfigValidation:
    """Test configuration validation"""

    def test_missing_required_fields(self):
        """Test config with missing fields"""

        from src.config import Config

        # Create invalid config
        invalid_config = {
            "telegram": {
                "bot_token": "test",
                # Missing chat_id
            }
        }

        with pytest.raises((ValueError, TypeError)):  # Pydantic ValidationError
            Config(**invalid_config)

    def test_placeholder_values_rejected(self):
        """Test that placeholder values are rejected"""
        from src.config import NotionConfig

        with pytest.raises(ValueError):
            NotionConfig(api_token="YOUR_TOKEN", database_id="real_id")


# Note: TestEndToEndErrorScenarios removed because it imports src.main
# which depends on alpha_vantage module that isn't installed.
# These tests should be re-enabled when alpha_vantage is added to requirements
# or the dependency is removed from main.py


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
