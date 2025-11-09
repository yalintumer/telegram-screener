#!/usr/bin/env python3
"""
Trader mantığı: "Max 5 iş günü" ne demek?

Senaryo A: Ekleme gününü say
  - Pazartesi ekledim (1. gün)
  - Salı (2. gün)
  - Çarşamba (3. gün)
  - Perşembe (4. gün)
  - Cuma (5. gün) ← 5. gün sonunda çıkar
  - Pazartesi sabah watchlist'te yok

Senaryo B: Ekleme gününden sonraki günleri say
  - Pazartesi ekledim (Gün 0)
  - Salı (1. gün)
  - Çarşamba (2. gün)
  - Perşembe (3. gün)
  - Cuma (4. gün)
  - Pazartesi (5. gün) ← 5. gün sonunda çıkar
  - Salı sabah watchlist'te yok

SORU: Hangi mantık doğru?
"""

print(__doc__)

response = input("\n🤔 Hangi davranış isteniyor? (A/B): ").strip().upper()

if response == 'A':
    print("\n✅ Senaryo A seçildi: Ekleme günü dahil")
    print("   current <= end_date olmalı (başlangıç günü dahil)")
    print("   Veya business_days >= max_days yerine > max_days")
    
elif response == 'B':
    print("\n✅ Senaryo B seçildi: Ekleme günü hariç")
    print("   Mevcut kod zaten doğru")
    print("   current < end_date (başlangıç günü hariç)")
else:
    print("\n⚠️  Belirsiz seçim")

print("\n📊 ÖNERİ:")
print("   Trader perspektifi: Senaryo A daha mantıklı")
print("   'Pazartesi ekledim, 5 iş günü bekle' = Cuma akşam çıkar")
print("   Değil: 'Pazartesi ekledim, 5 iş günü bekle' = Pazartesi akşam çıkar")
