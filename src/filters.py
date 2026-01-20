"""Market filters for stock screening.

This module contains the filtering logic used in the two-stage screening process:
- Stage 1 (Market Filter): Market cap, Stoch RSI, Bollinger Bands, MFI
- Stage 2 (WaveTrend): Daily/Weekly WaveTrend confirmation

Extracted from main.py for better separation of concerns.
"""

import yfinance as yf

from .cache import MarketCapCache
from .data_source_yfinance import daily_ohlc, weekly_ohlc
from .indicators import (
    bollinger_bands,
    mfi,
    mfi_uptrend,
    stoch_rsi_buy,
    stochastic_rsi,
    wavetrend,
    wavetrend_buy,
)
from .logger import logger
from .market_symbols import get_market_cap_threshold

# Optional: Alpha Vantage support
try:
    from .data_source_alpha_vantage import alpha_vantage_ohlc
except ImportError:
    alpha_vantage_ohlc = None


# =============================================================================
# Stage 1: Market Filter
# =============================================================================


def check_market_filter(
    symbol: str, cache: MarketCapCache | None = None, alpha_vantage_key: str | None = None
) -> dict | None:
    """
    Check if symbol passes market scanner filters (Stage 1).

    Uses hybrid approach:
    - yfinance: Market cap (fast, unlimited)
    - Alpha Vantage: Technical indicators (precise, if key provided)

    Filters (must pass ALL):
    1. Market Cap >= 50B USD (cached for 24h)
    2. Stoch RSI (3,3,14,14) - D < 20 (oversold)
    3. Price < Bollinger Lower Band (20 period)
    4. MFI (14) <= 40 (weak momentum)

    Args:
        symbol: Stock ticker symbol
        cache: Optional MarketCapCache instance for performance
        alpha_vantage_key: Optional Alpha Vantage API key for precise indicators

    Returns:
        dict with 'passed' (bool) and indicator values, or None if data unavailable

    Examples:
        >>> result = check_market_filter("AAPL")
        >>> if result and result['passed']:
        ...     print(f"AAPL passed with MFI={result['mfi']:.1f}")
    """
    try:
        logger.info(
            "market_filter_check", symbol=symbol, using_alpha_vantage=bool(alpha_vantage_key and alpha_vantage_ohlc)
        )

        # Get price data - use Alpha Vantage if available, else yfinance
        if alpha_vantage_key and alpha_vantage_ohlc is not None:
            df = alpha_vantage_ohlc(symbol, alpha_vantage_key, days=100)
            if df is None:
                # Fallback to yfinance
                logger.warning("alpha_vantage_failed_fallback_yfinance", symbol=symbol)
                df = daily_ohlc(symbol)
        else:
            df = daily_ohlc(symbol)

        if df is None or len(df) < 30:
            logger.warning("market_filter_insufficient_data", symbol=symbol)
            return None

        # 1. Check Market Cap >= 50B USD (with caching)
        market_cap = None
        if cache:
            market_cap = cache.get(symbol)

        if market_cap is None:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                market_cap = info.get("marketCap", 0)

                # Cache the result
                if cache and market_cap > 0:
                    cache.set(symbol, market_cap)

            except Exception as e:
                logger.warning("market_filter_market_cap_error", symbol=symbol, error=str(e))
                return None

        threshold = get_market_cap_threshold()
        if market_cap < threshold:
            logger.info("market_filter_market_cap_too_low", symbol=symbol, market_cap=market_cap, threshold=threshold)
            return {"passed": False, "reason": "market_cap_too_low"}

        # 2. Calculate Stochastic RSI (3,3,14,14)
        stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        stoch_d = float(stoch_ind["d"].iloc[-1])
        stoch_k = float(stoch_ind["k"].iloc[-1])

        if stoch_d >= 20:
            logger.info("market_filter_stoch_not_oversold", symbol=symbol, stoch_d=stoch_d)
            return {"passed": False, "reason": "stoch_d_not_oversold", "stoch_d": stoch_d}

        # 3. Check Bollinger Bands - Price < Lower Band
        bb = bollinger_bands(df["Close"], period=20, std_dev=2.0)
        current_price = float(df["Close"].iloc[-1])
        bb_lower = float(bb["lower"].iloc[-1])

        if current_price >= bb_lower:
            logger.info("market_filter_price_not_below_bb", symbol=symbol, price=current_price, bb_lower=bb_lower)
            return {"passed": False, "reason": "price_not_below_bb", "price": current_price, "bb_lower": bb_lower}

        # 4. Check MFI <= 40
        mfi_values = mfi(df, period=14)
        mfi_current = float(mfi_values.iloc[-1])

        if mfi_current > 40:
            logger.info("market_filter_mfi_too_high", symbol=symbol, mfi=mfi_current)
            return {"passed": False, "reason": "mfi_too_high", "mfi": mfi_current}

        # All filters passed!
        logger.info(
            "market_filter_passed",
            symbol=symbol,
            market_cap=market_cap,
            stoch_d=stoch_d,
            stoch_k=stoch_k,
            price=current_price,
            bb_lower=bb_lower,
            mfi=mfi_current,
        )

        return {
            "passed": True,
            "market_cap": market_cap,
            "stoch_d": stoch_d,
            "stoch_k": stoch_k,
            "price": current_price,
            "bb_lower": bb_lower,
            "mfi": mfi_current,
        }

    except Exception as e:
        logger.error("market_filter_check_failed", symbol=symbol, error=str(e))
        return None


