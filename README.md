# 📊 Telegram Stock Screener

> Production-ready automated TradingView symbol screening with Stochastic RSI signals via Telegram

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🎯 What It Does

1. **Capture** → Screenshot TradingView screener, extract symbols via OCR
2. **Scan** → Check Stochastic RSI for buy signals (K crosses D in oversold)
3. **Alert** → Send Telegram notifications for buy signals
4. **Monitor** → Track system health, statistics, and watchlist status
5. **Repeat** → Runs continuously in production (Docker/systemd)

## ✨ Features

- 🎯 **Advanced Technical Analysis**: Stochastic RSI with customizable parameters
- 📸 **Intelligent OCR**: Extracts symbols from TradingView screenshots
- 🔄 **Grace Period System**: Prevents duplicate signals with business-day tracking
- 📊 **Health Monitoring**: Built-in status tracking and statistics
- 🚀 **Production Ready**: Systemd service, Docker support, comprehensive logging
- 🆓 **Free Data**: Uses yfinance (unlimited, no API key needed)
- ⚡ **Adaptive Rate Limiting**: Smart delays based on error patterns
- 🎨 **Beautiful CLI**: Rich terminal UI with progress bars and tables

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

cp config.example.yaml config.yaml
nano config.yaml  # Adjust settings if needed

# Test
python -m src.main add AAPL MSFT GOOGL
python -m src.main list
python -m src.main status

# Deploy as Service
# macOS:
python deploy_macos.py install
python deploy_macos.py start

# Linux:
python deploy_service.py install
python deploy_service.py start
```

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide (systemd, Docker)
- **[API Documentation](docs/)** - Detailed API and configuration docs
- **Commands** - See `python -m src.main --help`

## 🎮 Commands

### Core Commands
```bash
# Capture symbols from TradingView screenshot
python -m src.main capture

# Scan watchlist for buy signals
python -m src.main scan

# Continuous mode (capture once, then scan every hour)
python -m src.main run --interval 3600

# System status and health monitoring
python -m src.main status
```

### Watchlist Management
```bash
# Show watchlist
python -m src.main list

# Add symbols manually
python -m src.main add AAPL MSFT GOOGL

# Remove symbols
python -m src.main remove AAPL MSFT

# Clear all symbols (with confirmation)
python -m src.main clear

# Debug specific symbol
python -m src.main debug AAPL
```

### Advanced Options
```bash
# Dry run (no changes, no messages sent)
python -m src.main scan --dry-run

# Parallel scanning (faster, but careful with rate limits)
python -m src.main scan --parallel

# Custom sleep between symbols
python -m src.main scan --sleep 20

# Click before capture (for window focus)
python -m src.main capture --click 150,50
```

## 🏗️ Architecture

### Signal Detection

**Stochastic RSI:**
```
1. Calculate RSI (14 periods)
2. Stochastic of RSI (14 periods)
3. K line = 3-day SMA of Stochastic
4. D line = 3-day SMA of K
5. Buy signal = K crosses above D when both < 20 (oversold)
```

### Grace Period

After sending a signal, symbol enters **5 business day grace period**:
- Prevents spam alerts
- VM filters grace period symbols before scanning
- Local Mac sends raw symbols (no grace check)

### Architecture

```
Local Mac → GitHub → VM (Ubuntu)
   ↓          ↓          ↓
Capture    Sync     Scan every hour
   ↓          ↓          ↓
OCR        Git      Telegram alerts
```

## 🌐 VM Setup

```bash
# On VM (Ubuntu)
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env

# Install service
sudo cp deploy/telegram-screener.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-screener
sudo systemctl start telegram-screener
```

**Service runs:** `run_scan_only.sh` → scans every 3600 seconds

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
