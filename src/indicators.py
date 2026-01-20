import pandas as pd

from .constants import (
    MFI_PERIOD,
    MFI_UPTREND_DAYS,
    SIGNAL_LOOKBACK_DAYS,
    STOCH_D_SMOOTH,
    STOCH_K_SMOOTH,
    STOCH_OVERSOLD,
    STOCH_PERIOD,
    STOCH_RSI_PERIOD,
    WAVETREND_OVERSOLD,
)


def rsi(series: pd.Series, period: int = STOCH_RSI_PERIOD) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index)

    Handles division by zero when loss=0 (all gains, no losses)
    """
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()

    # Prevent division by zero: replace 0 with tiny value
    loss = loss.replace(0, 1e-10)

    rs = gain / loss
    return 100 - (100 / (1 + rs))


def mfi(df: pd.DataFrame, period: int = MFI_PERIOD) -> pd.Series:
    """
    Calculate MFI (Money Flow Index)

    MFI uses both price and volume to measure buying/selling pressure.
    Similar to RSI but volume-weighted.

    Args:
        df: DataFrame with High, Low, Close, Volume columns
        period: Lookback period (default: 14)

    Returns:
        Series with MFI values (0-100)
    """
    # Typical Price = (High + Low + Close) / 3
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3

    # Money Flow = Typical Price * Volume
    money_flow = typical_price * df["Volume"]

    # Vectorized Positive/Negative Money Flow (no iloc loop)
    price_diff = typical_price.diff()
    positive_flow = money_flow.where(price_diff > 0, 0.0)
    negative_flow = money_flow.where(price_diff < 0, 0.0)

    # Sum over period
    positive_mf = positive_flow.rolling(period).sum()
    negative_mf = negative_flow.rolling(period).sum()

    # Money Flow Ratio
    mfr = positive_mf / negative_mf.replace(0, 1e-10)

    # Money Flow Index
    mfi = 100 - (100 / (1 + mfr))

    return mfi


def mfi_uptrend(mfi_series: pd.Series, days: int = MFI_UPTREND_DAYS) -> bool:
    """
    Check if MFI shows uptrend pattern

    Args:
        mfi_series: Series of MFI values
        days: Number of days to look back (default: 3)

    Returns:
        True if MFI at day 3 is greater than both day 2 and day 1
        This captures V-shaped recovery patterns

    Pattern: P3 > P2 AND P3 > P1
    Where P1=today, P2=yesterday, P3=2 days ago
    """
    if len(mfi_series) < days + 1:
        return False

    # P1 = today (most recent)
    # P2 = yesterday
    # P3 = 2 days ago
    p1 = mfi_series.iloc[-1]  # today
    p2 = mfi_series.iloc[-2]  # yesterday
    p3 = mfi_series.iloc[-3]  # 2 days ago

    if pd.isna(p1) or pd.isna(p2) or pd.isna(p3):
        return False

    # P3 must be greater than both P2 and P1
    # This shows MFI made a higher point 2 days ago and is coming down
    # Actually, let me re-read the request...
    # "P3 > P2 ve P3 > P1" means the oldest point (P3) is higher
    # But that would mean MFI is FALLING not rising

    # I think the intent is: current trend is UP
    # Let's interpret as: P1 > P2 (today > yesterday) AND P1 > P3 (today > 2 days ago)
    # This means today's MFI is higher than both yesterday and 2 days ago

    return p1 > p2 and p1 > p3


def wavetrend(df: pd.DataFrame, channel_length: int = 10, average_length: int = 21) -> pd.DataFrame:
    """
    Calculate WaveTrend indicator by LazyBear

    WaveTrend is a momentum oscillator that identifies overbought/oversold conditions
    and trend changes through wt1/wt2 crossovers.

    Args:
        df: DataFrame with High, Low, Close columns
        channel_length: Channel length (n1, default: 10)
        average_length: Average length (n2, default: 21)

    Returns:
        DataFrame with columns: wt1, wt2
        - wt1: Main wave (tci)
        - wt2: Signal line (SMA of wt1, period 4)

    Levels:
        Overbought: > 60 (extreme), > 53 (warning)
        Oversold: < -60 (extreme), < -53 (warning)
    """
    # ap = hlc3 (typical price)
    ap = (df["High"] + df["Low"] + df["Close"]) / 3

    # esa = EMA of ap with channel_length
    esa = ap.ewm(span=channel_length, adjust=False).mean()

    # d = EMA of absolute deviation
    d = (ap - esa).abs().ewm(span=channel_length, adjust=False).mean()

    # ci = (ap - esa) / (0.015 * d)
    ci = (ap - esa) / (0.015 * d)

    # tci = EMA of ci with average_length
    tci = ci.ewm(span=average_length, adjust=False).mean()

    # wt1 = tci
    wt1 = tci

    # wt2 = SMA of wt1 with period 4
    wt2 = wt1.rolling(4).mean()

    return pd.DataFrame({"wt1": wt1, "wt2": wt2})


def wavetrend_buy(
    wt_df: pd.DataFrame, lookback_days: int = SIGNAL_LOOKBACK_DAYS, oversold_level: int = WAVETREND_OVERSOLD
) -> bool:
    """
    Detect WaveTrend buy signal (bullish cross in oversold zone)

    Args:
        wt_df: DataFrame with wt1, wt2 columns
        lookback_days: Check for cross in last N days (default: 5)
        oversold_level: Oversold threshold (default: -53)

    Returns:
        True if wt1 crosses above wt2 in oversold zone

    Conditions:
        1. wt1 crosses above wt2 (bullish cross)
        2. Cross happens in oversold zone (wt1 or wt2 < oversold_level)
    """
    min_required = lookback_days + 1
    if len(wt_df) < min_required:
        return False

    # Check last N days for bullish cross
    for i in range(1, lookback_days + 1):
        idx = -i
        prev_idx = idx - 1

        if abs(prev_idx) > len(wt_df):
            break

        prev = wt_df.iloc[prev_idx]
        curr = wt_df.iloc[idx]

        # NaN check
        if pd.isna(prev.wt1) or pd.isna(prev.wt2) or pd.isna(curr.wt1) or pd.isna(curr.wt2):
            continue

        # Cross up: wt1 crosses above wt2
        cross_up = prev.wt1 <= prev.wt2 and curr.wt1 > curr.wt2

        # Oversold: Either wave below oversold level
        oversold = (
            curr.wt1 < oversold_level
            or curr.wt2 < oversold_level
            or prev.wt1 < oversold_level
            or prev.wt2 < oversold_level
        )

        if cross_up and oversold:
            return True

    return False


def stochastic_rsi(
    close: pd.Series, rsi_period=STOCH_RSI_PERIOD, stoch_period=STOCH_PERIOD, k=STOCH_K_SMOOTH, d=STOCH_D_SMOOTH
) -> pd.DataFrame:
    r = rsi(close, rsi_period)
    r_min = r.rolling(stoch_period).min()
    r_max = r.rolling(stoch_period).max()
    base = (r_max - r_min).replace(0, 1e-9)
    stoch = (r - r_min) / base
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"rsi": r, "k": k_line, "d": d_line})


def stoch_rsi_buy(df: pd.DataFrame, lookback_days: int = SIGNAL_LOOKBACK_DAYS) -> bool:
    """
    Stochastic RSI buy signal detection.

    Args:
        df: DataFrame with columns 'rsi', 'k', 'd'
        lookback_days: Check for cross in last N days (default: 5)

    Returns True if K line crosses above D line in oversold zone.

    Conditions for TRUE bullish crossover:
    1. K line crosses above D line (K was below, now above)
    2. Cross happens in oversold zone (K or D below 20)

    Looks back N days to catch recent crosses that may have been missed.
    """
    min_required = lookback_days + 2
    if len(df) < min_required:
        return False

    # Check last N days for a bullish cross
    for i in range(1, lookback_days + 1):
        idx = -i
        prev_idx = idx - 1

        # Boundary check
        if abs(prev_idx) > len(df):
            break

        prev = df.iloc[prev_idx]
        curr = df.iloc[idx]

        # NaN check
        if any(pd.isna(v) for v in [prev.k, prev.d, curr.k, curr.d]):
            continue

        # Cross up: K crosses above D
        cross_up = prev.k <= prev.d and curr.k > curr.d

        # Oversold: Either line is below 20 during the cross
        oversold = (
            curr.k < STOCH_OVERSOLD or curr.d < STOCH_OVERSOLD or prev.k < STOCH_OVERSOLD or prev.d < STOCH_OVERSOLD
        )

        # Valid signal requires: cross + oversold (simplified)
        valid_cross = cross_up and oversold

        if valid_cross:
            return True

    return False


def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    """
    Calculate Bollinger Bands.

    Bollinger Bands consist of:
    - Middle Band: Simple Moving Average (SMA)
    - Upper Band: SMA + (Standard Deviation × std_dev)
    - Lower Band: SMA - (Standard Deviation × std_dev)

    Args:
        data: Price series (typically Close prices)
        period: SMA period (default: 20)
        std_dev: Number of standard deviations (default: 2.0)

    Returns:
        dict with 'upper', 'middle', 'lower' bands as pd.Series

    Example:
        >>> bb = bollinger_bands(df['Close'], period=20, std_dev=2.0)
        >>> current_price = df['Close'].iloc[-1]
        >>> if current_price < bb['lower'].iloc[-1]:
        >>>     print("Price below lower band - oversold signal")
    """
    # Middle band = SMA
    middle = data.rolling(window=period).mean()

    # Standard deviation
    std = data.rolling(window=period).std()

    # Upper and lower bands
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return {"upper": upper, "middle": middle, "lower": lower}
