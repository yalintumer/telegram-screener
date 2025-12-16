"""
Alpha Vantage data source for precise technical indicators
Used alongside yfinance for hybrid approach:
- yfinance: Market cap, general info (fast, unlimited)
- Alpha Vantage: Technical indicators (precise, 500 calls/day)
"""

import pandas as pd
from alpha_vantage.timeseries import TimeSeries

from .exceptions import DataSourceError
from .logger import logger


class AlphaVantageSource:
    """Alpha Vantage API wrapper for precise technical data"""

    def __init__(self, api_key: str):
        """
        Initialize Alpha Vantage client
        
        Args:
            api_key: Alpha Vantage API key
        """
        if not api_key:
            raise DataSourceError("Alpha Vantage API key is required")

        self.api_key = api_key
        self.ts = TimeSeries(key=api_key, output_format='pandas')
        logger.info("alpha_vantage.initialized")

    def daily_ohlc(self, symbol: str, outputsize: str = 'compact') -> pd.DataFrame | None:
        """
        Fetch daily OHLC data from Alpha Vantage
        
        Args:
            symbol: Stock ticker symbol
            outputsize: 'compact' (100 days) or 'full' (20+ years)
            
        Returns:
            DataFrame with columns: Date (index), Open, High, Low, Close, Volume
            Returns None if data fetch fails
        """
        try:
            logger.info("alpha_vantage.fetch", symbol=symbol, outputsize=outputsize)

            # Fetch data
            data, meta_data = self.ts.get_daily(symbol=symbol, outputsize=outputsize)

            if data.empty:
                logger.warning("alpha_vantage.no_data", symbol=symbol)
                return None

            # Sort by date (oldest first) for proper rolling calculations
            data = data.sort_index(ascending=True)

            # Rename columns to match yfinance format
            data = data.rename(columns={
                '1. open': 'Open',
                '2. high': 'High',
                '3. low': 'Low',
                '4. close': 'Close',
                '5. volume': 'Volume'
            })

            # Keep only needed columns
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

            # Reset index to have Date as column
            data = data.reset_index()
            data = data.rename(columns={'date': 'Date'})

            logger.info("alpha_vantage.success", symbol=symbol, rows=len(data))
            return data

        except Exception as e:
            logger.error("alpha_vantage.error", symbol=symbol, error=str(e))
            return None

    def get_latest_price(self, symbol: str) -> float | None:
        """
        Get latest closing price
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Latest closing price or None
        """
        try:
            data = self.daily_ohlc(symbol, outputsize='compact')
            if data is not None and len(data) > 0:
                return float(data['Close'].iloc[-1])
            return None
        except Exception as e:
            logger.error("alpha_vantage.price_error", symbol=symbol, error=str(e))
            return None


# Global instance (initialized when needed)
_alpha_vantage_instance: AlphaVantageSource | None = None


def get_alpha_vantage(api_key: str) -> AlphaVantageSource:
    """
    Get or create Alpha Vantage instance (singleton pattern)
    
    Args:
        api_key: Alpha Vantage API key
        
    Returns:
        AlphaVantageSource instance
    """
    global _alpha_vantage_instance

    if _alpha_vantage_instance is None:
        _alpha_vantage_instance = AlphaVantageSource(api_key)

    return _alpha_vantage_instance


def alpha_vantage_ohlc(symbol: str, api_key: str, days: int = 100) -> pd.DataFrame | None:
    """
    Convenience function to fetch OHLC data
    
    Args:
        symbol: Stock ticker symbol
        api_key: Alpha Vantage API key
        days: Number of days (100 for compact, more for full)
        
    Returns:
        DataFrame with OHLC data
    """
    av = get_alpha_vantage(api_key)
    outputsize = 'compact' if days <= 100 else 'full'
    data = av.daily_ohlc(symbol, outputsize=outputsize)

    if data is not None and days < len(data):
        # Return only requested number of days
        data = data.tail(days)

    return data
