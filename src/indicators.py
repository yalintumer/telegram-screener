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


def stochastic_rsi(close: pd.Series, rsi_period=14, stoch_period=14, k=3, d=3) -> pd.DataFrame:
    r = rsi(close, rsi_period)
    r_min = r.rolling(stoch_period).min()
    r_max = r.rolling(stoch_period).max()
    base = (r_max - r_min).replace(0, 1e-9)
    stoch = (r - r_min) / base
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"rsi": r, "k": k_line, "d": d_line})


def stoch_rsi_buy(df: pd.DataFrame, lookback_days: int = 3) -> bool:
    """
    Stochastic RSI buy signal detection.
    
    Args:
        df: DataFrame with columns 'rsi', 'k', 'd'
        lookback_days: Check for cross in last N days (default: 3)
    
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
