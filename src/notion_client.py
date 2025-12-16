"""
Notion API client for managing signals and buy databases.

This module provides backwards-compatible access to the Notion API.
The implementation has been refactored into separate modules:
- notion_models.py: Data models and type definitions
- notion_http.py: HTTP client with retry and rate limiting
- notion_repo.py: Repository for database operations

For new code, prefer importing directly from those modules.
"""

from src.exceptions import ConfigError
from src.logger import logger
from src.notion_http import NotionHTTPClient
from src.notion_models import NotionConfig, SignalData
from src.notion_repo import NotionRepository

# Re-export for backwards compatibility
__all__ = [
    "NotionClient",
    "NotionConfig",
    "SignalData",
    "NotionHTTPClient",
    "NotionRepository",
]


class NotionClient:
    """
    Client for interacting with Notion API - Signals and Buy databases.

    This is a facade that delegates to NotionRepository.
    Maintains backwards compatibility with existing code.
    """

    def __init__(
        self,
        api_token: str,
        database_id: str | None = None,
        signals_database_id: str | None = None,
        buy_database_id: str | None = None,
    ):
        """
        Initialize Notion client.

        Args:
            api_token: Notion integration token
            database_id: Watchlist database ID (optional)
            signals_database_id: ID of signals database
            buy_database_id: ID of buy database
        """
        if not api_token or api_token.startswith("YOUR_"):
            raise ConfigError("Valid Notion API token required")

        if not signals_database_id or signals_database_id.startswith("YOUR_"):
            raise ConfigError("Valid signals_database_id required")

        # Create config
        self._config = NotionConfig(
            api_key=api_token,
            database_id=database_id or "",
            signals_database_id=signals_database_id,
            buy_database_id=buy_database_id,
        )

        # Create repository (handles all operations)
        self._repo = NotionRepository(self._config)

        # Expose properties for backwards compatibility
        self.api_token = api_token
        self.database_id = database_id
        self.signals_database_id = signals_database_id
        self.buy_database_id = buy_database_id
        self.base_url = self._config.base_url
        self.headers = self._config.headers

        logger.debug("notion.client_initialized")

    # ==================== Watchlist Operations ====================

    def get_watchlist(self) -> tuple[list[str], dict[str, str]]:
        """Get all symbols from the watchlist database."""
        return self._repo.get_watchlist()

    def add_to_watchlist(self, symbol: str, date_str: str | None = None) -> bool:
        """Add a symbol to the watchlist database."""
        return self._repo.add_to_watchlist(symbol, date_str)

    def delete_from_watchlist(self, symbol: str) -> bool:
        """Delete a symbol from the watchlist database."""
        return self._repo.delete_from_watchlist(symbol)

    def update_watchlist_date(
        self, symbol: str, page_id: str | None = None
    ) -> bool:
        """Update the date of an existing watchlist entry."""
        return self._repo.update_watchlist_date(symbol, page_id)

    # ==================== Signals Operations ====================

    def get_signals(self) -> tuple[list[str], dict[str, str]]:
        """Get all symbols from the signals database."""
        return self._repo.get_signals()

    def add_to_signals(
        self,
        symbol: str,
        date_str: str | None = None,
        rsi: float | None = None,
        stoch_k: float | None = None,
        stoch_d: float | None = None,
        macd: float | None = None,
        macd_signal: float | None = None,
        macd_hist: float | None = None,
        close_price: float | None = None,
        volume: int | None = None,
    ) -> bool:
        """Add a signal to the signals database."""
        from datetime import date

        signal = SignalData(
            symbol=symbol,
            date=date_str or date.today().isoformat(),
            rsi=rsi,
            stoch_k=stoch_k,
            stoch_d=stoch_d,
            macd=macd,
            macd_signal=macd_signal,
            macd_hist=macd_hist,
            close_price=close_price,
            volume=volume,
        )
        return self._repo.add_to_signals(signal)

    def delete_from_signals(self, symbol: str) -> bool:
        """Delete a symbol from the signals database."""
        return self._repo.delete_from_signals(symbol)

    def symbol_exists_in_signals(self, symbol: str) -> bool:
        """Check if a symbol exists in signals database."""
        return self._repo.symbol_exists_in_signals(symbol)

    def remove_duplicates_from_signals(self) -> int:
        """Remove duplicate symbols from signals database."""
        return self._repo.remove_duplicates_from_signals()

    def cleanup_old_signals(self, max_age_days: int = 7) -> int:
        """Remove old entries from signals database."""
        return self._repo.cleanup_old_signals(max_age_days)

    # ==================== Buy Database Operations ====================

    def add_to_buy(
        self,
        symbol: str,
        date_str: str | None = None,
        rsi: float | None = None,
        stoch_k: float | None = None,
        stoch_d: float | None = None,
    ) -> bool:
        """Add a symbol to the buy database."""
        return self._repo.add_to_buy(symbol, date_str, rsi, stoch_k, stoch_d)

    def delete_from_buy(self, symbol: str) -> bool:
        """Delete a symbol from the buy database."""
        return self._repo.delete_from_buy(symbol)

    def symbol_exists_in_buy(self, symbol: str) -> bool:
        """Check if a symbol exists in buy database."""
        return self._repo.symbol_exists_in_buy(symbol)

    # ==================== Common Operations ====================

    def get_all_symbols(self) -> set:
        """Get all unique symbols across signals and buy databases."""
        return self._repo.get_all_symbols()

    def delete_page(self, page_id: str) -> bool:
        """Archive (delete) a page from Notion."""
        return self._repo.delete_page(page_id)

    # ==================== Internal Methods (for compatibility) ====================

    def _get_database_schema(self, database_id: str) -> dict:
        """Get database schema with caching."""
        return self._repo.http.get_database_schema(database_id)

    def _find_title_property(self, properties: dict) -> str | None:
        """Find the title property name in a schema."""
        return self._repo.http.find_title_property(properties)

    def _get_symbol_page_map(self, database_id: str) -> dict[str, str]:
        """Get symbol to page_id mapping from any database."""
        return self._repo._get_symbol_page_map(database_id)

    def _get_symbols_from_database(self, database_id: str) -> list[str]:
        """Generic method to fetch symbols from any database."""
        return self._repo._get_symbols_from_database(database_id)
