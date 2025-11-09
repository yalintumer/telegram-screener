#!/usr/bin/env python3
"""Test business days bug: start date not counted"""

from datetime import date, timedelta
import sys
sys.path.insert(0, 'src')

from watchlist import _business_days_between

print("🔍 BUG TEST: Start date should be counted!")
print("=" * 60)

# Scenario: Pazartesi ekledim, bugün Cuma (aynı hafta)
monday = date(2025, 11, 3)  # Monday
friday = date(2025, 11, 7)  # Friday

days = _business_days_between(monday, friday)
print(f"Scenario 1: Pazartesi ekledim → Bugün Cuma")
print(f"  Dates: {monday} → {friday}")
print(f"  Current result: {days} business days")
print(f"  Expected: 5 business days (Mon, Tue, Wed, Thu, Fri)")
print(f"  ❌ HATA: Pazartesi günü sayılmıyor!\n")

# Scenario 2: Bugün ile bugün
today = date(2025, 11, 9)
days = _business_days_between(today, today)
print(f"Scenario 2: Bugün ekledim → Bugün")
print(f"  Dates: {today} → {today}")
print(f"  Current result: {days} business days")
print(f"  Expected: 0 (aynı gün)")
print(f"  ✅ Doğru\n")

# Scenario 3: Perşembe ekledim, Pazartesi kontrolü
thursday = date(2025, 11, 6)  # Thursday
next_monday = date(2025, 11, 10)  # Next Monday
days = _business_days_between(thursday, next_monday)
print(f"Scenario 3: Perşembe ekledim → Pazartesi")
print(f"  Dates: {thursday} → {next_monday}")
print(f"  Current result: {days} business days")
print(f"  Expected: 3 business days (Thu, Fri, Mon)")
print(f"  ❌ HATA: Perşembe günü sayılmıyor!\n")

print("=" * 60)
print("🎯 TRADER MANTIĞI:")
print("   Pazartesi eklediğim hisse, o gün 1. iş günü olmalı!")
print("   5 iş günü = Pazartesi → Cuma (dahil)")
print("   Şu anki kod başlangıç gününü saymiyor!")
