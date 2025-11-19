"""Notion API client for fetching watchlist from database"""

from typing import List
import requests
from .logger import logger
from .exceptions import ConfigError


class NotionClient:
    """Client for interacting with Notion API to fetch watchlist"""
    
    def __init__(self, api_token: str, database_id: str):
        """
        Initialize Notion client
        
        Args:
            api_token: Notion integration token
            database_id: ID of the database containing watchlist
        """
        if not api_token or api_token.startswith("YOUR_"):
            raise ConfigError("Valid Notion API token required")
        
        if not database_id or database_id.startswith("YOUR_"):
            raise ConfigError("Valid Notion database ID required")
        
        self.api_token = api_token
        self.database_id = database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    def get_watchlist(self) -> List[str]:
        """
        Fetch watchlist symbols from Notion database
        
        Expects database to have a property called "Symbol" (or similar)
        containing the ticker symbols.
        
        Returns:
            List of ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"
        
        try:
            response = requests.post(url, headers=self.headers, json={})
            response.raise_for_status()
            
            data = response.json()
            symbols = []
            
            # Parse results - look for symbol/ticker property
            for page in data.get("results", []):
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
                
                if symbol:
                    symbols.append(symbol)
            
            logger.info("notion.watchlist_fetched", count=len(symbols), symbols=symbols)
            return symbols
            
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
