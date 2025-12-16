# 📊 Telegram Stock Screener

> Automated S&P 500 screening with **two-stage confirmation**: Market Filter → WaveTrend

![CI](https://github.com/yalintumer/telegram-screener/actions/workflows/ci.yml/badge.svg)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-32%25-yellow.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What It Does

Two-stage filter system for high-confidence buy signals:

### Stage 1: Market Scanner
Scans S&P 500 daily for oversold setups:

| Filter | Threshold | Purpose |
|--------|-----------|---------|
| Market Cap | ≥ $50B | Large-cap only |
| Stoch RSI (3,3,14,14) | D < 20 | Oversold |
| Bollinger Bands | Price < Lower | Statistical extreme |
| MFI (14) | ≤ 40 | Weak money flow |
| MFI Trend | 3-day uptrend | Accumulation starting |

→ Adds to **Signals Database** (Notion)

### Stage 2: WaveTrend Confirmation
Checks signals hourly for trend reversal:

| Filter | Threshold | Purpose |
|--------|-----------|---------|
| WaveTrend | WT1 crosses WT2 | Momentum shift |
| Oversold zone | < -53 | Not FOMO buying |
| Weekly WT1 | < 60 | Not weekly overbought |

→ Moves to **Buy Database** + Telegram alert 🚨

---

## 🚀 Quick Start

```bash
# Clone & setup
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure (see Configuration section)
cp config.example.yaml config.yaml
nano config.yaml

# Run once
python -m src.main --once

# Run continuous (every hour)
python -m src.main

# Run tests
pytest
```

---

## ⚙️ Configuration

### Required: config.yaml

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"     # From @BotFather
  chat_id: "YOUR_CHAT_ID"         # Your Telegram user/group ID

notion:
  api_token: "secret_xxx"         # Notion integration token
  signals_database_id: "xxx"      # Stage 1 signals
  buy_database_id: "xxx"          # Confirmed buys

api:
  provider: "yfinance"            # Free, no key needed
```

### Optional: Environment Variables

For production, use env vars instead of config.yaml:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export NOTION_API_TOKEN="..."
export NOTION_SIGNALS_DATABASE_ID="..."
export NOTION_BUY_DATABASE_ID="..."
```

---

## 📱 Commands

```bash
# Full scan (both stages)
python -m src.main --once

# Stage 1 only (market scanner)
python -m src.main --market-scan

# Stage 2 only (WaveTrend check)
python -m src.main --wavetrend

# Continuous mode (hourly)
python -m src.main --interval 3600

# Custom interval (30 min)
python -m src.main --interval 1800
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    S&P 500 (500 symbols)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Market Filter (Daily)                              │
│  • Market Cap ≥ $50B                                        │
│  • Stoch RSI D < 20                                         │
│  • Price < BB Lower                                         │
│  • MFI ≤ 40 + 3-day uptrend                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Signals DB     │  (Notion)
                    │  ~5-10 symbols  │
                    └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: WaveTrend Confirmation (Hourly)                   │
│  • WT1 crosses WT2 in oversold (<-53)                      │
│  • Weekly WT1 not overbought (<60)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Buy DB        │  (Notion)
                    │   + Telegram    │  🚨
                    └─────────────────┘
```

---

## 🧪 Testing

```bash
# All tests (121 tests)
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test file
pytest tests/test_indicators.py -v

# Fast (parallel)
pytest -n auto
```

| Module | Coverage | Status |
|--------|----------|--------|
| indicators.py | 93% | ✅ |
| rate_limiter.py | 98% | ✅ |
| retry.py | 97% | ✅ |
| health.py | 96% | ✅ |
| config.py | 90% | ✅ |
| **Total** | **32%** | 🔄 |

---

## 🚀 Deployment

### Option 1: systemd (Linux VM)

```bash
# Install as service
python deploy_service.py install
python deploy_service.py start

# View logs
journalctl -u telegram-screener -f

# Status
systemctl status telegram-screener
```

### Option 2: launchd (macOS)

```bash
python deploy_macos.py install
python deploy_macos.py start
```

### Option 3: Docker

```bash
docker-compose up -d
```

---

## 📊 Monitoring

### Health Check

```bash
cat health.json
# {
#   "status": "healthy",
#   "scan_count": 42,
#   "last_scan": {...}
# }
```

### Logs

```bash
# Structured JSON logs
tail -f logs/screener.log | jq .

# Filter by level
grep '"level":"ERROR"' logs/screener.log
```

### Sentry (Optional)

```bash
export SENTRY_DSN="https://xxx@sentry.io/xxx"
```

---

## 📁 Project Structure

```
telegram-screener/
├── src/
│   ├── main.py              # Entry point, CLI
│   ├── config.py            # Pydantic config loading
│   ├── indicators.py        # Technical indicators
│   ├── notion_client.py     # Notion API wrapper
│   ├── telegram_client.py   # Telegram messaging
│   ├── data_source_yfinance.py
│   ├── rate_limiter.py      # API rate limiting
│   ├── retry.py             # Exponential backoff
│   ├── health.py            # Health checks
│   └── ...
├── tests/                   # 121 tests
├── docs/
│   ├── adr/                 # Architecture decisions
│   ├── TEST_STRATEGY.md
│   └── CI_GUIDE.md
├── .github/workflows/       # CI/CD
└── config.example.yaml
```

---

## 🔧 Troubleshooting

### "Rate limit exceeded"
```
[WARNING] rate_limit.waiting service=yfinance wait_seconds=45.2
```
→ Normal, rate limiter is working. Will auto-resume.

### "Notion 401 Unauthorized"
→ Check `NOTION_API_TOKEN` env var or config.yaml

### "No signals found"
→ Market conditions may not match filters. Check Stage 1 criteria.

---

## 📚 Documentation

- [Test Strategy](docs/TEST_STRATEGY.md)
- [CI/CD Guide](docs/CI_GUIDE.md)
- [Refactoring Plan](docs/REFACTORING_PLAN.md)
- [Security Setup](docs/SECURITY_SETUP.md)
- [ADRs](docs/adr/) - Architecture Decision Records

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/amazing`
3. Run tests: `pytest`
4. Run lint: `ruff check src/`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing`
7. Open PR

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## ⚠️ Disclaimer

This software is for educational purposes only. Not financial advice. 
Always do your own research before trading.
