# 📊 Telegram Stock Screener

> **Automated stock screening with Stochastic RSI signals sent to Telegram**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-46%20passed-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-89--95%25-green.svg)](htmlcov/)

**What it does:**
1. 📸 Captures TradingView screenshots (OCR) → extracts symbols
2. 📊 Scans using Stochastic RSI indicator
3. 🚀 Sends buy signals to Telegram
4. 🌐 Runs 24/7 on cloud VM (Ubuntu)
5. 🎨 Beautiful terminal UI with Rich library

---

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add Telegram bot token and chat ID

# Test
python -m src.main --config config.yaml list
```

### 3. Test
```bash
# View watchlist (beautiful table)
python -m src.main --config config.yaml list

# Scan for signals (dry-run)
python -m src.main --config config.yaml scan --dry-run

# Add symbols manually
python -m src.main --config config.yaml add AAPL MSFT GOOGL
```

---

## 📋 Features

### 🎨 **Beautiful Terminal UI**
- ✅ Color-coded tables with age indicators
- ✅ Progress bars with spinners and ETA
- ✅ Bordered panels and styled headers
- ✅ Rich error messages and warnings

### 📊 **Smart Screening**
- ✅ Stochastic RSI buy signal detection
- ✅ Grace period (5 business days) prevents spam
- ✅ Adaptive rate limiting (0.5s - 5s)
- ✅ Parallel scanning (optional, 3 workers)
- ✅ Automatic symbol pruning (5 business days)

### 🌐 **Cloud VM Integration**
- ✅ Systemd service (auto-restart)
- ✅ Hourly scans (24/7 monitoring)
- ✅ Git-based deployment
- ✅ SSH automation

### 🧪 **Testing & Quality**
- ✅ 46 unit tests (all passing)
- ✅ 89-95% code coverage
- ✅ Type hints throughout
- ✅ Input validation & error handling

---

## 🛠️ CLI Commands (TV Aliases)

All commands available via simple `tv*` aliases:

### 📊 **Watchlist Management**
```bash
tvlist                    # Show watchlist (beautiful table)
tvadd AAPL MSFT          # Add symbols
tvremove AAPL            # Remove symbols
tvclear                  # Clear entire watchlist
tvcapture                # Screenshot + OCR + sync
```

### 🔍 **Scanning & Analysis**
```bash
tvscan                   # Scan for signals (with progress bar)
tvdebug AAPL            # Debug single symbol
tvrun                    # Continuous mode (capture + scan loop)
```

### 🌐 **VM Management**
```bash
tvm                      # SSH to VM
tvstatus                 # Service status
tvlogs                   # Last 50 log lines
tvlogs-live             # Live log stream (Ctrl+C to exit)
tvstart                  # Start service
tvstop                   # Stop service
tvrestart               # Restart service
```

### 🔄 **Sync & Git**
```bash
tvsync                   # Full sync (pull + push + VM restart)
tvpush                   # Commit + push + VM update
tvpull                   # Git pull
tvcompare               # Compare local vs VM watchlist
```

### 🔧 **Utilities**
```bash
tvhealth                # System health check
tvcd                    # Change to project directory
tvhelp                  # Show all commands
```

---

## 📖 How It Works

### 🎯 **Architecture**

```
┌─────────────┐     Git Push      ┌──────────────┐
│  Local Mac  │ ──────────────────> │   GitHub     │
│             │                     │              │
│ - Screenshot│                     │ Repository   │
│ - OCR       │                     └──────┬───────┘
│ - UI        │                            │
└─────────────┘                            │ Git Pull
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  VM (Ubuntu) │
                                    │              │
                                    │ - Scan every │
                                    │   1 hour     │
                                    │ - Send alerts│
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  Telegram    │
                                    │  🚀 Signals  │
                                    └──────────────┘
```

### 🔍 **Signal Detection Logic**

**Stochastic RSI Buy Signal:**
1. Calculate RSI (14 periods)
2. Calculate Stochastic of RSI (14 periods)
3. K line = 3-day SMA of Stochastic
4. D line = 3-day SMA of K line
5. **Signal = K crosses above D in oversold zone (< 20)**

**Example:**
```
Stoch RSI
100 |                    
 80 |                    
 60 |                    
 40 |              D ----
 20 |        K ---/      ← K crosses D (BUY SIGNAL! 🚀)
  0 |___________/________
     Day: -3  -2  -1  0
