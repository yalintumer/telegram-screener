"""
Test error handling and edge cases
"""
import pytest
from unittest.mock import Mock, patch
from src.notion_client import NotionClient
from src.telegram_client import TelegramClient
from src.data_source_yfinance import daily_ohlc
from src.exceptions import ConfigError, TelegramError, DataSourceError


class TestNotionClientErrorHandling:
    """Test Notion API error handling"""
    
    def test_invalid_api_token(self):
        """Test with invalid API token"""
        with pytest.raises(ConfigError):
            NotionClient("YOUR_TOKEN", "database_id")
    
    def test_invalid_database_id(self):
        """Test with invalid database ID"""
        with pytest.raises(ConfigError):
            NotionClient("valid_token", "YOUR_DATABASE")
    
    @patch('requests.post')
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors"""
        mock_post.side_effect = Exception("Network error")
        
        client = NotionClient("ntn_test123", "db123")
        
        # Network error should raise exception (this is a critical failure)
        with pytest.raises(Exception) as exc_info:
            symbols, mapping = client.get_watchlist()
        
        assert "Network error" in str(exc_info.value)
    
    @patch('requests.post')
    def test_empty_database_response(self, mock_post):
        """Test handling of empty database"""
        mock_post.return_value.json.return_value = {"results": []}
        mock_post.return_value.raise_for_status = Mock()
        
        client = NotionClient("ntn_test123", "db123")
        symbols, mapping = client.get_watchlist()
        
        assert symbols == []
        assert mapping == {}


class TestTelegramClientErrorHandling:
    """Test Telegram error handling"""
    
    def test_invalid_bot_token(self):
        """Test with placeholder bot token"""
        # Should create client but fail on send
        client = TelegramClient("YOUR_BOT_TOKEN", "123456")
        
        # Send should raise error
        with pytest.raises(TelegramError):
            client.send("Test message")
    
    @patch('requests.post')
    def test_network_error(self, mock_post):
        """Test Telegram network error"""
        mock_post.side_effect = Exception("Network error")
        
        client = TelegramClient("bot123", "chat123")
        
        with pytest.raises(TelegramError):
            client.send("Test")
    
    @patch('requests.post')
    def test_rate_limit_error(self, mock_post):
        """Test Telegram rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"description": "Too Many Requests"}
        mock_post.return_value = mock_response
        
        client = TelegramClient("bot123", "chat123")
        
        with pytest.raises(TelegramError):
            client.send("Test")


class TestDataSourceErrorHandling:
    """Test data source error handling"""
    
    def test_invalid_symbol(self):
        """Test with invalid stock symbol"""
        result = daily_ohlc("INVALID_SYMBOL_XYZ123")
        
        # Should return None for invalid symbols
        assert result is None
    
    @patch('yfinance.Ticker')
    def test_network_failure(self, mock_ticker):
        """Test yfinance network failure"""
        mock_instance = Mock()
        mock_instance.history.side_effect = Exception("Network error")
        mock_ticker.return_value = mock_instance
        
        result = daily_ohlc("AAPL")
        
        # Should handle gracefully
        assert result is None
    
    @patch('yfinance.Ticker')
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
        import yaml
        
        # Create invalid config
        invalid_config = {
            "telegram": {
                "bot_token": "test",
                # Missing chat_id
            }
        }
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            Config(**invalid_config)
    
    def test_placeholder_values_rejected(self):
        """Test that placeholder values are rejected"""
        from src.config import NotionConfig
        
        with pytest.raises(ValueError):
            NotionConfig(
                api_token="YOUR_TOKEN",
                database_id="real_id"
            )


class TestEndToEndErrorScenarios:
    """Test complete error scenarios"""
    
    @patch('src.data_source_yfinance.daily_ohlc')
    def test_main_handles_data_failure(self, mock_ohlc):
        """Test main loop handles data source failures"""
        from src.main import check_symbol
        
        mock_ohlc.return_value = None
        
        # Should return False, not crash
        result = check_symbol("TEST")
        assert result == False
    
    @patch('src.data_source_yfinance.daily_ohlc')
    def test_insufficient_data_handling(self, mock_ohlc):
        """Test handling of insufficient data points"""
        import pandas as pd
        from src.main import check_symbol
        
        # Only 5 data points (need 30+)
        mock_ohlc.return_value = pd.DataFrame({
            'Date': pd.date_range('2025-01-01', periods=5),
            'Open': [100] * 5,
            'High': [101] * 5,
            'Low': [99] * 5,
            'Close': [100] * 5,
            'Volume': [1000000] * 5
        })
        
        result = check_symbol("TEST")
        assert result == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
