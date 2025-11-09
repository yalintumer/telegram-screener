#!/usr/bin/env python3
"""Verify weekday numbers"""

from datetime import date

# Test specific dates
dates = [
    (date(2025, 11, 3), "Monday"),
    (date(2025, 11, 4), "Tuesday"),
    (date(2025, 11, 5), "Wednesday"),
    (date(2025, 11, 6), "Thursday"),
    (date(2025, 11, 7), "Friday"),
    (date(2025, 11, 8), "Saturday"),
    (date(2025, 11, 9), "Sunday"),
]

print("Weekday verification:")
print("-" * 40)
for d, name in dates:
    weekday_num = d.weekday()
    is_business = weekday_num < 5
    print(f"{name:10s} = {weekday_num} -> Business day: {is_business}")

print("\n✅ 0-4 (Monday-Friday) are business days")
print("❌ 5-6 (Saturday-Sunday) are NOT business days")
