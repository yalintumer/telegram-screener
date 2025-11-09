#!/usr/bin/env python3
"""Check which symbols are in grace period"""

import json
from pathlib import Path
from datetime import date, timedelta

def business_days_between(start_date, end_date):
    """Calculate business days between two dates"""
    if start_date > end_date:
        return 0
    
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4
            days += 1
        current += timedelta(days=1)
    return days

def check_grace_periods():
    """Check signal history for grace periods"""
    signal_path = Path("signal_history.json")
    
    if not signal_path.exists():
        print("✅ No signals in grace period")
        return
    
    data = json.loads(signal_path.read_text())
    today = date.today()
    
    print("⏰ Grace Period Status (5 business days):\n")
    
    grace_symbols = []
    for symbol, info in data.items():
        last_signal = date.fromisoformat(info["last_signal"])
        days_since = business_days_between(last_signal, today)
        days_remaining = 5 - days_since
        
        if days_remaining > 0:
            grace_symbols.append((symbol, days_remaining, info["count"]))
    
    if not grace_symbols:
        print("✅ No symbols in grace period")
    else:
        for symbol, days_left, count in sorted(grace_symbols, key=lambda x: x[1]):
            emoji = "🟡" if days_left <= 2 else "🟢"
            print(f"{emoji} {symbol}: {days_left} business days left (signaled {count}x)")

if __name__ == "__main__":
    check_grace_periods()
