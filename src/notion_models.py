"""
Notion data models and type definitions.

This module contains all dataclasses and type hints used by the Notion client.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class NotionConfig:
    """Configuration for Notion API connection."""

    api_key: str
    database_id: str  # Watchlist database
    signals_database_id: str | None = None
    buy_database_id: str | None = None
    base_url: str = "https://api.notion.com/v1"
    notion_version: str = "2022-06-28"
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0

    @property
    def headers(self) -> dict[str, str]:
        """Generate API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.notion_version,
        }


@dataclass
class SignalData:
    """Data for a trading signal entry."""

    symbol: str
    date: str  # ISO format: YYYY-MM-DD
    rsi: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    close_price: float | None = None
    volume: int | None = None

    def to_notion_properties(
        self, title_property: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Convert to Notion API properties format.

        Args:
            title_property: Name of the title property in the database
            schema: Database schema to match property names

        Returns:
            Dictionary of Notion property values
        """
        properties: dict[str, Any] = {
            title_property: {"title": [{"text": {"content": self.symbol}}]}
        }

        # Map our fields to potential Notion property names
        field_mappings = {
            "rsi": ["RSI", "rsi", "Rsi"],
            "stoch_k": ["Stoch K", "StochK", "stoch_k", "K"],
            "stoch_d": ["Stoch D", "StochD", "stoch_d", "D"],
            "macd": ["MACD", "macd", "Macd"],
            "macd_signal": ["MACD Signal", "Signal", "macd_signal"],
            "macd_hist": ["MACD Hist", "Histogram", "macd_hist"],
            "close_price": ["Close", "Price", "close_price"],
            "volume": ["Volume", "volume", "Vol"],
        }

        for field_name, possible_names in field_mappings.items():
            value = getattr(self, field_name)
            if value is not None:
                for prop_name in possible_names:
                    if prop_name in schema:
                        prop_type = schema[prop_name].get("type")
                        if prop_type == "number":
                            properties[prop_name] = {"number": value}
                        break

        # Add date if schema has a date property
        for prop_name, prop_data in schema.items():
            if prop_data.get("type") == "date":
                properties[prop_name] = {"date": {"start": self.date}}
                break

        return properties


@dataclass
class PageResult:
    """Result of a page operation."""

    page_id: str
    symbol: str
    success: bool
    error: str | None = None
    created_time: datetime | None = None
    last_edited_time: datetime | None = None


@dataclass
class DatabaseSchema:
    """Cached database schema information."""

    database_id: str
    properties: dict[str, Any]
    title_property: str | None = None
    date_property: str | None = None
    fetched_at: datetime = field(default_factory=datetime.now)

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if schema cache is stale."""
        age = (datetime.now() - self.fetched_at).total_seconds()
        return age > max_age_seconds


@dataclass
class WatchlistEntry:
    """A single watchlist entry."""

    symbol: str
    page_id: str
    added_date: date | None = None


@dataclass
class SignalEntry:
    """A single signal entry."""

    symbol: str
    page_id: str
    signal_date: date | None = None
    rsi: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
