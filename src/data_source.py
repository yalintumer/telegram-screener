import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from functools import lru_cache
from datetime import datetime
from .logger import logger
from .exceptions import DataSourceError


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True
)
def _fetch_av_with_retry(symbol: str, api_key: str) -> dict:
    """Fetch from AlphaVantage with retry on network errors"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "apikey": api_key,
        "outputsize": "compact"
    }
    logger.debug("api.request", symbol=symbol, provider="alphavantage")
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=256)
def _cached_fetch_av(symbol: str, api_key: str, date_key: str) -> dict:
    """Cached wrapper - cache key includes date for daily refresh"""
    return _fetch_av_with_retry(symbol, api_key)


def daily_ohlc(symbol: str, provider: str, api_key: str) -> pd.DataFrame | None:
    """
    Fetch daily OHLC data with caching and retry logic
    
    Args:
        symbol: Ticker symbol
        provider: Data provider name
        api_key: API key
    
    Returns:
        DataFrame with 'close' column or None if no data
        
    Raises:
        DataSourceError: On API errors or rate limits
    """
    try:
        provider = (provider or "").lower()
        if provider.startswith("alpha"):
            # Use today's date as cache key for daily refresh
            date_key = datetime.now().strftime("%Y-%m-%d")
            js = _cached_fetch_av(symbol, api_key, date_key)
            
            # Check for API errors
            if "Error Message" in js:
                raise DataSourceError(f"API error: {js['Error Message']}")
            
            ts = js.get("Time Series (Daily)", {})
            if not ts:
                if "Note" in js:
                    logger.warning("api.rate_limit", symbol=symbol, message=js["Note"])
                    raise DataSourceError(f"Rate limit: {js['Note']}")
                if "Information" in js:
                    logger.warning("api.info", symbol=symbol, message=js["Information"])
                logger.warning("api.no_data", symbol=symbol)
                return None
            
            df = (
                pd.DataFrame(ts).T
                .rename(columns={"4. close": "close"})
                .astype(float)
                .sort_index()
            )
            logger.info("data.fetched", symbol=symbol, rows=len(df))
            return df[["close"]]
        else:
            raise DataSourceError(f"Unsupported provider: {provider}")
            
    except requests.RequestException as e:
        logger.error("data.network_error", symbol=symbol, error=str(e))
        raise DataSourceError(f"Network error for {symbol}: {e}")
    except Exception as e:
        logger.error("data.error", symbol=symbol, error=str(e))
        raise DataSourceError(f"Data fetch failed for {symbol}: {e}")
