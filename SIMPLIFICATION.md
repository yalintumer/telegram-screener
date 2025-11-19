# 🎉 Basitleştirme Tamamlandı!

## ✨ Değişiklikler

### ❌ Kaldırılanlar

1. **OCR & Screenshot Capture** - Artık TradingView'dan manuel capture yok
2. **Grace Period Logic** - Karmaşık sinyal geçmişi ve bekleme süreleri kaldırıldı
3. **Watchlist.json** - Artık Notion kullanıyoruz
4. **VM SSH Sync** - VM artık Notion'dan direkt çekiyor
5. **Git Sync (symbols.txt)** - Gereksiz
6. **Rate Limiter, Health Monitor** - Kompleks sistemler kaldırıldı
7. **UI/Rich Terminal** - Basit print() kullanıyoruz
8. **Capture Command** - Artık yok

### ✅ Kalanlar (Basitleştirilmiş)

1. **Notion Integration** - Watchlist artık Notion database'den geliyor
2. **Stochastic RSI** - Aynı sinyal algoritması
3. **Telegram Notifications** - Aynı bildirim sistemi
4. **yfinance Data** - Aynı veri kaynağı

## 📂 Yeni Dosya Yapısı

```
src/
├── main.py                    # ✨ YENİ - Basit ana dosya (~150 satır)
├── notion_client.py           # ✨ YENİ - Notion API entegrasyonu
├── config.py                  # Güncellendi - Notion config eklendi
├── telegram_client.py         # Aynı
├── indicators.py              # Aynı
├── data_source_yfinance.py    # Aynı
├── logger.py                  # Aynı
└── exceptions.py              # Aynı

# Artık kullanılmıyor (backup):
├── main_old_complex.py        # Eski 988 satırlık sistem
├── capture.py                 # OCR capture
├── ocr.py                     # OCR logic
├── ui.py                      # Rich terminal UI
├── watchlist.py               # Local watchlist
├── rate_limiter.py           # Rate limiting
├── health.py                  # Health monitoring
└── validation.py              # Symbol validation
```

## 🚀 Kullanım

### 1. Notion Setup

1. Notion'da bir Database oluştur
2. "Symbol" sütunu ekle (veya Ticker/Stock)
3. Integration oluştur (https://www.notion.so/my-integrations)
4. Database'i integration ile paylaş (Share → Connections)
5. API token ve Database ID'yi kopyala

### 2. Config

`config.yaml` düzenle:

```yaml
telegram:
  bot_token: "123456:ABC..."
  chat_id: "-100123456789"

notion:
  api_token: "secret_xxx..."
  database_id: "abc123..."

data:
  max_watch_days: 5

api:
  provider: "yfinance"
  token: ""
```

### 3. Çalıştır

**Tek test:**
```bash
python -m src.main --once
```

**Sürekli (her 1 saat):**
```bash
python -m src.main --interval 3600
```

**VM'de Systemd Service:**
```bash
bash deploy_simple.sh
```

## 📊 Nasıl Çalışır?

```
┌─────────────┐
│   NOTION    │  ← Sen buradan watchlist düzenlersin
│  Database   │
└──────┬──────┘
       │
       │ API call (her scan'de)
       ↓
┌─────────────┐
│   Scanner   │  ← Her 1 saatte çalışır (veya senin belirlediğin süre)
└──────┬──────┘
       │
       │ yfinance ile veri çek
       │ Stochastic RSI hesapla
       │
       ↓
┌─────────────┐
│ Sinyal var? │
└──────┬──────┘
       │
       │ Evet ise
       ↓
┌─────────────┐
│  TELEGRAM   │  ← Bildirim gönder
└─────────────┘
```

## 🔧 VM Deployment

### Ubuntu/Debian VM'de:

```bash
# 1. Script çalıştır
bash deploy_simple.sh

# 2. Config düzenle
nano config.yaml

# 3. Test et
source venv/bin/activate
python -m src.main --once

# 4. Service başlat
systemctl start telegram-screener
systemctl enable telegram-screener

# 5. Log kontrol
tail -f logs/service.log
```

## 📝 Notion Database Yapısı

Minimum gereksinim:

| Symbol | (İsteğe bağlı diğer sütunlar) |
|--------|-------------------------------|
| AAPL   | ...                          |
| MSFT   | ...                          |
| GOOGL  | ...                          |

- **Symbol** sütunu olmalı (veya "Ticker", "Stock" gibi)
- Her satır bir hisse senedi
- Database'i integration ile paylaş

## 🎯 Stochastic RSI Sinyali

**AL Sinyali** koşulları:
1. ✅ K çizgisi D çizgisini yukarı kesiyor
2. ✅ Kesişme oversold bölgede (K veya D < 0.20)

## 💡 Avantajlar

1. **Daha Basit** - 988 satırdan ~150 satıra düştü
2. **Daha Anlaşılır** - Karmaşık grace period logic yok
3. **Kolay Yönetim** - Watchlist Notion'da, web UI ile düzenle
4. **Daha Az Bağımlılık** - OCR, screenshot, UI kütüphaneleri kaldırıldı
5. **VM'de Stabil** - Daha az moving parts
6. **Manuel Kontrol** - Sen Notion'dan watchlist'i yönetirsin

## 🔙 Eski Sisteme Dönüş

Eğer gerekirse:

```bash
mv src/main.py src/main_simple.py
mv src/main_old_complex.py src/main.py
git checkout requirements.txt config.yaml
```

## 📚 Ek Dökümanlar

- `README_SIMPLE.md` - Kullanım kılavuzu
- `deploy_simple.sh` - VM deployment script
- `config.example.yaml` - Örnek config

---

**Artık sadece Notion'dan watchlist düzenleyip, VM'in sinyalleri yakalamasını izle! 🚀**
