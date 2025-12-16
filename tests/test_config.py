"""
Tests for config loading and validation
"""
import os
import tempfile
from unittest.mock import patch

import pytest

from src.config import APIConfig, Config, NotionConfig, TelegramConfig
from src.exceptions import ConfigError


class TestTelegramConfig:
    """Test Telegram configuration validation"""

    def test_valid_config(self):
        """Test valid Telegram config"""
        config = TelegramConfig(
            bot_token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
            chat_id="-100123456789"
        )
        assert config.bot_token.startswith("1234567890")
        assert config.chat_id == "-100123456789"

    def test_placeholder_bot_token_rejected(self):
        """Test that placeholder bot token is rejected"""
        with pytest.raises(ValueError, match="placeholder"):
            TelegramConfig(bot_token="YOUR_BOT_TOKEN", chat_id="123456")

    def test_placeholder_chat_id_rejected(self):
        """Test that placeholder chat ID is rejected"""
        with pytest.raises(ValueError, match="placeholder"):
            TelegramConfig(bot_token="valid_token_123", chat_id="YOUR_CHAT_ID")

    def test_short_bot_token_rejected(self):
        """Test that too short bot token is rejected"""
        with pytest.raises(ValueError):
            TelegramConfig(bot_token="short", chat_id="123456")


class TestNotionConfig:
    """Test Notion configuration validation"""

    def test_valid_config(self):
        """Test valid Notion config"""
        config = NotionConfig(
            api_token="ntn_secret_abc123",
            signals_database_id="abc123def456",
            buy_database_id="xyz789ghi012"
        )
        assert config.api_token == "ntn_secret_abc123"
        assert config.signals_database_id == "abc123def456"

    def test_placeholder_api_token_rejected(self):
        """Test that placeholder API token is rejected"""
        with pytest.raises(ValueError, match="placeholder"):
            NotionConfig(
                api_token="YOUR_NOTION_TOKEN",
                signals_database_id="valid_db",
                buy_database_id="valid_db"
            )

    def test_placeholder_signals_db_rejected(self):
        """Test that placeholder signals DB is rejected"""
        with pytest.raises(ValueError, match="placeholder"):
            NotionConfig(
                api_token="valid_token",
                signals_database_id="YOUR_SIGNALS_DB",
                buy_database_id="valid_db"
            )


class TestAPIConfig:
    """Test API configuration validation"""

    def test_default_provider_is_yfinance(self):
        """Test that default provider is yfinance"""
        config = APIConfig()
        assert config.provider == "yfinance"

    def test_unsupported_provider_rejected(self):
        """Test that unsupported providers are rejected"""
        with pytest.raises(ValueError, match="Unsupported"):
            APIConfig(provider="alpha_vantage")


class TestConfigLoad:
    """Test Config.load() functionality"""

    def test_load_missing_file_raises(self):
        """Test that missing config file raises ConfigError"""
        with pytest.raises(ConfigError, match="not found"):
            Config.load("/nonexistent/config.yaml")

    def test_load_invalid_yaml_raises(self):
        """Test that invalid YAML raises ConfigError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            try:
                with pytest.raises(ConfigError, match="Failed to parse"):
                    Config.load(f.name)
            finally:
                os.unlink(f.name)

    def test_load_valid_config(self):
        """Test loading a valid config file"""
        config_content = """
telegram:
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
  chat_id: "-100123456789"
api:
  provider: "yfinance"
data:
  max_watch_days: 5
notion:
  api_token: "ntn_secret_valid"
  signals_database_id: "signals_db_id"
  buy_database_id: "buy_db_id"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                # Clear env vars that might override
                with patch.dict(os.environ, {
                    'TELEGRAM_BOT_TOKEN': '',
                    'TELEGRAM_CHAT_ID': '',
                    'NOTION_API_TOKEN': '',
                    'NOTION_SIGNALS_DATABASE_ID': '',
                    'NOTION_BUY_DATABASE_ID': ''
                }, clear=False):
                    # Remove keys if they exist
                    env_backup = {}
                    keys_to_clear = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
                                    'NOTION_API_TOKEN', 'NOTION_SIGNALS_DATABASE_ID',
                                    'NOTION_BUY_DATABASE_ID']
                    for key in keys_to_clear:
                        if key in os.environ:
                            env_backup[key] = os.environ.pop(key)

                    try:
                        config = Config.load(f.name)
                        assert config.telegram.bot_token == "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                        assert config.api.provider == "yfinance"
                        assert config.notion.signals_database_id == "signals_db_id"
                    finally:
                        # Restore env vars
                        os.environ.update(env_backup)
            finally:
                os.unlink(f.name)

    def test_env_var_overrides_config_file(self):
        """Test that environment variables override config file values"""
        config_content = """
telegram:
  bot_token: "file_token_123456789"
  chat_id: "-100123456789"
api:
  provider: "yfinance"
data:
  max_watch_days: 5
notion:
  api_token: "file_notion_token"
  signals_database_id: "file_signals_db"
  buy_database_id: "file_buy_db"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                # Backup and clear existing env vars, then set test values
                env_backup = {}
                keys_to_manage = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
                                 'NOTION_API_TOKEN', 'NOTION_SIGNALS_DATABASE_ID',
                                 'NOTION_BUY_DATABASE_ID']
                for key in keys_to_manage:
                    if key in os.environ:
                        env_backup[key] = os.environ.pop(key)

                try:
                    # Set specific override values
                    os.environ['TELEGRAM_BOT_TOKEN'] = 'env_token_1234567890'
                    os.environ['NOTION_API_TOKEN'] = 'env_notion_token'

                    config = Config.load(f.name)
                    # Env vars should override file values
                    assert config.telegram.bot_token == 'env_token_1234567890'
                    assert config.notion.api_token == 'env_notion_token'
                    # File values should remain for non-overridden
                    assert config.telegram.chat_id == "-100123456789"
                finally:
                    # Clean up test env vars
                    for key in ['TELEGRAM_BOT_TOKEN', 'NOTION_API_TOKEN']:
                        if key in os.environ:
                            del os.environ[key]
                    # Restore original env vars
                    os.environ.update(env_backup)
            finally:
                os.unlink(f.name)


class TestConfigValidation:
    """Test full config validation"""

    def test_missing_required_fields(self):
        """Test that missing required fields raise error"""
        config_content = """
telegram:
  bot_token: "valid_token_123456"
api:
  provider: "yfinance"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                with pytest.raises(ConfigError, match="Invalid configuration"):
                    Config.load(f.name)
            finally:
                os.unlink(f.name)
