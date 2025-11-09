#!/usr/bin/env python3
"""Test business days calculation"""

from datetime import date, timedelta
import sys
sys.path.insert(0, 'src')

from watchlist import _business_days_between

# Test 1: Hafta içi 5 gün (Pazartesi-Cuma)
monday = date(2025, 11, 3)  # Monday
friday = date(2025, 11, 7)  # Friday
days = _business_days_between(monday, friday)
print(f"Test 1: Monday to Friday = {days} business days (expected: 4)")
assert days == 4, f"Expected 4 but got {days}"

# Test 2: Hafta sonu dahil (Cuma-Pazartesi)
friday = date(2025, 11, 7)  # Friday
next_monday = date(2025, 11, 10)  # Monday
days = _business_days_between(friday, next_monday)
print(f"Test 2: Friday to next Monday = {days} business days (expected: 1)")
assert days == 1, f"Expected 1 but got {days}"

# Test 3: Tam bir hafta (Pazartesi-Pazartesi)
monday1 = date(2025, 11, 3)  # Monday
monday2 = date(2025, 11, 10)  # Next Monday
days = _business_days_between(monday1, monday2)
print(f"Test 3: Monday to next Monday = {days} business days (expected: 5)")
assert days == 5, f"Expected 5 but got {days}"

# Test 4: 7 takvim günü içinde 5 iş günü
monday = date(2025, 11, 3)  # Monday
next_monday = date(2025, 11, 10)  # Monday (7 days later)
days = _business_days_between(monday, next_monday)
print(f"Test 4: 7 calendar days = {days} business days (expected: 5)")
assert days == 5, f"Expected 5 but got {days}"

# Test 5: 5 takvim günü (Pazartesi-Cumartesi)
monday = date(2025, 11, 3)  # Monday
saturday = date(2025, 11, 8)  # Saturday
days = _business_days_between(monday, saturday)
print(f"Test 5: Monday to Saturday = {days} business days (expected: 5)")
assert days == 5, f"Expected 5 but got {days}"

print("\n✅ All tests passed! Business days calculation is working correctly.")
print(f"\nNow max_watch_days=5 means 5 business days (weekdays only).")
print(f"Weekend days are excluded from the count.")