def check_signal_criteria(symbol: str) -> dict | None:
    """
    Check if symbol passes signal criteria (Stoch RSI cross + MFI uptrend).

    This is the second part of Stage 1 filtering, applied after market_filter passes.

    Criteria:
    1. Stoch RSI bullish cross (K crosses above D in oversold zone)
    2. MFI shows 3-day uptrend (accumulation starting)

    Args:
        symbol: Stock ticker symbol

    Returns:
        dict with indicator values if signal found, None otherwise
    """
    try:
        df = daily_ohlc(symbol)
        if df is None or len(df) < 30:
            return None

        # Calculate indicators
        stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        mfi_values = mfi(df, period=14)

        # Check Stochastic RSI bullish cross
        has_stoch_signal = stoch_rsi_buy(stoch_ind)

        # Check MFI 3-day uptrend
        mfi_trending_up = mfi_uptrend(mfi_values, days=3)

        if has_stoch_signal and mfi_trending_up:
            return {
                "stoch_k": float(stoch_ind["k"].iloc[-1]),
                "stoch_d": float(stoch_ind["d"].iloc[-1]),
                "mfi": float(mfi_values.iloc[-1]),
                "mfi_uptrend": True,
            }

        return None

    except Exception as e:
        logger.warning("signal_check_failed", symbol=symbol, error=str(e))
        return None


# =============================================================================
# Stage 2: WaveTrend Confirmation
# =============================================================================


def check_wavetrend_signal(symbol: str, use_multi_timeframe: bool = True) -> bool:
    """
    Check if symbol has WaveTrend buy signal (Stage 2 confirmation).

    Conditions:
    1. Daily: WaveTrend WT1 crosses above WT2 in oversold zone (< -53)
    2. Weekly (optional): WaveTrend must NOT be extremely overbought (WT1 < 60)

    Args:
        symbol: Stock ticker symbol
        use_multi_timeframe: If True, confirms daily signal with weekly trend

    Returns:
        True if WaveTrend buy signal detected

    Examples:
        >>> if check_wavetrend_signal("AAPL"):
        ...     print("WaveTrend confirmed - ready to buy!")
    """
    try:
        logger.info("checking_wavetrend", symbol=symbol, multi_timeframe=use_multi_timeframe)

        # Get daily price data
        df_daily = daily_ohlc(symbol)

        if df_daily is None or len(df_daily) < 30:
            logger.warning("insufficient_data", symbol=symbol)
            return False

        # Calculate daily WaveTrend
        wt_daily = wavetrend(df_daily, channel_length=10, average_length=21)

        # Check for daily WaveTrend buy signal
        has_daily_signal = wavetrend_buy(wt_daily, lookback_days=3, oversold_level=-53)

        if not has_daily_signal:
            return False

        # Multi-timeframe confirmation (optional)
        if use_multi_timeframe:
            df_weekly = weekly_ohlc(symbol, weeks=52)

            if df_weekly is not None and len(df_weekly) >= 14:
                wt_weekly = wavetrend(df_weekly, channel_length=10, average_length=21)
                weekly_wt1 = float(wt_weekly["wt1"].iloc[-1])

                # Reject if weekly is extremely overbought (prevents buying at tops)
                if weekly_wt1 > 60:
                    logger.info("wavetrend_rejected_weekly", symbol=symbol, daily_signal=True, weekly_wt1=weekly_wt1)
                    return False

                logger.info(
                    "wavetrend_multi_timeframe_confirmed",
                    symbol=symbol,
                    daily_wt1=float(wt_daily["wt1"].iloc[-1]),
                    weekly_wt1=weekly_wt1,
                )
            else:
                logger.warning("weekly_data_unavailable", symbol=symbol)

        if has_daily_signal:
            logger.info(
                "wavetrend_signal_found",
                symbol=symbol,
                wt1=float(wt_daily["wt1"].iloc[-1]),
                wt2=float(wt_daily["wt2"].iloc[-1]),
            )

        return has_daily_signal

    except Exception as e:
        logger.error("wavetrend_check_failed", symbol=symbol, error=str(e))
        return False


def get_wavetrend_values(symbol: str) -> dict | None:
    """
    Get current WaveTrend indicator values for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        dict with 'daily_wt1', 'daily_wt2', 'weekly_wt1' values, or None if unavailable
    """
    try:
        df_daily = daily_ohlc(symbol)
        if df_daily is None or len(df_daily) < 30:
            return None

        wt_daily = wavetrend(df_daily, channel_length=10, average_length=21)

        result = {
            "daily_wt1": float(wt_daily["wt1"].iloc[-1]),
            "daily_wt2": float(wt_daily["wt2"].iloc[-1]),
        }

        # Try to get weekly data
        df_weekly = weekly_ohlc(symbol, weeks=52)
        if df_weekly is not None and len(df_weekly) >= 14:
            wt_weekly = wavetrend(df_weekly, channel_length=10, average_length=21)
            result["weekly_wt1"] = float(wt_weekly["wt1"].iloc[-1])

        return result

    except Exception as e:
        logger.warning("get_wavetrend_values_failed", symbol=symbol, error=str(e))
        return None
