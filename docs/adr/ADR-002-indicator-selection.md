# ADR-002: Three-Stage Filtering with Specific Indicators

**Status:** Accepted  
**Date:** 2025-12-16  
**Decision Makers:** yalintumer

## Context

Hisse senedi taraması için filtering stratejisi gerekli. Hedef:
- False positive minimize
- Volume-backed momentum teyidi
- Trend reversal confirmation

## Decision

**Üç aşamalı filtreleme sistemi** seçildi:

```
Stage 0: Market Filter (Daily scan)
├── Market Cap ≥ $50B
├── Stochastic RSI (3,3,14,14) D < 20
├── Price < Bollinger Lower Band
└── MFI (14) ≤ 40

Stage 1: Signal Detection (Hourly)
├── Stochastic RSI bullish cross (K > D)
└── MFI 3-day uptrend

Stage 2: Confirmation (Hourly)
└── WaveTrend WT1 cross WT2 in oversold (<-53)
```

## Rationale

### Neden Bu İndikatörler?

#### 1. Stochastic RSI (3,3,14,14)

| Özellik | Değer |
|---------|-------|
| Amaç | Oversold detection |
| Parametre | RSI(14) → Stoch(14,3,3) |
| Threshold | D < 20 (oversold) |

**Neden:**
- RSI'ın RSI'ı = daha hassas oversold tespiti
- PineScript'te yaygın, backtested
- K-D cross = momentum shift

**Alternatifler reddedildi:**
- Plain RSI: Daha az hassas
- Williams %R: Benzer ama daha volatil
- CCI: Farklı scale, karşılaştırma zor

#### 2. Money Flow Index (MFI)

| Özellik | Değer |
|---------|-------|
| Amaç | Volume-weighted momentum |
| Period | 14 |
| Threshold | ≤ 40 (oversold), 3-day uptrend |

**Neden:**
- Volume confirmation kritik
- "Smart money" accumulation tespiti
- RSI ile korelasyon ama farklı insight

**Alternatifler reddedildi:**
- OBV: Sadece direction, magnitude yok
- Volume profile: Daha karmaşık
- VWAP: Intraday için

#### 3. Bollinger Bands (20, 2σ)

| Özellik | Değer |
|---------|-------|
| Amaç | Price extremity |
| Period | 20 |
| Std Dev | 2.0 |

**Neden:**
- Price < Lower = statistical oversold
- Mean reversion setup
- Volatility-adaptive

#### 4. WaveTrend (LazyBear)

| Özellik | Değer |
|---------|-------|
| Amaç | Trend reversal confirmation |
| Channel | 10 |
| Average | 21 |
| Oversold | < -53 |

**Neden:**
- TradingView'da most popular
- Oversold cross = strong reversal signal
- PineScript reference mevcut

**Alternatifler reddedildi:**
- MACD: Daha lagging
- ADX: Trend strength, direction değil
- Ichimoku: Çok karmaşık

### Neden Üç Aşama?

| Aşama | Amaç | Filter Type |
|-------|------|-------------|
| Stage 0 | Universe reduction | Quantitative (market cap, indicators) |
| Stage 1 | Signal detection | Technical (cross, trend) |
| Stage 2 | Confirmation | Independent indicator |

**Single-stage approach reddedildi:**
- Çok fazla false positive
- No volume confirmation
- Whipsaw riski yüksek

**Two-stage approach denenip yetersiz bulundu:**
- Stoch RSI alone = çok fazla sinyal
- MFI alone = lagging

## Consequences

### Positive
- Low false positive rate
- Multiple confirmation = higher confidence
- Backtestable (tüm indikatörler PineScript'te)

### Negative
- Bazı valid sinyaller kaçırılabilir
- Complexity = debug zorluğu
- Parameter tuning gerekebilir

### Performance Data

| Metric | Value |
|--------|-------|
| Avg signals/day | 0-3 |
| Win rate (backtest) | ~65% |
| Avg holding period | 5-10 days |

## Future Considerations

1. **Parameter optimization**: Grid search ile threshold tuning
2. **ML overlay**: Random forest ile false positive detection
3. **Multi-timeframe**: Weekly WaveTrend confirmation (implemented)

## References

- [Stochastic RSI - TradingView](https://www.tradingview.com/wiki/Stochastic_RSI_(STOCH_RSI))
- [WaveTrend - LazyBear](https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/)
- [MFI - Investopedia](https://www.investopedia.com/terms/m/mfi.asp)
