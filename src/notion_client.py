"""Notion API client for fetching watchlist from database"""

from typing import List, Dict, Tuple
import requests
from .logger import logger
from .exceptions import ConfigError


class NotionClient:
    """Client for interacting with Notion API to fetch watchlist"""
    
    def __init__(self, api_token: str, database_id: str, signals_database_id: str = None, buy_database_id: str = None):
        """
        Initialize Notion client
        
        Args:
            api_token: Notion integration token
            database_id: ID of the watchlist database
            signals_database_id: Optional ID of signals database (Stoch RSI + MFI signals)
            buy_database_id: Optional ID of buy database (final confirmed signals with WaveTrend)
        """
        if not api_token or api_token.startswith("YOUR_"):
            raise ConfigError("Valid Notion API token required")
        
        if not database_id or database_id.startswith("YOUR_"):
            raise ConfigError("Valid Notion database ID required")
        
        self.api_token = api_token
        self.database_id = database_id
        self.signals_database_id = signals_database_id
        self.buy_database_id = buy_database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
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
            response = requests.post(url, headers=self.headers, json={})
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
    
    def delete_page(self, page_id: str) -> bool:
        """
        Delete (archive) a page from Notion database
        
        Args:
            page_id: ID of the page to delete
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/pages/{page_id}"
        
        try:
            # Archive the page (soft delete)
            response = requests.patch(
                url, 
                headers=self.headers, 
                json={"archived": True}
            )
            response.raise_for_status()
            logger.info("notion.page_deleted", page_id=page_id)
            return True
            
        except Exception as e:
            logger.error("notion.delete_failed", page_id=page_id, error=str(e))
            return False
    
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
            
            # First, get the database schema to find the title property name
            schema_url = f"{self.base_url}/databases/{self.signals_database_id}"
            schema_response = requests.get(schema_url, headers=self.headers)
            schema_response.raise_for_status()
            schema_data = schema_response.json()
            
            # Find the title property (first property is usually title)
            properties = schema_data.get("properties", {})
            title_property = None
            date_property = None
            
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "title":
                    title_property = prop_name
                if prop_data.get("type") == "date":
                    date_property = prop_name
            
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
            response = requests.post(create_url, headers=self.headers, json=payload)
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
            
            response = requests.post(url, headers=self.headers, json={})
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
            response = requests.get(query_url, headers=self.headers)
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
            response = requests.post(create_url, headers=self.headers, json=payload)
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
    
    def delete_page(self, page_id: str) -> bool:
        """
        Archive (delete) a page from Notion
        
        Args:
            page_id: The ID of the page to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            delete_url = f"https://api.notion.com/v1/pages/{page_id}"
            payload = {"archived": True}
            
            response = requests.patch(delete_url, headers=self.headers, json=payload)
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
            response = requests.post(url, headers=self.headers, json={})
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

