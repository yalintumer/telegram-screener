# ADR-003: yfinance as Primary Data Source

**Status:** Accepted  
**Date:** 2025-12-16  
**Decision Makers:** yalintumer

## Context

OHLCV (Open, High, Low, Close, Volume) data çekmek için API seçimi.

Değerlendirilen seçenekler:
1. yfinance (Yahoo Finance wrapper)
2. Alpha Vantage API
3. Polygon.io
4. IEX Cloud
5. Tiingo

## Decision

**yfinance** primary data source olarak seçildi.  
**Alpha Vantage** optional backup olarak tutuldu.

## Rationale

### Comparison Matrix

| Criteria | yfinance | Alpha Vantage | Polygon | IEX Cloud |
|----------|----------|---------------|---------|-----------|
| Cost | ✅ Free | ⚠️ 5 req/min | ❌ $99/mo | ❌ $9/mo |
| Rate limit | ✅ ~2000/hour | ❌ 5/min | ✅ Unlimited | ✅ 500k/mo |
| Data quality | ⚠️ Good | ✅ Excellent | ✅ Excellent | ✅ Excellent |
| Setup | ✅ pip install | ⚠️ API key | ⚠️ API key | ⚠️ API key |
| Reliability | ⚠️ Yahoo-dependent | ✅ Enterprise | ✅ Enterprise | ✅ Enterprise |

### Why yfinance?

1. **Zero cost**: S&P 500 taraması için önemli (500 symbol × multiple calls)
2. **No API key**: Secrets management yok
3. **Good enough**: Daily data accuracy yeterli
4. **Popular**: Community support, issues quickly fixed

### Tradeoffs Accepted

| Issue | Mitigation |
|-------|------------|
| Yahoo blocks aggressive scraping | rate_limiter.py: 60/min |
| Occasional data gaps | Retry logic, fallback to Alpha Vantage |
| Market cap sometimes stale | 24h cache acceptable |
| No guaranteed SLA | Alerts on failure, not critical path |

## Implementation Details

```python
# data_source_yfinance.py
def daily_ohlc(symbol: str, days: int = 100) -> pd.DataFrame:
    rate_limit("yfinance")  # 60/min max
    ticker = yf.Ticker(symbol)
    df = ticker.history(...)
    return df
```

### Alpha Vantage as Backup

```python
# data_source_alpha_vantage.py
# Used when ALPHA_VANTAGE_KEY env var set
# Provides more accurate indicator values
# Rate limited: 5/min (free tier)
```

## Consequences

### Positive
- No monthly costs
- Simple deployment (no API key management)
- Fast development iteration

### Negative
- Yahoo can change/break API (has happened before)
- No official support
- Data quality not guaranteed

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Yahoo blocks IP | Low | High | Use Alpha Vantage fallback |
| Data accuracy issue | Medium | Medium | Multi-source validation |
| Rate limiting | Low | Low | rate_limiter.py |

## Alternatives Rejected

### Alpha Vantage (Primary)
- ❌ 5 req/min too slow for 500 symbols
- ❌ Would need paid plan ($49.99/mo)

### Polygon.io
- ❌ $99/mo minimum
- ✅ Excellent data quality
- Would consider if monetizing

### IEX Cloud
- ❌ Pay per message pricing complex
- ✅ Good documentation

## Future Considerations

1. **Data quality monitoring**: Track discrepancies
2. **Multiple source validation**: Compare yfinance vs Alpha Vantage
3. **Paid upgrade**: If product monetized, consider Polygon

## References

- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [Alpha Vantage Pricing](https://www.alphavantage.co/premium/)
