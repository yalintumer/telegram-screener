# Telegram Screener - Basitleştirilmiş Versiyon

Notion'dan watchlist çeker, Stochastic RSI sinyali olanları Telegram'a gönderir.

## 🎯 Ne Yapar?

1. **Notion Database**'den watchlist sembollerini çeker
2. Her sembol için **Stochastic RSI** hesaplar
3. AL sinyali olanları **Telegram**'a bildirim gönderir

## 📋 Kurulum

### 1. Python Bağımlılıkları

```bash
pip install -r requirements.txt
```

### 2. Konfigürasyon

`config.yaml` dosyasını düzenle:

```yaml
telegram:
  bot_token: "YOUR_TELEGRAM_BOT_TOKEN"
  chat_id: "YOUR_TELEGRAM_CHAT_ID"

notion:
  api_token: "YOUR_NOTION_API_TOKEN"
  database_id: "YOUR_NOTION_DATABASE_ID"

data:
  max_watch_days: 5

api:
  provider: "yfinance"
  token: ""
```

### 3. Notion Database Yapısı

Notion'da bir database oluştur ve şu sütunu ekle:
- **Symbol** (veya Ticker/Stock): Hisse senedi sembolleri (örn: AAPL, MSFT)

## 🚀 Kullanım

### Tek Scan (Test)

```bash
python -m src.main --once
```

### Sürekli Çalışma (VM'de)

```bash
# Her 1 saatte bir tarar
python -m src.main --interval 3600

# Her 30 dakikada bir
python -m src.main --interval 1800
```

### Systemd Service (Ubuntu/VM)

`/etc/systemd/system/telegram-screener.service`:

```ini
[Unit]
Description=Telegram Screener
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-screener
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 3600
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Servisi başlat:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-screener
sudo systemctl start telegram-screener
sudo systemctl status telegram-screener
```

## 📊 Stochastic RSI Sinyali

**AL Sinyali** koşulları:
1. K çizgisi D çizgisini yukarı keserse (bullish cross)
2. Bu kesişme oversold bölgede olursa (K veya D < 0.20)

## 🔧 Parametreler

- `--config`: Config dosyası yolu (default: config.yaml)
- `--interval`: Tarama aralığı saniye cinsinden (default: 3600)
- `--once`: Tek sefer çalış ve çık

## 📝 Loglar

Loglar `logs/` klasöründe tutulur:
- `app.log`: Tüm loglar
- Konsola da yazdırılır

## 🆘 Sorun Giderme

### Notion'dan veri gelmiyor

1. API token'ın doğru olduğundan emin ol
2. Database ID'nin doğru olduğundan emin ol
3. Integration'ın database'e erişimi olduğundan emin ol (Share → Connections)
4. Database'de "Symbol" sütunu var mı kontrol et

### Telegram mesaj gitmiyor

1. Bot token doğru mu?
2. Chat ID doğru mu?
3. Bot'u gruba ekledin mi?

### Hisse verisi gelmiyor

yfinance bazı semboller için veri bulamayabilir. Sadece US hisseler için çalışır.

## 🔄 Eski Komplex Versiyona Dönüş

Eğer eski sisteme dönmek istersen:

```bash
mv src/main.py src/main_simple.py
mv src/main_old_complex.py src/main.py
```

## 📦 Dosya Yapısı

```
telegram-screener/
├── src/
│   ├── main.py              # Basit ana dosya
│   ├── notion_client.py     # Notion API
│   ├── telegram_client.py   # Telegram API
│   ├── indicators.py        # Stochastic RSI
│   ├── data_source_yfinance.py
│   ├── config.py
│   └── logger.py
├── config.yaml              # Ana konfigürasyon
├── requirements.txt         # Python bağımlılıkları
└── README_SIMPLE.md         # Bu dosya
```
