import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
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


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
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
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    
    # Money Flow = Typical Price * Volume
    money_flow = typical_price * df['Volume']
    
    # Positive/Negative Money Flow
    positive_flow = pd.Series(0.0, index=df.index)
    negative_flow = pd.Series(0.0, index=df.index)
    
    # If typical price increased, it's positive flow
    for i in range(1, len(df)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            positive_flow.iloc[i] = money_flow.iloc[i]
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            negative_flow.iloc[i] = money_flow.iloc[i]
    
    # Sum over period
    positive_mf = positive_flow.rolling(period).sum()
    negative_mf = negative_flow.rolling(period).sum()
    
    # Money Flow Ratio
    mfr = positive_mf / negative_mf.replace(0, 1e-10)
    
    # Money Flow Index
    mfi = 100 - (100 / (1 + mfr))
    
    return mfi


def mfi_uptrend(mfi_series: pd.Series, days: int = 3) -> bool:
    """
    Check if MFI is in uptrend for the last N days
    
    Args:
        mfi_series: Series of MFI values
        days: Number of days to check (default: 3)
    
    Returns:
        True if MFI has been rising for the last N days
    """
    if len(mfi_series) < days + 1:
        return False
    
    # Check last N days for consecutive increases
    for i in range(1, days + 1):
        curr = mfi_series.iloc[-i]
        prev = mfi_series.iloc[-i-1]
        
        if pd.isna(curr) or pd.isna(prev):
            return False
        
        # MFI must be rising
        if curr <= prev:
            return False
    
    return True


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
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    
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


def wavetrend_buy(wt_df: pd.DataFrame, lookback_days: int = 5, 
                  oversold_level: int = -53) -> bool:
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
        oversold = (curr.wt1 < oversold_level or curr.wt2 < oversold_level or
                   prev.wt1 < oversold_level or prev.wt2 < oversold_level)
        
        if cross_up and oversold:
            return True
    
    return False


def stochastic_rsi(close: pd.Series, rsi_period=14, stoch_period=14, k=3, d=3) -> pd.DataFrame:
    r = rsi(close, rsi_period)
    r_min = r.rolling(stoch_period).min()
    r_max = r.rolling(stoch_period).max()
    base = (r_max - r_min).replace(0, 1e-9)
    stoch = (r - r_min) / base
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"rsi": r, "k": k_line, "d": d_line})


def stoch_rsi_buy(df: pd.DataFrame, lookback_days: int = 5) -> bool:
    """
    Stochastic RSI buy signal detection.
    
    Args:
        df: DataFrame with columns 'rsi', 'k', 'd'
        lookback_days: Check for cross in last N days (default: 5)
    
    Returns True if K line crosses above D line with sustained bullish momentum.
    
    Conditions for TRUE bullish crossover:
    1. K line crosses above D line (K was below, now above)
    2. Cross happens in oversold zone (K or D below 20)
    3. K has SUSTAINED upward momentum (rising for 2+ days) - prevents dead cat bounces
    4. D is not crashing (stable or rising)
    
    Looks back N days to catch recent crosses that may have been missed.
    """
    # Need at least lookback_days + 2 rows for momentum check
    min_required = lookback_days + 3  # Need 2 days back for momentum
    if len(df) < min_required:
        return False
    
    # Check last N days for a bullish cross
    for i in range(1, lookback_days + 1):
        idx = -i
        prev_idx = idx - 1
        prev_prev_idx = idx - 2  # For 2-day momentum check
        
        # Double check boundary
        if abs(prev_prev_idx) > len(df):
            break
        
        prev_prev = df.iloc[prev_prev_idx]
        prev = df.iloc[prev_idx]
        curr = df.iloc[idx]
        
        # NaN check
        if any(pd.isna(v) for v in [prev_prev.k, prev.k, prev.d, curr.k, curr.d]):
            continue
        
        # Cross up: K crosses above D
        cross_up = prev.k <= prev.d and curr.k > curr.d
        
        # Oversold: Either line is below 20 during the cross
        oversold = (curr.k < 0.2 or curr.d < 0.2 or 
                   prev.k < 0.2 or prev.d < 0.2)
        
        # CRITICAL: Check for SUSTAINED upward momentum (2 consecutive days rising)
        # This prevents false positives from temporary bounces
        k_rising_today = curr.k > prev.k
        k_rising_yesterday = prev.k > prev_prev.k
        sustained_uptrend = k_rising_today and k_rising_yesterday
        
        # D should not be crashing (stable or rising)
        d_not_crashing = curr.d >= prev.d * 0.9  # D not falling more than 10%
        
        # Valid signal requires: cross + oversold + sustained K uptrend + D not crashing
        valid_cross = cross_up and oversold and sustained_uptrend and d_not_crashing
        
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
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }
