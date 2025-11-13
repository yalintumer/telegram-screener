# 📊 Telegram Stock Screener

> Automated TradingView symbol screening with Stochastic RSI signals via Telegram

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-46%20passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-89--95%25-green.svg)](htmlcov/)

---

## 🎯 What It Does

1. **Capture** → Screenshot TradingView screener, extract symbols via OCR
2. **Scan** → Check Stochastic RSI for buy signals (K crosses D in oversold)
3. **Alert** → Send Telegram notifications for buy signals
4. **Repeat** → Runs every hour on cloud VM

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

# Test
python -m src.main --config config.yaml list
python -m src.main --config config.yaml scan --dry-run
```

## 🛠️ Commands (via aliases)

Add to `~/.zshrc`:
```bash
source ~/.zshrc  # Reload after adding aliases
```

**Local:**
- `tvlist` - Show watchlist
- `tvadd AAPL MSFT` - Add symbols
- `tvscan` - Scan for signals
- `tvcapture` - Screenshot + OCR
- `tvrun` - Continuous mode

**VM:**
- `tvstatus` - Check VM service
- `tvlogs` - View logs
- `tvrestart` - Restart service
- `tvsync` - Sync local → VM

**Utilities:**
- `tvhealth` - System health check
- `tvcompare` - Compare local vs VM
- `tvhelp` - Show all commands

## 📖 How It Works

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
