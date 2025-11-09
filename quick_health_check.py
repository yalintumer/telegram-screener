#!/usr/bin/env python3
"""
Quick verification script - Run this after updates
"""

import sys
sys.path.insert(0, 'src')

print("🔍 Quick Code Health Check")
print("=" * 60)

# 1. Import check
try:
    from watchlist import _business_days_between, prune, can_add_to_watchlist
    from indicators import rsi, stochastic_rsi, stoch_rsi_buy
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# 2. Business days sanity check
from datetime import date
monday = date(2025, 11, 3)
friday = date(2025, 11, 7)
days = _business_days_between(monday, friday)
assert days == 4, f"Expected 4, got {days}"
print(f"✅ Business days: Mon→Fri = {days} days (correct)")

# 3. RSI with all gains (no crash)
import pandas as pd
gains = pd.Series([100 + i for i in range(20)])
r = rsi(gains, 14)
assert not r.isna().all(), "RSI returned all NaN"
assert r.iloc[-1] > 90, f"Expected RSI near 100, got {r.iloc[-1]:.2f}"
print(f"✅ RSI divide-by-zero protection: RSI={r.iloc[-1]:.2f}")

# 4. Stoch RSI boundary
small_df = pd.DataFrame({
    'rsi': [50, 50, 50, 50, 50],
    'k': [0.1, 0.1, 0.1, 0.1, 0.1],
    'd': [0.2, 0.2, 0.2, 0.2, 0.2]
})
result = stoch_rsi_buy(small_df, lookback_days=3)  # Should not crash
print(f"✅ Stoch RSI boundary check: No crash with 5 rows")

print("\n" + "=" * 60)
print("🎉 All checks passed! Code is healthy.")
print("\n📋 Changes made:")
print("   1. Prune logic: business_days > max_days (not >=)")
print("   2. RSI: Added divide-by-zero protection")
print("   3. Stoch RSI: Fixed boundary check (lookback+2)")
print("   4. Cleanup: Now uses business days")
print("\n📖 See CODE_REVIEW_REPORT.md for full details")