```

### ⏰ **Grace Period System**

**Problem:** Same symbol keeps triggering signals

**Solution:** After sending signal, symbol goes into "grace period" for **5 business days**

**How it works:**
```
Monday    → AAPL signal sent 🚀
            AAPL removed from watchlist
            signal_history.json: {"AAPL": {"last_signal": "2025-11-13"}}

Tuesday   → User captures AAPL again from TradingView
            Local: Added to watchlist (no check)
            VM: Filters out AAPL (grace period active - 4 days left)

...

Next Monday → Grace period expired (5 business days)
              AAPL can be scanned and signaled again
```

**Key Points:**
- ✅ Grace period uses **business days** (weekends don't count)
- ✅ Filtering happens **on VM** before scanning
- ✅ Local Mac just sends raw tickers (no grace check)
- ✅ Signal history stored in `signal_history.json`

---

## 📂 Project Structure

```
telegram-screener/
├── src/                          # Main source code
│   ├── main.py                   # CLI commands (cmd_scan, cmd_capture, etc.)
│   ├── watchlist.py              # Watchlist & grace period logic
│   ├── indicators.py             # Stochastic RSI calculations
│   ├── telegram_client.py        # Telegram API wrapper
│   ├── rate_limiter.py           # Adaptive rate limiting
│   ├── ui.py                     # Rich UI components (NEW!)
│   ├── validation.py             # Input validation
│   ├── config.py                 # Pydantic config models
│   ├── logger.py                 # Structured logging
│   ├── capture.py                # Screenshot capture (Mac only)
│   ├── ocr.py                    # Tesseract OCR
│   └── data_source_yfinance.py   # yfinance data fetcher
│
├── tests/                        # Unit tests (46 tests)
│   ├── test_indicators.py
│   ├── test_rate_limiter.py
│   └── test_validation.py
│
├── deploy/                       # VM deployment scripts
│   ├── deploy.sh
│   ├── oracle_setup.sh
│   └── quick_install.sh
│
├── watchlist.json                # Active watchlist
├── signal_history.json           # Signal tracking
├── config.yaml                   # Configuration
├── requirements.txt              # Python dependencies
├── tvhealth.py                   # Health check script
└── README.md                     # This file
```

---

## ⚙️ Configuration

### `config.yaml` Structure

```yaml
api:
  provider: "yfinance"           # Data source (yfinance or alphavantage)
  alpha_vantage_key: ""          # Optional: AlphaVantage key

telegram:
  bot_token: "YOUR_BOT_TOKEN"    # From @BotFather
  chat_id: "YOUR_CHAT_ID"        # Your Telegram chat ID

data:
  max_watch_days: 5              # Auto-remove after 5 business days

screen:
  region: [0, 200, 165, 645]     # Screenshot region (Mac)
  app_name: "TradingView"        # App to focus

tesseract:
  path: "/opt/homebrew/bin/tesseract"  # Tesseract binary
  lang: "eng"                    # OCR language
  config_str: "--psm 6"          # Tesseract config

logging:
  level: "INFO"                  # DEBUG, INFO, WARNING, ERROR
  file: "logs/screener.log"      # Log file path
```

---

## 🎨 UI Examples

### Beautiful Watchlist Table
```
╭────────────────────────────────────────────────────────────╮
│                                                            │
│                       📋 Watchlist                         │
│                         3 symbols                          │
│                                                            │
╰────────────────────────────────────────────────────────────╯
                  📋 Watchlist                   
┏━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃    # ┃ Symbol     ┃ Added Date   ┃   Days Ago ┃
┡━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│    1 │ AAPL       │ 2025-11-13   │         0d │  ← Green (fresh)
├──────┼────────────┼──────────────┼────────────┤
│    2 │ MSFT       │ 2025-11-11   │         2d │  ← Yellow (mid)
├──────┼────────────┼──────────────┼────────────┤
│    3 │ GOOGL      │ 2025-11-08   │         5d │  ← Red (old)
└──────┴────────────┴──────────────┴────────────┘
```

### Scan Progress with Stats
```
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│                    🔍 Signal Scanner                        │
│              Scanning 10 symbols for buy signals           │
│                                                             │
╰─────────────────────────────────────────────────────────────╯

ℹ  Sequential mode (delay: 15s between symbols)

Scanning (delay: 1.2s)... ━━━━━━━╸━━━━━━━━━━ 40% 0:00:12

╭─ 📊 Statistics ──────────────────────────────────────────╮
│                                                          │
│  Current Delay: 1.20s                                    │
│  Success Streak: 8                                       │
│  Total Errors: 1                                         │
│                                                          │
╰──────────────────────────────────────────────────────────╯

✓ Scan complete! Found 2 buy signal(s)
  🚀 AAPL
  🚀 TSLA
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### With Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Results
```
46 tests passed ✅
Coverage:
  - indicators.py:   94%
  - rate_limiter.py: 89%
  - validation.py:   95%
```

---

## 🌐 VM Deployment

### Automatic Setup (Recommended)
```bash
# On your Mac
cd deploy/
./quick_install.sh
```

This will:
1. Create Ubuntu VM (DigitalOcean/Oracle)
2. Install Python 3.13 + dependencies
3. Setup systemd service
4. Configure auto-start
5. Setup SSH keys

### Manual Deployment
```bash
# 1. SSH to VM
ssh root@YOUR_VM_IP

# 2. Clone repo
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener

# 3. Setup Python
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp config.yaml.example config.yaml
nano config.yaml

# 5. Create systemd service
sudo nano /etc/systemd/system/telegram-screener.service
```

**Service File (`/etc/systemd/system/telegram-screener.service`):**
```ini
[Unit]
Description=Telegram Stock Screener Bot (Scan Only)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-screener
ExecStart=/root/telegram-screener/run_scan_only.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Run Script (`run_scan_only.sh`):**
```bash
#!/bin/bash
set -e

cd "$(dirname "$0")"
source venv/bin/activate

while true; do
    echo "🔍 Starting scan cycle at $(date)"
    python -m src.main --config config.yaml scan
    
    echo "⏳ Waiting 3600 seconds (1 hour) before next scan..."
    sleep 3600
done
```

**Enable and Start:**
```bash
chmod +x run_scan_only.sh
sudo systemctl daemon-reload
sudo systemctl enable telegram-screener.service
sudo systemctl start telegram-screener.service
sudo systemctl status telegram-screener.service
```

---

## 🔧 Troubleshooting

### Check System Health
```bash
tvhealth
```

**Output:**
```
╭─────────────────────────────────────────╮
│     🏥 System Health Check              │
╰─────────────────────────────────────────╯

📍 Local Status:
   ✅ Watchlist: 3 symbols
   ✅ config.yaml exists
   📊 Signal history: 5 signals

🌐 VM Status:
   ✅ Service: Running
   ✅ VM Watchlist: 3 symbols

📊 Git Status:
   ✅ No uncommitted changes
```

### Common Issues

#### 1. **JSON Parse Error**
```bash
# Error: Illegal trailing comma
# Fix: Remove trailing comma in watchlist.json
tvlist  # Will show error
```

#### 2. **VM Out of Sync**
```bash
# Reset VM to match GitHub
ssh root@YOUR_VM_IP
cd ~/telegram-screener
git reset --hard origin/main
sudo systemctl restart telegram-screener.service
```

#### 3. **Grace Period Not Working**
```bash
# Check signal history
cat signal_history.json

# Force add symbol (skip grace check)
# Note: Local capture already skips grace check
tvcapture
```

#### 4. **Service Not Running**
```bash
# Check logs
tvlogs

# Check status
tvstatus

# Restart
tvrestart
```

#### 5. **API Rate Limiting**
```bash
# Adaptive rate limiter will automatically slow down
# Check current delay in scan progress
tvscan  # Shows "delay: X.Xs" in progress bar
```

---

## 📊 Usage Scenarios

### Scenario 1: Daily Morning Routine
```bash
# 1. Check VM status
tvstatus

# 2. View current watchlist
tvlist

# 3. Capture new symbols from TradingView
tvcapture

# 4. Check for immediate signals (dry-run)
tvscan --dry-run

# 5. Sync to VM
tvsync
```

### Scenario 2: Debug Single Symbol
```bash
# Show last 5 days of data + indicators
tvdebug AAPL

