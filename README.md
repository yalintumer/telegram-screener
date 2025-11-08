# 📊 TV OCR Screener — Telegram Bot

**TradingView Screener** ekranlarından OCR ile ticker sembolleri çıkarıp, **Stokastik RSI** sinyal tespiti yapan ve **Telegram** üzerinden bildirim gönderen otomatik screener botu.

⚠️ **Önemli Uyarı**: Bu proje, TradingView web/uygulama arayüzünü ekran görüntüsü ile otomatik okumaya dayanır. Kullanım Koşulları ihlali riski vardır. Eğitim amaçlıdır; kullanımdan doğacak sorumluluk size aittir.

---

## 📚 Dokümantasyon

- 📖 **[QUICKSTART.md](QUICKSTART.md)** — Adım adım başlangıç kılavuzu
- 📋 **[CHEATSHEET.txt](CHEATSHEET.txt)** — Hızlı komut referansı (yazdır!)
- 📘 **[README.md](README.md)** — Detaylı teknik döküman (bu dosya)

---

## ✨ Özellikler

- 📸 **Otomatik ekran görüntüsü** + gelişmiş OCR preprocessing
- 🔍 **Ticker çıkarma** — akıllı filtreleme ve validasyon
- 📊 **Stokastik RSI** sinyal tespiti (günlük)
- 📱 **Telegram bildirimleri** — anında AL sinyali
- ⏱️ **Grace period** — sinyal verilen semboller 5 gün tekrar eklenemez
- 🧹 **Otomatik temizlik** — 30 gün+ eski sinyal kayıtları silinir
- 🖱️ **Pencere odaklama** — macOS PyAutoGUI ile TradingView'a otomatik tıklama
- 🚀 **Startup agent** — Mac açıldığında otomatik kontrol (hafta içi, 16 saat+)
- 🔄 **Otomatik retry** mekanizması (API ve Telegram)
- ⚡ **Paralel tarama** (opsiyonel, hızlı)
- 📝 **Yapısal loglama** — dosya + konsol
- 🧪 **Dry-run modu** — test için
- 🎯 **Progress bar** — görsel ilerleme takibi
- ⚙️ **Pydantic validasyon** — güvenli config
- 🌐 **yfinance desteği** — ücretsiz, limitsiz veri

---

## 🚀 Kurulum

### 1. Tesseract OCR Kur (macOS)

```bash
brew install tesseract
```

### 2. Python Sanal Ortamı Oluştur

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Konfigürasyon Ayarla

**Yöntem A: Config dosyası** (önerilen)
```bash
cp config.example.yaml config.yaml
# config.yaml dosyasını düzenle
```

**Yöntem B: Environment değişkenleri**
```bash
cp .env.example .env
# .env dosyasını düzenle
```

#### Gerekli ayarlar:

