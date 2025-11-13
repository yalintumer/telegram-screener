# 🚀 Production Deployment Guide

## Platform-Specific Instructions

### macOS (Development/Local)

macOS uses **launchd** instead of systemd. Use the `deploy_macos.py` script:

#### Quick Start
```bash
# 1. Install and configure
cd ~/telegram-screener  # or your project path
python deploy_macos.py install

# 2. Configure credentials
nano .env  # Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Start service
python deploy_macos.py start

# 4. Check status
python deploy_macos.py status

# 5. View logs
python deploy_macos.py logs
```

#### Available Commands
```bash
python deploy_macos.py install    # Install Launch Agent
python deploy_macos.py start      # Start service
python deploy_macos.py stop       # Stop service
python deploy_macos.py restart    # Restart service
python deploy_macos.py status     # Check status
python deploy_macos.py logs       # View logs
python deploy_macos.py uninstall  # Remove service
```

#### Logs Location
```bash
# Output logs
tail -f logs/launchd.out.log

# Error logs
tail -f logs/launchd.err.log

# Application logs
tail -f logs/screener_$(date +%Y%m%d).log
```

---

## Linux/VM Deployment (Production)

### Quick Deploy (Systemd Service - Recommended)

### 1. Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.13 python3.13-venv tesseract-ocr git
```

### 2. Clone and Setup
```bash
cd ~
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3. Configure
```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Add your credentials:
# TELEGRAM_BOT_TOKEN=your_token_here
# TELEGRAM_CHAT_ID=your_chat_id_here

# Copy and edit config
cp config.example.yaml config.yaml
nano config.yaml
```

### 4. Test Installation
```bash
# Test commands
python -m src.main add AAPL MSFT GOOGL
python -m src.main list
python -m src.main status

# Test scan (dry run)
python -m src.main scan --dry-run
```

### 5. Install as Systemd Service
```bash
# Deploy service
python deploy_service.py install

# Start service
python deploy_service.py start

# Check status
python deploy_service.py status

# View logs
python deploy_service.py logs
```

### 6. Monitor Service
```bash
# Live logs
sudo journalctl -u telegram-screener -f

# Service status
sudo systemctl status telegram-screener

# Restart service
python deploy_service.py restart
```

## Docker Deployment (Alternative)

### 1. Build Image
```bash
docker build -t telegram-screener .
```

### 2. Run Container
```bash
# Using docker run
docker run -d \
  --name telegram-screener \
  --restart unless-stopped \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/watchlist.json:/app/watchlist.json \
  -v $(pwd)/signal_history.json:/app/signal_history.json \
  -v $(pwd)/logs:/app/logs \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  telegram-screener
```

### 3. Using Docker Compose
```bash
# Configure .env file first
cp .env.example .env
nano .env

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## Manual Run (Development)

### Continuous Mode (Recommended for Production)
```bash
# Run continuously, scan every hour
python -m src.main run --interval 3600

# Custom interval (every 2 hours)
python -m src.main run --interval 7200
```

### One-time Commands
```bash
# Capture symbols from TradingView
python -m src.main capture

# Scan for signals
python -m src.main scan

# Check system status
python -m src.main status
```

## Monitoring & Maintenance

### Health Checks
```bash
# System status
python -m src.main status

# Watchlist
python -m src.main list

# Check specific symbol
python -m src.main debug AAPL
```

### Log Management
```bash
# View application logs
tail -f logs/screener_$(date +%Y%m%d).log

# View systemd logs
sudo journalctl -u telegram-screener -n 100
```

### Backup Data
```bash
# Backup important files
tar -czf backup_$(date +%Y%m%d).tar.gz \
  watchlist.json \
  signal_history.json \
  stats.json \
  config.yaml \
  .env
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status telegram-screener

# View detailed logs
sudo journalctl -u telegram-screener -xe

# Check file permissions
ls -la /root/telegram-screener/
```

### OCR Not Working
```bash
# Verify tesseract installation
tesseract --version

# Test OCR manually
python -m src.main capture --dry-run
```

### Network Issues
```bash
# Test Telegram connectivity
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"

# Test yfinance
python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1d'))"
```

## Security Best Practices

1. **Never commit secrets**
   - Keep `.env` and `config.yaml` out of git
   - Use `.env.example` as template

2. **Restrict file permissions**
   ```bash
   chmod 600 .env config.yaml
   chmod 700 deploy_service.py
   ```

3. **Regular updates**
   ```bash
   cd ~/telegram-screener
   git pull
   source venv/bin/activate
   pip install --upgrade -r requirements.txt
   python deploy_service.py restart
   ```

4. **Monitor logs**
   - Check logs daily for errors
   - Rotate logs to prevent disk fill
   - Set up log alerts (optional)

## Performance Tuning

### Reduce Memory Usage
- Use sequential scan mode (not parallel)
- Reduce scan interval if CPU/memory constrained
- Limit watchlist size

### Optimize Scan Speed
- Use parallel scan mode: `--parallel`
- Reduce sleep between symbols: `--sleep 5`
- But be careful of rate limits!

### Resource Limits
Edit `telegram-screener.service`:
```ini
[Service]
MemoryLimit=512M
CPUQuota=100%
```

## Upgrade Guide

```bash
# Stop service
python deploy_service.py stop

# Backup data
tar -czf backup_pre_upgrade.tar.gz watchlist.json signal_history.json

# Update code
git pull

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart service
python deploy_service.py start

# Verify
python deploy_service.py status
```

## Support

- **Issues**: https://github.com/yalintumer/telegram-screener/issues
- **Logs**: Check `logs/` directory
- **Status**: Run `python -m src.main status`
