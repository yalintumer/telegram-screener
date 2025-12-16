# Failure Scenarios & System Behavior

## Overview

This document describes how the telegram-screener handles various failure scenarios.
The system is designed to be resilient and self-healing where possible.

---

## Failure Matrix

| Component | Failure Type | Detection | System Behavior | Recovery |
|-----------|--------------|-----------|-----------------|----------|
| **Notion API** | 401 Unauthorized | HTTP 401 | Log error, skip operation | Manual: Check API token |
| **Notion API** | 429 Rate Limited | HTTP 429 | Auto-retry with backoff (3x) | Auto: Exponential backoff |
| **Notion API** | 500/502/503/504 | HTTP 5xx | Auto-retry with backoff (3x) | Auto: Max 3 attempts |
| **Notion API** | Network timeout | Request timeout | Auto-retry with backoff (3x) | Auto: 30s timeout |
| **Telegram API** | 401 Invalid token | HTTP 401 | Log error, increment failure count | Manual: Check bot token |
| **Telegram API** | 429 Rate Limited | HTTP 429 | Wait `Retry-After` header | Auto: Respects rate limit |
| **Telegram API** | Network error | Connection failed | Retry 3x, log warning | Auto: Continue scanning |
| **Telegram API** | 5 consecutive fails | Failure counter | Raise TelegramError, stop | Manual: Check connectivity |
| **yfinance API** | No data returned | Empty DataFrame | Skip symbol, continue | Auto: Move to next symbol |
| **yfinance API** | Rate limited | HTTP 429/error | Rate limiter kicks in | Auto: 60 req/min limit |
| **yfinance API** | Invalid symbol | API error | Log warning, skip symbol | Auto: Continue scanning |
| **File System** | Backup dir not writable | Permission error | Fallback to /tmp | Auto: Use fallback dir |
| **File System** | Disk full | Write error | Log error, skip backup | Manual: Free disk space |
| **Memory** | OOM (Out of Memory) | Process killed | Systemd restarts service | Auto: RestartSec=60 |
| **Process** | Unhandled exception | Exception raised | Sentry capture, log, continue | Auto: Try next cycle |
| **Process** | Fatal error | Exception in main | Service restart | Auto: Systemd restart |

---

## Component-Specific Behavior

### Notion API Failures

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Call      │────▶│  Rate Limiter   │────▶│  HTTP Request   │
│                 │     │  (30 req/min)   │     │  (with retry)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
                ┌───────────────┐              ┌─────────────────┐              ┌─────────────────┐
                │   Success     │              │  Retryable      │              │  Non-Retryable  │
                │   (200)       │              │  (429,5xx)      │              │  (401,403,404)  │
                └───────────────┘              └────────┬────────┘              └────────┬────────┘
                                                       │                                 │
                                                       ▼                                 ▼
                                               ┌─────────────────┐              ┌─────────────────┐
                                               │  Retry with     │              │  Log error      │
                                               │  exp backoff    │              │  Return None    │
                                               │  (max 3x)       │              │                 │
                                               └─────────────────┘              └─────────────────┘
```

**Retry delays:**
- Attempt 1: 1 second
- Attempt 2: 2 seconds  
- Attempt 3: 4 seconds
- Total max wait: ~7 seconds per operation

### Telegram API Failures

```
┌─────────────────┐
│  Send Message   │
│  (critical=?)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     Fail      ┌─────────────────┐
│   Try Send      │─────────────▶│  Retry (3x)     │
│   (timeout=10s) │              │  with backoff   │
└────────┬────────┘              └────────┬────────┘
         │                                │
         │ Success                        │ All failed
         ▼                                ▼
