"""Notion API client for fetching watchlist from database"""

from typing import List, Dict, Tuple
import requests
from .logger import logger
from .exceptions import ConfigError


class NotionClient:
    """Client for interacting with Notion API to fetch watchlist"""
    
    def __init__(self, api_token: str, database_id: str, signals_database_id: str = None):
        """
        Initialize Notion client
        
        Args:
            api_token: Notion integration token
            database_id: ID of the watchlist database
            signals_database_id: Optional ID of signals database to move completed signals
        """
        if not api_token or api_token.startswith("YOUR_"):
            raise ConfigError("Valid Notion API token required")
        
        if not database_id or database_id.startswith("YOUR_"):
            raise ConfigError("Valid Notion database ID required")
        
        self.api_token = api_token
        self.database_id = database_id
        self.signals_database_id = signals_database_id
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
    
    def add_to_signals(self, symbol: str, date: str = None) -> bool:
        """
        Add a symbol to the signals database
        
        Args:
            symbol: Stock ticker symbol
            date: Signal date (optional, defaults to today)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.signals_database_id:
            logger.warning("notion.no_signals_db", symbol=symbol)
            return False
        
        url = f"{self.base_url}/pages"
        
        try:
            from datetime import date as dt
            signal_date = date or dt.today().isoformat()
            
            payload = {
                "parent": {"database_id": self.signals_database_id},
                "properties": {
                    "Symbol": {
                        "title": [
                            {
                                "text": {
                                    "content": symbol
                                }
                            }
                        ]
                    },
                    "Date": {
                        "date": {
                            "start": signal_date
                        }
                    }
                }
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info("notion.signal_added", symbol=symbol, date=signal_date)
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
