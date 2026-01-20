"""
Notion repository for domain operations.

This module handles all business logic for interacting with Notion databases:
- Watchlist operations (get, add, delete, update)
- Signals operations (get, add, delete, cleanup)
- Buy database operations (get, add, delete)
"""

from datetime import date, datetime, timedelta
from typing import Any

from src.logger import logger
from src.notion_http import NotionHTTPClient
from src.notion_models import NotionConfig, SignalData


class NotionRepository:
    """
    Repository for Notion database operations.

    Provides high-level methods for managing watchlist, signals, and buy databases.
    """

    def __init__(self, config: NotionConfig):
        """
        Initialize the repository.

        Args:
            config: NotionConfig with database IDs and API settings
        """
        self.config = config
        self.http = NotionHTTPClient(config)

        # Shorthand for database IDs
        self.database_id = config.database_id
        self.signals_database_id = config.signals_database_id
        self.buy_database_id = config.buy_database_id

    # ==================== Watchlist Operations ====================

    def get_watchlist(self) -> tuple[list[str], dict[str, str]]:
        """
        Get all symbols from the watchlist database.

        Returns:
            Tuple of (list of symbols, dict mapping symbol to page_id)
        """
        try:
            response = self.http.post(f"/databases/{self.database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return [], {}

            # Find title property
            properties = self.http.get_database_schema(self.database_id)
            title_property = self.http.find_title_property(properties)

            if not title_property:
                logger.error("notion.no_title_property", database_id=self.database_id)
                return [], {}

            symbols = []
            symbol_to_page: dict[str, str] = {}

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])

                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        symbols.append(symbol)
                        symbol_to_page[symbol] = page_id

            return symbols, symbol_to_page

        except Exception as e:
            logger.error("notion.get_watchlist_failed", error=str(e))
            return [], {}

    def add_to_watchlist(self, symbol: str, date_str: str | None = None) -> bool:
        """
        Add a symbol to the watchlist database.

        Args:
            symbol: Stock ticker symbol
            date_str: Added date (optional, defaults to today)

        Returns:
            True if successful, False otherwise
        """
        try:
            added_date = date_str or date.today().isoformat()

            properties = self.http.get_database_schema(self.database_id)
            if not properties:
                logger.error("notion.schema_fetch_failed", database_id=self.database_id)
                return False

            title_property = self.http.find_title_property(properties)
            if not title_property:
                logger.error("notion.no_title_property", database_id=self.database_id)
                return False

            # Find date property
            date_property = None
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "date" and "add" in prop_name.lower():
                    date_property = prop_name
                    break

            payload: dict[str, Any] = {
                "parent": {"database_id": self.database_id},
                "properties": {title_property: {"title": [{"text": {"content": symbol}}]}},
            }

            if date_property:
                payload["properties"][date_property] = {"date": {"start": added_date}}

            self.http.post("/pages", json=payload)
            logger.info("notion.watchlist_added", symbol=symbol, date=added_date)
            return True

        except Exception as e:
            logger.error("notion.add_watchlist_failed", symbol=symbol, error=str(e))
            return False

    def delete_from_watchlist(self, symbol: str) -> bool:
        """
        Delete a symbol from the watchlist database.

        Args:
            symbol: Stock ticker symbol to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            _, symbol_to_page = self.get_watchlist()

            if symbol not in symbol_to_page:
                logger.warning("notion.symbol_not_in_watchlist", symbol=symbol)
                return False

            page_id = symbol_to_page[symbol]
            result = self.delete_page(page_id)

            if result:
                logger.info("notion.deleted_from_watchlist", symbol=symbol)
            return result

        except Exception as e:
            logger.error("notion.delete_from_watchlist_failed", symbol=symbol, error=str(e))
            return False

    def update_watchlist_date(self, symbol: str, page_id: str | None = None) -> bool:
        """
        Update the date of an existing watchlist entry.

        Args:
            symbol: Stock symbol to update
            page_id: Notion page ID (if known, otherwise will fetch)

        Returns:
            True if update successful, False otherwise
        """
        try:
            if not page_id:
                _, symbol_to_page = self.get_watchlist()
                page_id = symbol_to_page.get(symbol)

                if not page_id:
                    logger.warning("notion.update_date_no_page", symbol=symbol)
                    return False

            today = date.today().isoformat()
            payload = {"properties": {"Added": {"date": {"start": today}}}}

            self.http.patch(f"/pages/{page_id}", json=payload)
            logger.info("notion.watchlist_date_updated", symbol=symbol, page_id=page_id)
            return True

        except Exception as e:
            logger.error("notion.update_date_failed", symbol=symbol, error=str(e))
            return False

    # ==================== Signals Operations ====================

    def get_signals(self) -> tuple[list[str], dict[str, str]]:
        """
        Get all symbols from the signals database.

        Returns:
            Tuple of (list of symbols, dict mapping symbol to page_id)
        """
        if not self.signals_database_id:
            return [], {}

        try:
            response = self.http.post(f"/databases/{self.signals_database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return [], {}

            # Detect title property from first result
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break

            if not title_property:
                return [], {}

            symbols = []
            symbol_to_page: dict[str, str] = {}

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])

                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        symbols.append(symbol)
                        symbol_to_page[symbol] = page_id

            return symbols, symbol_to_page

        except Exception as e:
            logger.error("notion.get_signals_failed", error=str(e))
            return [], {}

    def add_to_signals(self, signal: SignalData) -> bool:
        """
        Add a signal to the signals database.

        Args:
            signal: SignalData object with symbol and indicators

        Returns:
            True if successful, False otherwise
        """
        if not self.signals_database_id:
            logger.warning("notion.no_signals_database")
            return False

        try:
            properties = self.http.get_database_schema(self.signals_database_id)
            if not properties:
                logger.error("notion.schema_fetch_failed", database_id=self.signals_database_id)
                return False

            title_property = self.http.find_title_property(properties)
            if not title_property:
                logger.error("notion.no_title_property", database_id=self.signals_database_id)
                return False

            notion_properties = signal.to_notion_properties(title_property, properties)

            payload = {
                "parent": {"database_id": self.signals_database_id},
                "properties": notion_properties,
            }

            self.http.post("/pages", json=payload)
            logger.info("notion.signal_added", symbol=signal.symbol)
            return True

        except Exception as e:
            logger.error("notion.add_signal_failed", symbol=signal.symbol, error=str(e))
            return False

    def delete_from_signals(self, symbol: str) -> bool:
        """
        Delete a symbol from the signals database.

        Args:
            symbol: Stock ticker symbol to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.signals_database_id:
            return False

        try:
            _, symbol_to_page = self.get_signals()

            if symbol not in symbol_to_page:
                logger.warning("notion.symbol_not_in_signals", symbol=symbol)
                return False

            page_id = symbol_to_page[symbol]
            result = self.delete_page(page_id)

            if result:
                logger.info("notion.deleted_from_signals", symbol=symbol)
            return result

        except Exception as e:
            logger.error("notion.delete_from_signals_failed", symbol=symbol, error=str(e))
            return False

    def symbol_exists_in_signals(self, symbol: str) -> bool:
        """
        Check if a symbol exists in signals database.

        Args:
            symbol: Stock ticker symbol to check

        Returns:
            True if symbol exists, False otherwise
        """
        if not self.signals_database_id:
            return False

        try:
            symbols, _ = self.get_signals()
            return symbol.upper() in [s.upper() for s in symbols]
        except Exception:
            return False

    def remove_duplicates_from_signals(self) -> int:
        """
        Remove duplicate symbols from signals database.

        Returns:
            Number of duplicates removed
        """
        if not self.signals_database_id:
            return 0

        try:
            response = self.http.post(f"/databases/{self.signals_database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return 0

            # Find title property
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break

            if not title_property:
                return 0

            # Track symbols and find duplicates
            seen_symbols: set[str] = set()
            duplicate_pages: list[tuple[str, str]] = []

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])

                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        if symbol in seen_symbols:
                            duplicate_pages.append((symbol, page_id))
                        else:
                            seen_symbols.add(symbol)

            # Delete duplicates
            removed = 0
            for symbol, page_id in duplicate_pages:
                if self.delete_page(page_id):
                    logger.info("notion.duplicate_removed", symbol=symbol, page_id=page_id)
                    removed += 1

            logger.info(
                "notion.duplicates_cleanup_complete",
                removed=removed,
                total_checked=len(results),
            )
            return removed

        except Exception as e:
            logger.error("notion.remove_duplicates_failed", error=str(e))
            return 0

    def cleanup_old_signals(self, max_age_days: int = 7) -> int:
        """
        Remove old entries from signals database.

        Args:
            max_age_days: Maximum age in days before signal is removed

        Returns:
            Number of signals removed
        """
        if not self.signals_database_id:
            logger.warning("notion.cleanup_no_signals_db")
            return 0

        try:
            response = self.http.post(f"/databases/{self.signals_database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return 0

            # Find date property
            first_page_props = results[0].get("properties", {})
            date_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "date":
                    date_property = prop_name
                    break

            removed_count = 0
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})

                signal_date = None
                if date_property:
                    date_data = props.get(date_property, {}).get("date")
                    if date_data and date_data.get("start"):
                        try:
                            signal_date = datetime.fromisoformat(date_data["start"].replace("Z", "+00:00"))
                            if signal_date.tzinfo:
                                signal_date = signal_date.replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass

                should_remove = signal_date is None or signal_date < cutoff_date

                if should_remove:
                    if self.delete_page(page_id):
                        removed_count += 1
                        # Get symbol for logging
                        for _prop_name, prop_data in props.items():
                            if prop_data.get("type") == "title":
                                title_content = prop_data.get("title", [])
                                if title_content:
                                    symbol = title_content[0].get("text", {}).get("content", "unknown")
                                    logger.info(
                                        "notion.old_signal_removed",
                                        symbol=symbol,
                                        page_id=page_id,
                                    )
                                break

            logger.info("notion.signals_cleanup_complete", removed=removed_count)
            return removed_count

        except Exception as e:
            logger.error("notion.cleanup_failed", error=str(e))
            return 0

    # ==================== Buy Database Operations ====================

    def add_to_buy(
        self,
        symbol: str,
        date_str: str | None = None,
        rsi: float | None = None,
        stoch_k: float | None = None,
        stoch_d: float | None = None,
    ) -> bool:
        """
        Add a symbol to the buy database.

        Args:
            symbol: Stock ticker symbol
            date_str: Signal date
            rsi: RSI indicator value
            stoch_k: Stochastic K value
            stoch_d: Stochastic D value

        Returns:
            True if successful, False otherwise
        """
        if not self.buy_database_id:
            logger.warning("notion.no_buy_database")
            return False

        try:
            properties = self.http.get_database_schema(self.buy_database_id)
            if not properties:
                logger.error("notion.schema_fetch_failed", database_id=self.buy_database_id)
                return False

            title_property = self.http.find_title_property(properties)
            if not title_property:
                logger.error("notion.no_title_property", database_id=self.buy_database_id)
                return False

            payload: dict[str, Any] = {
                "parent": {"database_id": self.buy_database_id},
                "properties": {title_property: {"title": [{"text": {"content": symbol}}]}},
            }

            # Add optional properties
            props = payload["properties"]

            if date_str:
                for prop_name, prop_data in properties.items():
                    if prop_data.get("type") == "date":
                        props[prop_name] = {"date": {"start": date_str}}
                        break

            if rsi is not None:
                for prop_name in ["RSI", "rsi", "Rsi"]:
                    if prop_name in properties:
                        props[prop_name] = {"number": rsi}
                        break

            if stoch_k is not None:
                for prop_name in ["Stoch K", "StochK", "stoch_k", "K"]:
                    if prop_name in properties:
                        props[prop_name] = {"number": stoch_k}
                        break

            if stoch_d is not None:
                for prop_name in ["Stoch D", "StochD", "stoch_d", "D"]:
                    if prop_name in properties:
                        props[prop_name] = {"number": stoch_d}
                        break

            self.http.post("/pages", json=payload)
            logger.info("notion.buy_added", symbol=symbol)
            return True

        except Exception as e:
            logger.error("notion.add_buy_failed", symbol=symbol, error=str(e))
            return False

    def delete_from_buy(self, symbol: str) -> bool:
        """
        Delete a symbol from the buy database.

        Args:
            symbol: Stock ticker symbol to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.buy_database_id:
            return False

        try:
            symbol_to_page = self._get_symbol_page_map(self.buy_database_id)

            if symbol not in symbol_to_page:
                logger.warning("notion.symbol_not_in_buy", symbol=symbol)
                return False

            page_id = symbol_to_page[symbol]
            result = self.delete_page(page_id)

            if result:
                logger.info("notion.deleted_from_buy", symbol=symbol)
            return result

        except Exception as e:
            logger.error("notion.delete_from_buy_failed", symbol=symbol, error=str(e))
            return False

    def symbol_exists_in_buy(self, symbol: str) -> bool:
        """
        Check if a symbol exists in buy database.

        Args:
            symbol: Stock ticker symbol to check

        Returns:
            True if symbol exists, False otherwise
        """
        if not self.buy_database_id:
            return False

        try:
            buy_symbols = self._get_symbols_from_database(self.buy_database_id)
            return symbol.upper() in [s.upper() for s in buy_symbols]
        except Exception:
            return False

    def cleanup_old_buys(self, max_age_days: int = 15) -> int:
        """
        Remove old entries from buy database.

        Args:
            max_age_days: Maximum age in days before buy entry is removed

        Returns:
            Number of buy entries removed
        """
        if not self.buy_database_id:
            logger.warning("notion.cleanup_no_buy_db")
            return 0

        try:
            response = self.http.post(f"/databases/{self.buy_database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return 0

            # Find date property
            first_page_props = results[0].get("properties", {})
            date_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "date":
                    date_property = prop_name
                    break

            removed_count = 0
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})

                buy_date = None
                if date_property:
                    date_data = props.get(date_property, {}).get("date")
                    if date_data and date_data.get("start"):
                        try:
                            buy_date = datetime.fromisoformat(date_data["start"].replace("Z", "+00:00"))
                            if buy_date.tzinfo:
                                buy_date = buy_date.replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass

                should_remove = buy_date is None or buy_date < cutoff_date

                if should_remove:
                    if self.delete_page(page_id):
                        removed_count += 1
                        # Get symbol for logging
                        for _prop_name, prop_data in props.items():
                            if prop_data.get("type") == "title":
                                title_content = prop_data.get("title", [])
                                if title_content:
                                    symbol = title_content[0].get("text", {}).get("content", "unknown")
                                    logger.info(
                                        "notion.old_buy_removed",
                                        symbol=symbol,
                                        page_id=page_id,
                                    )
                                break

            logger.info("notion.buys_cleanup_complete", removed=removed_count)
            return removed_count

        except Exception as e:
            logger.error("notion.buy_cleanup_failed", error=str(e))
            return 0

    # ==================== Common Operations ====================

    def get_all_symbols(self) -> set[str]:
        """
        Get all unique symbols across signals and buy databases.

        Returns:
            Set of symbols that are in signals or buy database
        """
        all_symbols: set[str] = set()

        if self.signals_database_id:
            try:
                signals_symbols, _ = self.get_signals()
                all_symbols.update(signals_symbols)
            except Exception as e:
                logger.warning("notion.get_signals_failed", error=str(e))

        if self.buy_database_id:
            try:
                buy_symbols = self._get_symbols_from_database(self.buy_database_id)
                all_symbols.update(buy_symbols)
            except Exception as e:
                logger.warning("notion.get_buy_failed", error=str(e))

        return all_symbols

    def delete_page(self, page_id: str) -> bool:
        """
        Archive (delete) a page from Notion.

        Args:
            page_id: The ID of the page to delete

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Check if page exists
            try:
                response = self.http.get(f"/pages/{page_id}")
                page_data = response.json()
                if page_data.get("archived", False):
                    logger.info("notion.page_already_archived", page_id=page_id)
                    return True
            except Exception:
                logger.warning("notion.page_not_found", page_id=page_id)
                return True  # Already deleted

            # Archive the page
            self.http.patch(f"/pages/{page_id}", json={"archived": True})
            logger.info("notion.page_deleted", page_id=page_id)
            return True

        except Exception as e:
            logger.error("notion.delete_failed", page_id=page_id, error=str(e))
            return False

    def _get_symbol_page_map(self, database_id: str) -> dict[str, str]:
        """
        Get symbol to page_id mapping from any database.

        Args:
            database_id: The ID of the database to query

        Returns:
            Dictionary mapping symbol names to page IDs
        """
        symbol_to_page: dict[str, str] = {}

        try:
            response = self.http.post(f"/databases/{database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return symbol_to_page

            # Detect title property
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break

            if not title_property:
                return symbol_to_page

            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])

                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        symbol_to_page[symbol] = page_id

            return symbol_to_page

        except Exception as e:
            logger.error("notion.get_symbol_page_map_failed", database_id=database_id, error=str(e))
            return symbol_to_page

    def _get_symbols_from_database(self, database_id: str) -> list[str]:
        """
        Generic method to fetch symbols from any database.

        Args:
            database_id: The ID of the database to query

        Returns:
            List of symbols
        """
        try:
            response = self.http.post(f"/databases/{database_id}/query", json={})
            data = response.json()
            results = data.get("results", [])

            if not results:
                return []

            # Detect title property
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break

            if not title_property:
                return []

            symbols = []
            for page in results:
                props = page.get("properties", {})
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])

                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        symbols.append(symbol)

            return symbols

        except Exception as e:
            logger.error("notion.fetch_symbols_failed", database_id=database_id, error=str(e))
            return []
