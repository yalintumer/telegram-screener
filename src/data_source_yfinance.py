"""
Yahoo Finance data source using yfinance library
Free, unlimited, no API key required!
"""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from .logger import logger
from .rate_limiter import rate_limit


def daily_ohlc(symbol: str, days: int = 100) -> pd.DataFrame | None:
    """
    Fetch daily OHLC data from Yahoo Finance

    Args:
        symbol: Stock ticker symbol
        days: Number of days of historical data

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
        Returns None if data fetch fails or insufficient data
    """
    try:
        # Rate limit yfinance calls
        rate_limit("yfinance")

        logger.info("yfinance.fetch", symbol=symbol, days=days)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 30)  # Extra buffer

        # Fetch data
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1d")

        if df.empty:
            logger.warning("yfinance.no_data", symbol=symbol)
            return None

        # Clean and prepare data
        df = df.reset_index()
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df = df.dropna()

        # Keep only requested number of days
        df = df.tail(days)

        if len(df) < 14:  # Minimum needed for RSI
            logger.warning("yfinance.insufficient_data", symbol=symbol, rows=len(df))
            return None

        logger.info("yfinance.success", symbol=symbol, rows=len(df))
        return df

    except Exception as e:
        logger.error("yfinance.error", symbol=symbol, error=str(e))
        return None


def weekly_ohlc(symbol: str, weeks: int = 52) -> pd.DataFrame | None:
    """
    Fetch weekly OHLC data from Yahoo Finance

    Args:
        symbol: Stock ticker symbol
        weeks: Number of weeks of historical data

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
        Returns None if data fetch fails or insufficient data
    """
    try:
        # Rate limit yfinance calls
        rate_limit("yfinance")

        logger.info("yfinance.fetch_weekly", symbol=symbol, weeks=weeks)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=weeks * 7 + 60)  # Extra buffer

        # Fetch data
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1wk")

        if df.empty:
            logger.warning("yfinance.no_weekly_data", symbol=symbol)
            return None

        # Clean and prepare data
        df = df.reset_index()
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df = df.dropna()

        # Keep only requested number of weeks
        df = df.tail(weeks)

        if len(df) < 14:  # Minimum needed for RSI
            logger.warning("yfinance.insufficient_weekly_data", symbol=symbol, rows=len(df))
            return None

        logger.info("yfinance.weekly_success", symbol=symbol, rows=len(df))
        return df

    except Exception as e:
        logger.error("yfinance.weekly_error", symbol=symbol, error=str(e))
        return None
