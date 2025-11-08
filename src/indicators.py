import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
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


def stoch_rsi_buy(df: pd.DataFrame) -> bool:
    """
    Stochastic RSI buy signal detection.
    
    Returns True if:
    1. K line crosses above D line (bullish cross)
    2. Cross happens in oversold zone (K or D below 20)
    
    Relaxed logic: Cross can happen when both are below 20, or when one is below 20
    """
    if len(df) < 2:
        return False
    
    prev, last = df.iloc[-2], df.iloc[-1]
    
    # NaN check
    if any(pd.isna(v) for v in [prev.k, prev.d, last.k, last.d]):
        return False
    
    # Cross up: K crosses above D
    cross_up = prev.k <= prev.d and last.k > last.d
    
    # Oversold: Either line is below 20, or both were below 20 during cross
    oversold = (last.k < 0.2 or last.d < 0.2 or 
                prev.k < 0.2 or prev.d < 0.2)
    
    return cross_up and oversold
