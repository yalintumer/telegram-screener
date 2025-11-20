# 📊 Telegram Stock Screener

> Production-ready automated stock screening with **two-stage filtering system**: Stochastic RSI + MFI → WaveTrend confirmation

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 What It Does

**Two-Stage Filtering System for High-Confidence Buy Signals:**

### Stage 1: Initial Filter (Momentum + Volume)
- **Stochastic RSI**: Detects oversold crossovers with sustained 2-day momentum
- **MFI (Money Flow Index)**: Confirms 3-day volume-weighted uptrend
- → Signals move to **Signals Database**

### Stage 2: Confirmation Filter (Trend Reversal)
- **WaveTrend (LazyBear)**: Validates oversold zone cross (WT1 > WT2)
- → Confirmed signals move to **Buy Database**
- → Sends eye-catching Telegram notification 🚨

**Result**: Only high-probability signals with dual confirmation reach you!

## ✨ Features

- 🎯 **Three Advanced Indicators**: 
  - Stochastic RSI (14/14/3/3) with false positive prevention
  - Money Flow Index (MFI) - volume-weighted momentum
  - WaveTrend oscillator (LazyBear's algorithm)
- 🔄 **Hierarchical Filtering**: Two-stage confirmation system
- 📊 **Notion Integration**: 3 databases (Watchlist → Signals → Buy)
- 🚀 **Production Ready**: 35/35 tests passing, comprehensive error handling
- 🆓 **Free Data**: Uses yfinance (unlimited, no API key needed)
- ⚡ **Smart Duplicate Prevention**: No repeated processing across databases
- 📱 **Enhanced Telegram Alerts**: Rich formatted notifications with indicator values
- 🎨 **Beautiful CLI**: Rich terminal UI with progress bars

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
nano config.yaml  # Add your Notion API tokens and database IDs

# Test
python -m src.main --once  # Run both stages once
python -m pytest tests/ -v # Run test suite (35 tests)

# Deploy as Service
# macOS:
python deploy_macos.py install
python deploy_macos.py start

# Linux:
python deploy_service.py install
python deploy_service.py start
```

## 🧪 Testing

Comprehensive test suite with 100% pass rate:

```bash
# Run all tests
python -m pytest tests/ -v

# Test categories:
pytest tests/test_indicators.py      # Indicator calculations (21 tests)
pytest tests/test_error_handling.py  # Error handling (14 tests)
```

**Test Coverage:**
- ✅ All 3 indicators validated against PineScript references
- ✅ Edge cases (empty data, NaN, network failures)
- ✅ Error handling for all external APIs
- ✅ Config validation
- ✅ End-to-end integration tests

## 🎮 Commands

### Core Commands
```bash
# Run both scanning stages once (for testing)
python -m src.main --once

# Continuous mode (scans every hour by default)
python -m src.main --interval 3600

# Run test suite
python -m pytest tests/ -v
```

## 🏗️ Architecture

### Two-Stage Filtering System

**Stage 1: Momentum + Volume Filter**
```
Watchlist → Stochastic RSI + MFI → Signals Database

Conditions:
1. Stochastic RSI (14/14/3/3):
   - K crosses above D in oversold zone (< 20%)
   - K shows sustained 2-day uptrend (prevents false positives)
   
2. Money Flow Index (14-period):
   - 3 consecutive days of rising MFI
   - Volume-weighted momentum confirmation
```

**Stage 2: Trend Reversal Confirmation**
```
Signals Database → WaveTrend → Buy Database

Conditions:
1. WaveTrend (LazyBear, 10/21):
   - WT1 crosses above WT2
   - Cross occurs in oversold zone (< -53)
   - Final confirmation of trend reversal

Result: Symbol deleted from Signals, added to Buy + Telegram alert 🚨
```

### System Flow

```
┌─────────────┐
│  Watchlist  │  (Notion Database 1)
│  Database   │
└──────┬──────┘
       │ Stage 1: Stoch RSI + MFI
       ↓
┌─────────────┐
│   Signals   │  (Notion Database 2)
│  Database   │
└──────┬──────┘
       │ Stage 2: WaveTrend
       ↓
┌─────────────┐
│     Buy     │  (Notion Database 3)
│  Database   │  + Telegram Alert 📱
└─────────────┘
```

### Duplicate Prevention

- Stage 1 skips symbols already in Signals or Buy
- Stage 2 skips symbols already in Buy
- No duplicate processing or notifications
- Efficient API usage

## 📂 Project Structure

```
telegram-screener/
├── src/
│   ├── main.py              # CLI entry point
│   ├── watchlist.py         # Watchlist & grace period
│   ├── indicators.py        # Stochastic RSI
│   ├── telegram_client.py   # Telegram API
│   ├── ui.py                # Rich UI components
│   ├── rate_limiter.py      # Adaptive delays
│   └── ...
├── tests/                   # 46 unit tests
├── deploy/                  # VM setup scripts
├── tvhealth.py              # Health check
├── run_scan_only.sh         # VM scan loop
├── watchlist.json           # Active symbols
├── signal_history.json      # Grace period tracking
├── config.yaml              # Config (gitignored)
└── README.md
```

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## 🔧 Configuration

Create `config.yaml`:
```yaml
api:
  provider: "yfinance"

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"

data:
  max_watch_days: 5

logging:
  level: "INFO"
  file: "logs/screener.log"
```

Or use `.env`:
```bash
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

## 🔐 Security

- ✅ `.env` and `config.yaml` in `.gitignore`
- ✅ Never commit API keys
- ⚠️ If leaked: revoke tokens immediately (@BotFather)

## 📊 Example Output

```
╭────────────────────────────────────╮
│         📋 Watchlist               │
│           3 symbols                │
╰────────────────────────────────────╯

┏━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃    # ┃ Symbol ┃ Added    ┃   Days ┃
┡━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│    1 │ AAPL   │ 2025-... │     0d │
│    2 │ MSFT   │ 2025-... │     2d │
│    3 │ GOOGL  │ 2025-... │     5d │
└──────┴────────┴──────────┴────────┘
```

## 🔧 Troubleshooting

**VM out of sync?**
```bash
ssh root@YOUR_VM "cd ~/telegram-screener && git reset --hard origin/main"
tvrestart
```

**Grace period not working?**
```bash
tvhealth  # Check signal_history.json
```

**Service not running?**
```bash
tvlogs  # Check errors
tvrestart
```

## 📚 Documentation

- **Full Docs:** `docs/archived/` (detailed guides)
- **Cheatsheet:** `CHEATSHEET.txt` (quick reference)
- **Security:** `SECURITY.md` (best practices)
- **Deployment:** `deploy/README.md` (VM setup)

## 🤝 Contributing

```bash
# Setup
pip install pytest pytest-cov black mypy

# Test
pytest tests/ -v

# Format
black src/ tests/

# Type check
mypy src/
```

## 📄 License

MIT License - See LICENSE file

---

**Built with:** [Rich](https://rich.readthedocs.io/), [yfinance](https://github.com/ranaroussi/yfinance), [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

**Note:** Educational purposes only. Not financial advice.
