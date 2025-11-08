"""
Yahoo Finance data source using yfinance library
Free, unlimited, no API key required!
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from .logger import logger
from .exceptions import DataSourceError


def daily_ohlc(symbol: str, days: int = 100) -> pd.DataFrame:
    """
    Fetch daily OHLC data from Yahoo Finance
    
    Args:
        symbol: Stock ticker symbol
        days: Number of days of historical data
        
    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
        
    Raises:
        DataSourceError: If data fetch fails
    """
    try:
        logger.info("yfinance.fetch", symbol=symbol, days=days)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 30)  # Extra buffer
        
        # Fetch data
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if df.empty:
            logger.warning("yfinance.no_data", symbol=symbol)
            raise DataSourceError(f"No data available for {symbol}")
        
        # Clean and prepare data
        df = df.reset_index()
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.dropna()
        
        # Keep only requested number of days
        df = df.tail(days)
        
        if len(df) < 14:  # Minimum needed for RSI
            logger.warning("yfinance.insufficient_data", symbol=symbol, rows=len(df))
            raise DataSourceError(f"Insufficient data for {symbol}: only {len(df)} days")
        
        logger.info("yfinance.success", symbol=symbol, rows=len(df))
        return df
        
    except DataSourceError:
        raise
    except Exception as e:
        logger.error("yfinance.error", symbol=symbol, error=str(e))
        raise DataSourceError(f"Failed to fetch data for {symbol}: {str(e)}")
