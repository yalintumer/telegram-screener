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
    if len(df) < 2:
        return False
    prev, last = df.iloc[-2], df.iloc[-1]
    if any(pd.isna(v) for v in [prev.k, prev.d, last.k, last.d]):
        return False
    cross_up = prev.k < prev.d and last.k > last.d
    oversold = last.k < 0.2 or last.d < 0.2
    return cross_up and oversold
