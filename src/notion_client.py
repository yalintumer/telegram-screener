"""Notion API client for managing signals and buy databases"""

from typing import List, Dict, Tuple, Optional
import requests
from .logger import logger
from .exceptions import ConfigError

# Default timeout for all Notion API requests (seconds)
NOTION_TIMEOUT = 30


class NotionClient:
    """Client for interacting with Notion API - Signals and Buy databases"""
    
    def __init__(self, api_token: str, database_id: str = None, signals_database_id: str = None, buy_database_id: str = None):
        """
        Initialize Notion client
        
        Args:
            api_token: Notion integration token
            database_id: DEPRECATED - Old watchlist database ID (kept for backward compatibility)
            signals_database_id: ID of signals database (Stoch RSI + MFI signals)
            buy_database_id: ID of buy database (final confirmed signals with WaveTrend)
        """
        if not api_token or api_token.startswith("YOUR_"):
            raise ConfigError("Valid Notion API token required")
        
        # signals_database_id is now required
        if not signals_database_id or signals_database_id.startswith("YOUR_"):
            raise ConfigError("Valid signals_database_id required")
        
        self.api_token = api_token
        self.database_id = database_id  # Deprecated but kept for compatibility
        self.signals_database_id = signals_database_id
        self.buy_database_id = buy_database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # Schema cache to avoid repeated API calls
        self._schema_cache: Dict[str, dict] = {}
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with timeout.
        
        Args:
            method: HTTP method (get, post, patch, delete)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        kwargs.setdefault('timeout', NOTION_TIMEOUT)
        kwargs.setdefault('headers', self.headers)
        return getattr(requests, method)(url, **kwargs)
    
    def _get_database_schema(self, database_id: str) -> Optional[dict]:
        """
        Get database schema with caching.
        
        Args:
            database_id: The Notion database ID
            
        Returns:
            Database schema properties dict or None if failed
        """
        if database_id in self._schema_cache:
            return self._schema_cache[database_id]
        
        try:
            schema_url = f"{self.base_url}/databases/{database_id}"
            schema_response = requests.get(schema_url, headers=self.headers, timeout=NOTION_TIMEOUT)
            schema_response.raise_for_status()
            schema_data = schema_response.json()
            
            properties = schema_data.get("properties", {})
            self._schema_cache[database_id] = properties
            logger.info("schema_cached", database_id=database_id[:8])
            return properties
            
        except Exception as e:
            logger.error("schema_fetch_failed", database_id=database_id[:8], error=str(e))
            return None
    
    def _find_title_property(self, properties: dict) -> Optional[str]:
        """Find the title property name from schema properties."""
        for prop_name, prop_info in properties.items():
            if prop_info.get("type") == "title":
                return prop_name
        return None
    
    def get_watchlist(self) -> Tuple[List[str], Dict[str, str]]:
        """
        Fetch watchlist symbols from Notion database
        
        Expects database to have a property called "Symbol" (or similar)
        containing the ticker symbols.
        
        Returns:
            Tuple of (symbols list, symbol_to_page_id dict)
            e.g., (["AAPL", "MSFT"], {"AAPL": "page_id_1", "MSFT": "page_id_2"})
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"
        
        try:
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            symbols = []
            symbol_to_page = {}
            
            # Parse results - look for symbol/ticker property
            for page in data.get("results", []):
                page_id = page.get("id")
                props = page.get("properties", {})
                
                # Try different common property names
                symbol = None
                for prop_name in ["Symbol", "Ticker", "Stock", "symbol", "ticker", "stock"]:
                    if prop_name in props:
                        prop_data = props[prop_name]
                        
                        # Handle different property types
                        if prop_data["type"] == "title":
                            title_content = prop_data.get("title", [])
                            if title_content:
                                symbol = title_content[0].get("plain_text", "").strip().upper()
                        
                        elif prop_data["type"] == "rich_text":
                            text_content = prop_data.get("rich_text", [])
                            if text_content:
                                symbol = text_content[0].get("plain_text", "").strip().upper()
                        
                        elif prop_data["type"] == "select":
                            select_data = prop_data.get("select")
                            if select_data:
                                symbol = select_data.get("name", "").strip().upper()
                        
                        if symbol:
                            break
                
                if symbol and page_id:
                    symbols.append(symbol)
                    symbol_to_page[symbol] = page_id
            
            logger.info("notion.watchlist_fetched", count=len(symbols), symbols=symbols)
            return symbols, symbol_to_page
            
        except requests.exceptions.RequestException as e:
            # Log detailed error response
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            logger.error("notion.fetch_failed", error=str(e), detail=error_detail)
            raise Exception(f"Failed to fetch watchlist from Notion: {e}\nDetail: {error_detail}")
        except Exception as e:
            logger.error("notion.parse_failed", error=str(e))
            raise Exception(f"Failed to parse Notion response: {e}")
    
    def add_to_signals(self, symbol: str, date_str: str = None) -> bool:
        """
        Add a symbol to the signals database
        
        Args:
            symbol: Stock ticker symbol
            date_str: Signal date (optional, defaults to today)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.signals_database_id:
            logger.warning("notion.no_signals_db", symbol=symbol)
            return False
        
        try:
            from datetime import date as dt
            signal_date = date_str or dt.today().isoformat()
            
            # Get cached schema
            properties = self._get_database_schema(self.signals_database_id)
            if not properties:
                logger.error("notion.schema_fetch_failed", database_id=self.signals_database_id)
                return False
            
            # Find the title and date properties
            title_property = self._find_title_property(properties)
            date_property = None
            
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "date":
                    date_property = prop_name
                    break
            
            if not title_property:
                logger.error("notion.no_title_property", database_id=self.signals_database_id)
                print(f"   ❌ Signals database has no title property")
                return False
            
            # Build payload with dynamic property names
            payload = {
                "parent": {"database_id": self.signals_database_id},
                "properties": {
                    title_property: {
                        "title": [
                            {
                                "text": {
                                    "content": symbol
                                }
                            }
                        ]
                    }
                }
            }
            
            # Add date if date property exists
            if date_property:
                payload["properties"][date_property] = {
                    "date": {
                        "start": signal_date
                    }
                }
            
            # Create the page
            create_url = f"{self.base_url}/pages"
            response = requests.post(create_url, headers=self.headers, json=payload, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            logger.info("notion.signal_added", symbol=symbol, date=signal_date, title_prop=title_property)
            return True
            
        except Exception as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            logger.error("notion.add_signal_failed", symbol=symbol, error=str(e), detail=error_detail)
            print(f"   ❌ Failed to add to signals: {error_detail}")
            return False
    
    def get_signals(self) -> Tuple[List[str], Dict[str, str]]:
        """
        Fetch symbols from signals database (first-stage signals)
        
        Returns:
            Tuple of (symbols list, symbol_to_page_id dict)
            
        Raises:
            Exception: If signals_database_id not configured or API request fails
        """
        if not self.signals_database_id:
            logger.warning("notion.no_signals_database", message="signals_database_id not configured")
            return ([], {})
        
        try:
            logger.info("notion.querying_signals_db", database_id=self.signals_database_id)
            url = f"{self.base_url}/databases/{self.signals_database_id}/query"
            
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.info("notion.empty_signals")
                return ([], {})
            
            # Detect title property name dynamically
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break
            
            if not title_property:
                raise ValueError("No title property found in signals database")
            
            symbols = []
            symbol_to_page = {}
            
            for page in results:
                page_id = page["id"]
                props = page.get("properties", {})
                
                # Extract symbol from title property
                title_data = props.get(title_property, {})
                title_content = title_data.get("title", [])
                
                if title_content and len(title_content) > 0:
                    symbol = title_content[0].get("text", {}).get("content", "").strip()
                    if symbol:
                        symbols.append(symbol)
                        symbol_to_page[symbol] = page_id
            
            logger.info("notion.signals_fetched", count=len(symbols), symbols=symbols)
            return (symbols, symbol_to_page)
            
        except Exception as e:
            logger.error("notion.fetch_signals_failed", error=str(e))
            raise
    
    def add_to_buy(self, symbol: str, signal_date: str) -> bool:
        """
        Add symbol to buy database (final confirmed signals with WaveTrend)
        
        Args:
            symbol: Stock ticker symbol
            signal_date: Date string (YYYY-MM-DD format)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.buy_database_id:
            logger.warning("notion.no_buy_database", symbol=symbol)
            return False
        
        try:
            # First, query the database to get schema
            query_url = f"{self.base_url}/databases/{self.buy_database_id}"
            response = requests.get(query_url, headers=self.headers, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            db_info = response.json()
            properties = db_info.get("properties", {})
            
            # Find title property and date property
            title_property = None
            date_property = None
            
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type")
                if prop_type == "title":
                    title_property = prop_name
                elif prop_type == "date":
                    date_property = prop_name
            
            if not title_property:
                raise ValueError("No title property found in buy database")
            
            # Build payload
            payload = {
                "parent": {"database_id": self.buy_database_id},
                "properties": {
                    title_property: {
                        "title": [
                            {
                                "text": {
                                    "content": symbol
                                }
                            }
                        ]
                    }
                }
            }
            
            # Add date if date property exists
            if date_property:
                payload["properties"][date_property] = {
                    "date": {
                        "start": signal_date
                    }
                }
            
            # Create the page
            create_url = f"{self.base_url}/pages"
            response = requests.post(create_url, headers=self.headers, json=payload, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            logger.info("notion.buy_added", symbol=symbol, date=signal_date, title_prop=title_property)
            return True
            
        except Exception as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            logger.error("notion.add_buy_failed", symbol=symbol, error=str(e), detail=error_detail)
            print(f"   ❌ Failed to add to buy: {error_detail}")
            return False
    
    def delete_from_signals(self, symbol: str) -> bool:
        """
        Delete a symbol from signals database by symbol name.
        
        Args:
            symbol: Stock ticker symbol to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.signals_database_id:
            logger.warning("notion.no_signals_db")
            return False
        
        try:
            # Get signals to find page_id
            signals, symbol_to_page = self.get_signals()
            
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
    
    def delete_from_buy(self, symbol: str) -> bool:
        """
        Delete a symbol from buy database by symbol name.
        
        Args:
            symbol: Stock ticker symbol to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.buy_database_id:
            logger.warning("notion.no_buy_db")
            return False
        
        try:
            # Get buy symbols with page IDs
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
    
    def delete_from_watchlist(self, symbol: str) -> bool:
        """
        Delete a symbol from watchlist database by symbol name.
        
        Args:
            symbol: Stock ticker symbol to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get watchlist to find page_id
            symbols, symbol_to_page = self.get_watchlist()
            
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
    
    def _get_symbol_page_map(self, database_id: str) -> Dict[str, str]:
        """
        Get symbol to page_id mapping from any database.
        
        Args:
            database_id: The ID of the database to query
            
        Returns:
            Dictionary mapping symbol names to page IDs
        """
        symbol_to_page = {}
        
        try:
            url = f"{self.base_url}/databases/{database_id}/query"
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
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

    def remove_duplicates_from_signals(self) -> int:
        """
        Remove duplicate symbols from signals database, keeping only the first occurrence.
        
        Returns:
            Number of duplicates removed
        """
        if not self.signals_database_id:
            return 0
        
        try:
            url = f"{self.base_url}/databases/{self.signals_database_id}/query"
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return 0
            
            # Detect title property
            first_page_props = results[0].get("properties", {})
            title_property = None
            for prop_name, prop_data in first_page_props.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                    break
            
            if not title_property:
                return 0
            
            # Track symbols and find duplicates
            seen_symbols = set()
            duplicate_pages = []
            
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
            
            logger.info("notion.duplicates_cleanup_complete", removed=removed, total_checked=len(results))
            return removed
            
        except Exception as e:
            logger.error("notion.remove_duplicates_failed", error=str(e))
            return 0

    def delete_page(self, page_id: str) -> bool:
        """
        Archive (delete) a page from Notion
        
        Args:
            page_id: The ID of the page to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # First check if page exists and is not already archived
            get_url = f"https://api.notion.com/v1/pages/{page_id}"
            check_response = requests.get(get_url, headers=self.headers, timeout=NOTION_TIMEOUT)
            
            if check_response.status_code == 404:
                logger.warning("notion.page_not_found", page_id=page_id)
                return True  # Already deleted, consider success
            
            if check_response.status_code == 200:
                page_data = check_response.json()
                if page_data.get("archived", False):
                    logger.info("notion.page_already_archived", page_id=page_id)
                    return True  # Already archived, consider success
            
            # Archive the page
            delete_url = f"https://api.notion.com/v1/pages/{page_id}"
            payload = {"archived": True}
            
            response = requests.patch(delete_url, headers=self.headers, json=payload, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            logger.info("notion.page_deleted", page_id=page_id)
            return True
            
        except Exception as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            logger.error("notion.delete_failed", page_id=page_id, error=str(e), detail=error_detail)
            return False
    
    def get_all_symbols(self) -> set:
        """
        Get all unique symbols across signals and buy databases
        
        Returns:
            Set of symbols that are already in signals or buy database
        """
        all_symbols = set()
        
        # Get from signals database
        if self.signals_database_id:
            try:
                signals_symbols, _ = self.get_signals()
                all_symbols.update(signals_symbols)
            except Exception as e:
                logger.warning("notion.get_signals_failed", error=str(e))
        
        # Get from buy database
        if self.buy_database_id:
            try:
                buy_symbols = self._get_symbols_from_database(self.buy_database_id)
                all_symbols.update(buy_symbols)
            except Exception as e:
                logger.warning("notion.get_buy_failed", error=str(e))
        
        return all_symbols
    
    def _get_symbols_from_database(self, database_id: str) -> list:
        """
        Generic method to fetch symbols from any database
        
        Args:
            database_id: The ID of the database to query
            
        Returns:
            List of symbols
        """
        try:
            url = f"{self.base_url}/databases/{database_id}/query"
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
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

    def add_to_watchlist(self, symbol: str, date_str: str = None) -> bool:
        """
        Add a symbol to the watchlist database (used by market scanner).
        
        Args:
            symbol: Stock ticker symbol
            date_str: Added date (optional, defaults to today)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from datetime import date as dt
            added_date = date_str or dt.today().isoformat()
            
            # Get cached schema
            properties = self._get_database_schema(self.database_id)
            if not properties:
                logger.error("notion.schema_fetch_failed", database_id=self.database_id)
                return False
            
            # Find the title property and date property
            title_property = self._find_title_property(properties)
            date_property = None
            
            for prop_name, prop_data in properties.items():
                # Look for "Added" date property
                if prop_data.get("type") == "date" and "add" in prop_name.lower():
                    date_property = prop_name
                    break
            
            if not title_property:
                logger.error("notion.no_title_property", database_id=self.database_id)
                return False
            
            # Build payload with dynamic property names
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": {
                    title_property: {
                        "title": [
                            {
                                "text": {
                                    "content": symbol
                                }
                            }
                        ]
                    }
                }
            }
            
            # Add date if date property exists
            if date_property:
                payload["properties"][date_property] = {
                    "date": {
                        "start": added_date
                    }
                }
            
            # Create the page
            url = f"{self.base_url}/pages"
            response = requests.post(url, headers=self.headers, json=payload, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            logger.info("notion.watchlist_added", symbol=symbol, date=added_date)
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error("notion.add_watchlist_failed", symbol=symbol, error=str(e))
            return False

    def update_watchlist_date(self, symbol: str, page_id: str = None) -> bool:
        """
        Update the date of an existing watchlist entry (for market scanner duplicates).
        
        This is used when market scanner finds a symbol that's already in watchlist.
        Instead of adding duplicate, we update the "Added" date to current date.
        
        Args:
            symbol: Stock symbol to update
            page_id: Notion page ID (if known, otherwise will fetch)
        
        Returns:
            bool: True if update successful, False otherwise
        """
        from datetime import date as date_module
        
        try:
            # If page_id not provided, fetch it
            if not page_id:
                _, symbol_to_page = self.get_watchlist()
                page_id = symbol_to_page.get(symbol)
                
                if not page_id:
                    logger.warning("notion.update_date_no_page", symbol=symbol)
                    return False
            
            # Update the "Added" property with current date
            url = f"{self.base_url}/pages/{page_id}"
            
            # Get today's date in ISO format (YYYY-MM-DD)
            today = date_module.today().isoformat()
            
            payload = {
                "properties": {
                    "Added": {
                        "date": {
                            "start": today
                        }
                    }
                }
            }
            
            response = requests.patch(url, headers=self.headers, json=payload, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            logger.info("notion.watchlist_date_updated", symbol=symbol, page_id=page_id)
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error("notion.update_date_failed", symbol=symbol, error=str(e))
            return False

    def cleanup_old_signals(self, max_age_days: int = 7) -> int:
        """
        Remove old entries from signals database.
        
        Signals older than max_age_days will be archived (deleted).
        This prevents stale signals from accumulating.
        
        Args:
            max_age_days: Maximum age in days before signal is removed (default: 7)
            
        Returns:
            int: Number of signals removed
        """
        from datetime import datetime, timedelta
        
        if not self.signals_database_id:
            logger.warning("notion.cleanup_no_signals_db")
            return 0
        
        try:
            url = f"{self.base_url}/databases/{self.signals_database_id}/query"
            response = requests.post(url, headers=self.headers, json={}, timeout=NOTION_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return 0
            
            # Find date property name
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
                
                # Get signal date
                signal_date = None
                if date_property:
                    date_data = props.get(date_property, {}).get("date")
                    if date_data and date_data.get("start"):
                        try:
                            signal_date = datetime.fromisoformat(date_data["start"].replace("Z", "+00:00"))
                            # Make naive for comparison
                            if signal_date.tzinfo:
                                signal_date = signal_date.replace(tzinfo=None)
                        except:
                            pass
                
                # If no date or date is old, remove it
                should_remove = False
                if signal_date is None:
                    # No date = old/manual entry, remove it
                    should_remove = True
                elif signal_date < cutoff_date:
                    should_remove = True
                
                if should_remove:
                    if self.delete_page(page_id):
                        removed_count += 1
                        # Get symbol for logging
                        for prop_name, prop_data in props.items():
                            if prop_data.get("type") == "title":
                                title_content = prop_data.get("title", [])
                                if title_content:
                                    symbol = title_content[0].get("text", {}).get("content", "unknown")
                                    logger.info("notion.old_signal_removed", symbol=symbol, page_id=page_id)
                                break
            
            logger.info("notion.signals_cleanup_complete", removed=removed_count)
            return removed_count
            
        except Exception as e:
            logger.error("notion.cleanup_failed", error=str(e))
            return 0

    def symbol_exists_in_signals(self, symbol: str) -> bool:
        """
        Check if a symbol already exists in signals database.
        
        Used to prevent duplicate entries (including manual ones).
        
        Args:
            symbol: Stock ticker symbol to check
            
        Returns:
            bool: True if symbol exists, False otherwise
        """
        if not self.signals_database_id:
            return False
        
        try:
            symbols, _ = self.get_signals()
            return symbol.upper() in [s.upper() for s in symbols]
        except:
            return False

    def symbol_exists_in_buy(self, symbol: str) -> bool:
        """
        Check if a symbol already exists in buy database.
        
        Args:
            symbol: Stock ticker symbol to check
            
        Returns:
            bool: True if symbol exists, False otherwise
        """
        if not self.buy_database_id:
            return False
        
        try:
            buy_symbols = self._get_symbols_from_database(self.buy_database_id)
            return symbol.upper() in [s.upper() for s in buy_symbols]
        except:
            return False