1. **Telegram Bot Token** — [@BotFather](https://t.me/BotFather)'dan al
2. **Telegram Chat ID** — [@userinfobot](https://t.me/userinfobot)'dan öğren
3. **AlphaVantage API Key** — [alphavantage.co](https://www.alphavantage.co/support/#api-key)'dan ücretsiz al
4. **Screen Region** — TradingView Screener tablosu koordinatları `[left, top, width, height]`

#### Screen Region nasıl bulunur?

1. TradingView Screener'ı aç (tam ekran değil, pencere modunda)
2. Screener tablosunu ortalarda konumlandır
3. macOS'ta **Cmd+Shift+4** ile screenshot aracını aç
4. Fareyle screener tablosunun sol üst köşesine tıkla
5. Koordinatları not et (örn: `100, 150`)
6. Sağ alt köşeye kadar sürükle, boyutları not et (örn: `900 x 600`)
7. `config.yaml` içinde `screen.region: [100, 150, 900, 600]` olarak ayarla

---

## 📖 Kullanım

### Temel Komutlar

#### 📸 Capture — Screenshot al ve watchlist güncelle
```bash
python -m src.main capture
```

#### 🔍 Scan — Watchlist'i tara ve sinyal bul
```bash
python -m src.main scan
```

#### 📋 List — Watchlist'i göster
```bash
python -m src.main list
```

#### 🔄 Run — Sürekli mod (capture + periyodik scan)
```bash
python -m src.main run --interval 3600
```

#### ➕ Add — Manuel sembol ekle
```bash
python -m src.main add AAPL MSFT TSLA
```

#### ➖ Remove — Sembol kaldır
```bash
python -m src.main remove AAPL
```

#### 🧹 Clear — Tüm listeyi temizle
```bash
python -m src.main clear
```

#### 🔍 Debug — Sembol analizi (K/D değerleri)
```bash
python -m src.main debug AAPL
```

---

### Gelişmiş Kullanım

#### Özel config dosyası
```bash
python -m src.main --config my_config.yaml capture
```

#### Test modu (hiçbir değişiklik yapmaz)
```bash
python -m src.main capture --dry-run
python -m src.main scan --dry-run
```

#### Paralel tarama (3x daha hızlı, rate limit riski)
```bash
python -m src.main scan --parallel
```

#### Özel bekleme süresi (rate limit için)
```bash
python -m src.main scan --sleep 20
```

#### 2 saatte bir otomatik tarama
```bash
python -m src.main run --interval 7200
```

#### Yardım
```bash
python -m src.main --help
python -m src.main scan --help
```

---

## ⚙️ Yapılandırma

### config.yaml örneği

```yaml
telegram:
  bot_token: "123456:ABC-DEF..."
  chat_id: "987654321"

api:
  provider: "alphavantage"
  token: "YOUR_KEY"
  rate_limit_per_minute: 5

data:
  max_watch_days: 5

screen:
  region: [100, 150, 900, 600]

tesseract:
  path: ""  # Boş bırak (otomatik) veya custom path
  lang: "eng"
  config_str: "--psm 6"

log_level: "INFO"
```

### Tesseract ayarları

- `--psm 6` — Düzenli metin bloğu (önerilen)
- `--psm 11` — Seyrek metin
- `--psm 3` — Tam otomatik (varsayılan)

---

## 🤖 Otomasyon (Cron)

BIST kapanış sonrası her gün (18:10) çalıştır:

```bash
crontab -e
```

Ekle:
```cron
10 18 * * 1-5 cd /Users/<kullanici>/Telegram\ Proje && /Users/<kullanici>/Telegram\ Proje/venv/bin/python -m src.main run --interval 3600 >> logs/cron.log 2>&1
```

Veya **launchd** ile (macOS önerilen):

`~/Library/LaunchAgents/com.tvscreener.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tvscreener</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/KULLANICI/Telegram Proje/venv/bin/python</string>
        <string>-m</string>
        <string>src.main</string>
        <string>run</string>
        <string>--interval</string>
        <string>3600</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/KULLANICI/Telegram Proje</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>10</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
</dict>
</plist>
```

Yükle:
```bash
launchctl load ~/Library/LaunchAgents/com.tvscreener.plist
```

---

## 🐛 Sorun Giderme

### OCR doğruluğu düşük

**Çözümler:**
- ✅ Ekran ölçeğini **%100** yap (macOS: Sistem Ayarları → Ekranlar)
- ✅ **Aydınlık tema** kullan (dark mode OCR için zor)
- ✅ `screen.region` koordinatlarını hassas ayarla
- ✅ Tesseract config değiştir: `config_str: "--psm 11"`
- ✅ Font boyutunu artır (TradingView ayarlarından)

### API Rate Limit

**Çözümler:**
- ✅ `--sleep 20` ile bekleme süresini artır
- ✅ `config.yaml` içinde `rate_limit_per_minute: 3` düşür
- ✅ Paralel modu (`--parallel`) kullanma
- ✅ AlphaVantage Premium üyelik al

### Telegram mesaj gitmiyor

**Kontroller:**
- ✅ Bot token doğru mu? (BotFather'dan kontrol et)
- ✅ Chat ID doğru mu? (@userinfobot ile tekrar al)
- ✅ Bot'a en az bir kez `/start` yazdın mı?
- ✅ `.env` dosyası doğru yükleniyor mu?

Test komutu:
```bash
python -c "from src.telegram_client import TelegramClient; from src.config import Config; cfg=Config.load(); TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id).send('Test mesajı')"
```

### Capture hataları

**Çözümler:**
- ✅ TradingView tam ekranda olmasın (pencere modunda)
- ✅ Region koordinatları ekran dışına taşmasın
- ✅ Screenshot izni var mı? (macOS: Sistem Ayarları → Gizlilik → Ekran Kaydı)

---

## 📁 Proje Yapısı

```
.
├── src/                    # Ana uygulama paketi
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── config.py          # Pydantic config + validation
│   ├── logger.py          # Logging setup
│   ├── exceptions.py      # Custom exception'lar
│   ├── capture.py         # Screenshot (mss)
│   ├── ocr.py            # OCR + preprocessing
│   ├── indicators.py      # RSI / Stoch RSI
│   ├── watchlist.py       # JSON watchlist manager
│   ├── telegram_client.py # Telegram API
│   └── data_source.py     # AlphaVantage API
├── config.example.yaml    # Örnek config
├── .env.example          # Örnek env dosyası
├── requirements.txt       # Python dependencies
├── README.md             # Bu dosya
├── .gitignore
└── logs/                 # Otomatik oluşur
    └── screener_YYYYMMDD.log
```

---

## 🔒 Güvenlik

- ✅ API key'leri **asla** Git'e commit etme
- ✅ `.env` ve `config.yaml` `.gitignore`'da
- ✅ `chmod 600 .env` ile dosya iznini sınırla
- ✅ Production'da `.env.example` kullanma

---

## 🧪 Test

```bash
# Tüm testler
pytest

# Coverage ile
pytest --cov=src --cov-report=html

# Belirli test
pytest tests/test_indicators.py -v
```

---

## 🚀 Deployment (DigitalOcean)

### VM Kurulumu

```bash
# 1. Ubuntu 22.04 droplet oluştur ($4/mo Basic)
# 2. SSH key ile bağlan
ssh -i ~/.ssh/key root@YOUR_IP

# 3. Proje'yi klonla
cd /root
git clone https://github.com/KULLANICI_ADI/telegram-screener.git
cd telegram-screener

# 4. Python ve dependencies kur
apt update && apt install -y python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Config ayarla (api_provider: yfinance kullan)
nano config.yaml

# 6. Systemd service kur
sudo systemctl enable /root/telegram-screener/telegram-screener.service
sudo systemctl start telegram-screener
sudo systemctl status telegram-screener
```

### macOS Otomasyonu

```bash
# LaunchAgent'lar zaten kurulu - kontrol et:
launchctl list | grep watchlist

# Manuel watchlist güncelleme:
cd '/Users/KULLANICI_ADI/Desktop/Telegram Proje'
./auto_update_watchlist.sh

# Startup agent test:
./startup_update_watchlist.sh
```

**Otomatik Çalışma:**
- 🕐 **Zamanlanmış**: 10:00, 18:00, 22:00, 00:00 (Pazartesi-Cuma)
- 🚀 **Startup**: Mac açıldığında (hafta içi, 16+ saat güncelleme yoksa)
- ☁️ **VM**: Saatte 1 scan (7/24)

---

## 🤝 Katkıda Bulunma

1. Fork'la
2. Feature branch oluştur (`git checkout -b feature/amazing`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Pull Request aç

---

## 📝 Lisans

MIT

---

## ⚖️ Yasal Uyarı

Bu proje **eğitim amaçlıdır**. TradingView kullanım koşullarını ihlal edebilir. Otomatik trading kararları için kullanılmamalıdır. Finansal kayıplardan sorumluluk kabul edilmez. Kullanım tamamen kendi sorumluluğunuzdadır.

---

## 🙏 Teşekkürler

- [pytesseract](https://github.com/madmaze/pytesseract)
- [mss](https://github.com/BoboTiG/python-mss)
- [pydantic](https://docs.pydantic.dev/)
- [tenacity](https://tenacity.readthedocs.io/)
- [tqdm](https://tqdm.github.io/)

---

**Made with ❤️ for algorithmic trading enthusiasts**