┌─────────────────┐              ┌─────────────────┐
│  Reset failure  │              │  Increment      │
│  counter        │              │  consecutive    │
└─────────────────┘              │  failures       │
                                 └────────┬────────┘
                                          │
                           ┌──────────────┴──────────────┐
                           │                             │
                           ▼                             ▼
                  ┌─────────────────┐         ┌─────────────────┐
                  │  failures < 5   │         │  failures >= 5  │
                  │  OR             │         │  OR             │
                  │  critical=False │         │  critical=True  │
                  └────────┬────────┘         └────────┬────────┘
                           │                           │
                           ▼                           ▼
                  ┌─────────────────┐         ┌─────────────────┐
                  │  Return False   │         │  Raise          │
                  │  Log warning    │         │  TelegramError  │
                  │  Continue scan  │         │  (crash/alert)  │
                  └─────────────────┘         └─────────────────┘
```

### Backup System Failures

```
Backup Attempt
     │
     ▼
┌─────────────────┐
│  Check backup   │
│  directory      │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Exists? │
    └────┬────┘
    No   │   Yes
    │    │    │
    ▼    │    ▼
┌───────┐│┌───────────┐
│Create │││  Writable?│
│  dir  │││           │
└───┬───┘│└─────┬─────┘
    │    │  No  │  Yes
    │    │  │   │
    ▼    │  ▼   ▼
┌───────────────┐   ┌───────────────┐
│   Fallback    │   │   Continue    │
│   to /tmp     │   │   with backup │
└───────────────┘   └───────────────┘
```

---

## Scan Cycle Error Handling

Each scan cycle is wrapped in try/catch:

```python
for cycle in continuous_loop:
    try:
        # Set correlation ID for this cycle
        cid = set_correlation_id(f"cycle-{cycle}")
        
        # Update health: scanning
        health.scan_started(cycle)
        
        # Stage 1: Market scan (with individual symbol error handling)
        run_market_scan()  # Errors logged, continues to next symbol
        
        # Stage 2: WaveTrend scan
        run_wavetrend_scan()  # Errors logged, continues
        
        # Update health: success
        health.scan_completed(stats)
        
    except Exception as e:
        # Update health: degraded
        health.scan_failed(str(e))
        
        # Report to Sentry
        sentry_sdk.capture_exception(e)
        
        # Log with correlation ID
        logger.exception("scan_cycle_failed", cycle=cycle)
        
    # Always continue to next cycle
    sleep(interval)
```

---

## Health States

| State | Meaning | health.json status |
|-------|---------|-------------------|
| **Starting** | Service just started | `"starting"` |
| **Scanning** | Currently in scan cycle | `"scanning"` |
| **Healthy** | Last scan completed OK | `"healthy"` |
| **Degraded** | Last scan had errors | `"degraded"` |

---

## Monitoring Recommendations

### Check health.json
```bash
# Quick health check
cat /root/telegram-screener/health.json | jq '.status'

# Full status
cat /root/telegram-screener/health.json | jq '.'
```

### Check for errors
```bash
# Recent errors
grep ERROR /root/telegram-screener/logs/screener_*.log | tail -20

# Errors by correlation ID
grep "cid=cycle-5" /root/telegram-screener/logs/screener_*.log | grep ERROR
```

### Check retry activity
```bash
# Notion retries
grep "notion.retry" /root/telegram-screener/logs/screener_*.log

# Telegram failures
grep "telegram.send_failed" /root/telegram-screener/logs/screener_*.log
```

---

## Recovery Procedures

### Notion API Issues
1. Check API token validity in Notion settings
2. Verify database IDs are correct
3. Check Notion status: https://status.notion.so/

### Telegram Issues
1. Verify bot token with BotFather
2. Check chat_id is correct
3. Ensure bot hasn't been blocked

### Service Won't Start
```bash
# Check logs
journalctl -u telegram-screener -n 100

# Check Python errors
/root/telegram-screener/venv/bin/python -c "from src.main import main"

# Restart manually
systemctl restart telegram-screener
```

### Data Recovery
```bash
# List backups
ls -la /root/telegram-screener/backups/

# Restore from backup
cat /root/telegram-screener/backups/signals_20251216_120000.json | jq '.pages | length'
```
