# Git-Based Symbol Sync Workflow

## Overview
Local capture tool commits symbols to git. VM scanner pulls and reads automatically.
No SSH, no credentials, no network complexity.

## Architecture

```
Local (macOS)          GitHub              VM Scanner
─────────────          ──────              ──────────
1. Capture screen
2. Extract symbols
3. Save to symbols.txt
4. git commit + push  ──────>  symbols.txt  <────── git pull (every scan)
                                                      Read symbols
                                                      Scan for signals
                                                      Send to Telegram
```

## Local Usage (macOS)

### Capture and Auto-Sync
```bash
python3 -m src.main capture
```
This will:
1. Take screenshot
2. Extract tickers via OCR
3. Save to `symbols.txt`
4. Auto-commit and push to GitHub
5. VM will pick it up on next scan

### Manual Symbol Management
Edit `symbols.txt` directly:
```bash
nano symbols.txt
# Add symbols, one per line
git add symbols.txt
git commit -m "Add AAPL, TSLA"
git push
```

## VM Usage

### Deploy/Update
```bash
cd /root/telegram-screener
git pull
sudo cp telegram-screener.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart telegram-screener.service
```

### Check Status
```bash
sudo systemctl status telegram-screener.service
sudo journalctl -u telegram-screener.service -f  # Follow logs
```

### How Scanner Works
Every scan cycle (15 seconds between symbols):
1. `git pull` to get latest symbols.txt
2. Read symbols from file
3. Scan each symbol for buy signals
4. Send alerts to Telegram (with grace period)

### Manual Scan Test
```bash
cd /root/telegram-screener
source venv/bin/activate
python3 -m src.main scan --sleep 5
```

## Fallback Behavior

If `symbols.txt` is empty or missing:
- Scanner falls back to watchlist database
- You can still use `add`/`remove` commands

## Benefits

✅ No SSH configuration needed
✅ No network errors during sync
✅ Git handles conflicts automatically
✅ Full audit trail of symbol changes
✅ Can review before VM picks up
✅ Works even if VM is down temporarily

## Troubleshooting

### "No symbols found"
```bash
# Check if file exists
cat symbols.txt

# If empty, add symbols manually
echo "AAPL" >> symbols.txt
echo "TSLA" >> symbols.txt
git add symbols.txt
git commit -m "Add test symbols"
git push
```

### "Git pull failed" in logs
Not a fatal error. Scanner continues with local copy.
Check VM git config:
```bash
cd /root/telegram-screener
git status
git pull  # Should work without password (public repo or SSH key)
```

### Symbols not syncing
```bash
# On local machine - verify push worked
git log -1  # See latest commit

# On VM - verify pull worked
cd /root/telegram-screener
git pull
cat symbols.txt  # Should match local
```

## Next Steps

1. **Test the flow:**
   - Run `capture` locally
   - Check GitHub for updated `symbols.txt`
   - Watch VM logs for git pull and scanning

2. **Monitor in production:**
   ```bash
   # Follow scanner logs
   sudo journalctl -u telegram-screener.service -f
   ```

3. **Iterate:**
   - Add symbols as you find interesting charts
   - Scanner will pick them up automatically
   - Grace period prevents spam (24h between signals per symbol)