# Example output:
# Last 5 Days:
# Date       | Close  | RSI  | K    | D    | Signal
# 2025-11-13 | 150.25 | 45.2 | 0.18 | 0.22 | NO
# 2025-11-12 | 148.50 | 42.1 | 0.22 | 0.25 | YES ← K crossed D
```

### Scenario 3: Monitor VM Logs Live
```bash
# Start live log stream
tvlogs-live

# Output will show:
# Nov 13 12:00:00 - 🔍 Starting scan cycle
# Nov 13 12:00:05 - ⏰ Skipped 1 symbol in grace period
# Nov 13 12:00:10 - Scanning AAPL...
# Nov 13 12:00:12 - 🚀 Signal! AAPL
# Nov 13 12:00:15 - ✓ Scan complete! Found 1 signal(s)
```

### Scenario 4: Emergency Stop
```bash
# Stop service immediately
tvstop

# Remove all symbols
tvclear

# Push to VM
tvsync

# Restart when ready
tvstart
```

---

## 🔐 Security Best Practices

### ⚠️ **NEVER Commit Secrets!**

**Sensitive Files (already in `.gitignore`):**
- ✅ `config.yaml` - Contains bot token and API keys
- ✅ `.env` - Environment variables
- ✅ `watchlist.json` - May contain private trading data
- ✅ `signal_history.json` - Trading history
- ✅ `logs/` - May contain sensitive data

### ✅ **Safe Configuration**

**Option 1: Environment Variables**
```bash
# .env file (not committed)
TELEGRAM_BOT_TOKEN=123456:ABCdef...
TELEGRAM_CHAT_ID=987654321

# Load in config
import os
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
```

**Option 2: Config Template**
```yaml
# config.yaml.example (committed)
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"
  chat_id: "YOUR_CHAT_ID_HERE"

# config.yaml (not committed)
telegram:
  bot_token: "123456:ABCdef..."
  chat_id: "987654321"
```

### 🔒 **If You Leaked Secrets**

1. **Immediately revoke old tokens:**
   - Telegram: @BotFather → /revoke
   - AlphaVantage: Generate new key

2. **Generate new credentials**

3. **Clean Git history:**
```bash
# Install BFG Repo Cleaner
brew install bfg

# Remove sensitive file from history
bfg --delete-files config.yaml

# Force push (WARNING: Rewrites history)
git push --force
```

---

## 📚 Additional Resources

### Documentation Files
- `QUICKSTART.md` - Step-by-step setup guide
- `QUICK_COMMANDS.md` - Command reference
- `AUTO_SYNC_GUIDE.md` - Sync workflow details
- `CODE_REVIEW_REPORT.md` - Code quality analysis
- `SECURITY.md` - Security guidelines
- `deploy/README.md` - VM deployment guide

### External Links
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Rich Library Docs](https://rich.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

---

## 🤝 Contributing

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black mypy

# Format code
black src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/ -v --cov=src
```

### Commit Message Format
```
Type: Brief description

- Detailed change 1
- Detailed change 2

Examples:
  Feature: Add grace period filtering to VM
  Fix: Correct JSON trailing comma validation
  Docs: Update README with new UI examples
  Test: Add rate limiter edge case tests
  Refactor: Move grace period logic to VM-side
```

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Credits

**Built with:**
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance data
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram API
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Text recognition
- [pytest](https://docs.pytest.org/) - Testing framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation

---

## 📞 Support

**Need Help?**

1. Check `tvhealth` for system status
2. Review logs: `tvlogs`
3. Read troubleshooting section above
4. Check GitHub Issues
5. Review test coverage: `pytest --cov`

---

## 🎯 Roadmap

### ✅ Completed
- Beautiful UI with Rich library
- Comprehensive test suite (46 tests)
- VM-side grace period filtering
- Adaptive rate limiting
- Environment variable support
- Health check system
- Alias command system

### 🔄 In Progress
- Paper trading integration
- Binance trading bot (separate project)
- Backtesting framework

### 📋 Planned
- Web dashboard
- Mobile app notifications
- Multi-exchange support
- Machine learning signal optimization
- Real-time data streaming

---

**Happy Trading! 🚀📈**

*Remember: This is for educational purposes. Always do your own research before making investment decisions.*
