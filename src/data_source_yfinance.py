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


def hourly_4h_ohlc(symbol: str, days: int = 30) -> pd.DataFrame | None:
    """
    Fetch 4-hour OHLC data from Yahoo Finance

    Args:
        symbol: Stock ticker symbol
        days: Number of days of historical data (max 60 for intraday)

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
        Returns None if data fetch fails or insufficient data
    """
    try:
        # Rate limit yfinance calls
        rate_limit("yfinance")

        logger.info("yfinance.fetch_4h", symbol=symbol, days=days)

        # yfinance only allows 60 days for intraday data
        days = min(days, 60)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Fetch data - use 1h and resample to 4h
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1h")

        if df.empty:
            logger.warning("yfinance.no_4h_data", symbol=symbol)
            return None

        # Resample 1h to 4h
        df_4h = df.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        df_4h = df_4h.dropna()

        # Clean and prepare data
        df_4h = df_4h.reset_index()
        df_4h = df_4h.rename(columns={"Datetime": "Date"})
        df_4h = df_4h[["Date", "Open", "High", "Low", "Close", "Volume"]]

        if len(df_4h) < 30:  # Minimum needed for WaveTrend
            logger.warning("yfinance.insufficient_4h_data", symbol=symbol, rows=len(df_4h))
            return None

        logger.info("yfinance.4h_success", symbol=symbol, rows=len(df_4h))
        return df_4h

    except Exception as e:
        logger.error("yfinance.4h_error", symbol=symbol, error=str(e))
        return None
