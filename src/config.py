import os
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from dotenv import load_dotenv
from .exceptions import ConfigError

load_dotenv()


class TelegramConfig(BaseModel):
    bot_token: str = Field(..., min_length=10, description="Telegram bot token")
    chat_id: str = Field(..., min_length=1, description="Telegram chat ID")

    @field_validator('bot_token', 'chat_id')
    @classmethod
    def not_placeholder(cls, v: str) -> str:
        if v.startswith('YOUR_'):
            raise ValueError('Replace placeholder values in config')
        return v


class APIConfig(BaseModel):
    provider: str = Field(default="yfinance")
    token: str = Field(default="", description="API token (not needed for yfinance)")
    alpha_vantage_key: str = Field(default="", description="Alpha Vantage API key for precise indicators")
    rate_limit_per_minute: int = Field(default=5, ge=1, le=60)
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Only yfinance is supported"""
        if v != "yfinance":
            raise ValueError(f"Unsupported API provider: {v}. Only 'yfinance' is currently supported.")
        return v


class DataConfig(BaseModel):
    max_watch_days: int = Field(default=5, ge=1, le=30)


class ScreenConfig(BaseModel):
    region: List[int] = Field(..., min_length=4, max_length=4)
    app_name: Optional[str] = Field(default=None, description="Application name to activate before capture")

    @field_validator('region')
    @classmethod
    def validate_region(cls, v: List[int]) -> List[int]:
        if any(x < 0 for x in v[:2]):
            raise ValueError('Left/top coordinates cannot be negative')
        if v[2] <= 0 or v[3] <= 0:
            raise ValueError('Width and height must be positive')
        return v


class TesseractConfig(BaseModel):
    path: Optional[str] = None
    lang: str = "eng"
    config_str: str = "--psm 6"


class NotionConfig(BaseModel):
    """Notion API configuration - only signals_database_id and buy_database_id are required"""
    api_token: str = Field(..., description="Notion integration token")
    database_id: Optional[str] = Field(default=None, description="DEPRECATED: Old watchlist database ID (no longer used)")
    signals_database_id: str = Field(..., description="Database ID for first-stage signals")
    buy_database_id: str = Field(..., description="Database ID for confirmed buy signals")
    
    @field_validator('api_token', 'signals_database_id', 'buy_database_id')
    @classmethod
    def not_placeholder(cls, v: str) -> str:
        if v and v.startswith('YOUR_'):
            raise ValueError('Replace placeholder values in config')
        return v


class Config(BaseModel):
    telegram: TelegramConfig
    api: APIConfig
    data: DataConfig
    notion: NotionConfig
    log_level: str = Field(default="INFO")

    @classmethod
    def load(cls, path: str = "config.example.yaml") -> "Config":
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {path}")
        
        try:
            raw = yaml.safe_load(p.read_text()) or {}
        except Exception as e:
            raise ConfigError(f"Failed to parse YAML: {e}")

        # Environment variable overrides for sensitive data
        if bot := os.getenv("TELEGRAM_BOT_TOKEN"):
            raw.setdefault("telegram", {})["bot_token"] = bot
        if chat := os.getenv("TELEGRAM_CHAT_ID"):
            raw.setdefault("telegram", {})["chat_id"] = chat
        if token := os.getenv("API_TOKEN"):
            raw.setdefault("api", {})["token"] = token
        if provider := os.getenv("API_PROVIDER"):
            raw.setdefault("api", {})["provider"] = provider
        if notion_token := os.getenv("NOTION_API_TOKEN"):
            raw.setdefault("notion", {})["api_token"] = notion_token
        if notion_signals_db := os.getenv("NOTION_SIGNALS_DATABASE_ID"):
            raw.setdefault("notion", {})["signals_database_id"] = notion_signals_db
        if notion_buy_db := os.getenv("NOTION_BUY_DATABASE_ID"):
            raw.setdefault("notion", {})["buy_database_id"] = notion_buy_db
        if alpha_vantage := os.getenv("ALPHA_VANTAGE_KEY"):
            raw.setdefault("api", {})["alpha_vantage_key"] = alpha_vantage

        try:
            return cls(**raw)
        except Exception as e:
            raise ConfigError(f"Invalid configuration: {e}")
