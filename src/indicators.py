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
    
    Returns True if K line crosses above D line in oversold zone within last N days.
    
    Conditions:
    1. K line crosses above D line (bullish cross)
    2. Cross happens in oversold zone (K or D below 20)
    
    Looks back N days to catch recent crosses that may have been missed.
    """
    # Need at least lookback_days + 1 rows for current + previous comparisons
    # For lookback_days=3, we need idx=-3,-2,-1 and prev_idx=-4,-3,-2
    # So minimum required: lookback_days + 2
    min_required = lookback_days + 2
    if len(df) < min_required:
        return False
    
    # Check last N days for a bullish cross
    for i in range(1, lookback_days + 1):
        idx = -i
        prev_idx = idx - 1
        
        # Double check boundary (should be safe now)
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
        oversold = (curr.k < 0.2 or curr.d < 0.2 or 
                   prev.k < 0.2 or prev.d < 0.2)
        
        if cross_up and oversold:
            return True
    
    return False
