# 🍎 macOS Kurulum Rehberi

## Hızlı Başlangıç (macOS için Özel)

### 1. Kurulum
```bash
cd ~/Desktop/Telegram\ Proje  # veya projenizin yolu
source venv/bin/activate

# Eğer venv yoksa:
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
```

### 2. Yapılandırma
```bash
# .env dosyasını kontrol edin
cat .env

# Telegram bilgilerinizi ekleyin
nano .env
```

Gerekli bilgiler:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Test Edin
```bash
# Manuel test
python -m src.main add AAPL MSFT GOOGL
python -m src.main list
python -m src.main status

# Dry run tarama
python -m src.main scan --dry-run
```

### 4. Servis Olarak Çalıştırın (Opsiyonel)

macOS'ta arka planda sürekli çalışması için launchd kullanılır:

```bash
# Servisi yükle
python deploy_macos.py install

# Servisi başlat
python deploy_macos.py start

# Durumu kontrol et
python deploy_macos.py status

# Logları görüntüle
python deploy_macos.py logs

# Servisi durdur
python deploy_macos.py stop

# Servisi kaldır
python deploy_macos.py uninstall
```

### 5. Manuel Çalıştırma (Önerilen - Mac için)

Servis yerine manuel çalıştırma daha pratik olabilir:

```bash
# Terminal'de çalıştır (sürekli mod)
python -m src.main run --interval 3600

# Veya sadece tarama
python -m src.main scan

# Capture + scan
python -m src.main capture
python -m src.main scan
```

## 🎮 Günlük Kullanım

### Watchlist Yönetimi
```bash
# Sembol ekle
python -m src.main add AAPL MSFT TSLA

# Listeyi göster
python -m src.main list

# Sembol çıkar
python -m src.main remove AAPL

# Tümünü temizle
python -m src.main clear
```

### Tarama
```bash
# Normal tarama
python -m src.main scan

# Hızlı tarama (paralel)
python -m src.main scan --parallel

# Dry run (mesaj gönderme)
python -m src.main scan --dry-run
```

### Capture (TradingView'dan)
```bash
# Ekran görüntüsü al ve OCR
python -m src.main capture

# Belirli koordinata tıklayarak
python -m src.main capture --click 150,50
```

### Monitoring
```bash
# Sistem durumu
python -m src.main status

# Belirli sembolü debug et
python -m src.main debug AAPL
```

## 📊 Log Yönetimi

### Log Konumları
```bash
# Uygulama logları
tail -f logs/screener_$(date +%Y%m%d).log

# Launchd logları (servis kullanıyorsanız)
tail -f logs/launchd.out.log
tail -f logs/launchd.err.log
```

### Logları Temizle
```bash
# Eski logları sil (7 günden eski)
find logs -name "screener_*.log" -mtime +7 -delete
```

## ⚙️ Yapılandırma

### Ekran Bölgesi Ayarlama (Capture için)
`config.yaml` dosyasını düzenleyin:

```yaml
screen:
  region: [0, 200, 165, 645]  # [left, top, width, height]
  app_name: "TradingView"
```

Koordinatları bulmak için:
1. TradingView screener'ı açın
2. Sembollerin göründüğü bölgeyi ölçün
3. macOS Screenshot uygulamasını kullanın (Cmd+Shift+4)

### Grace Period Ayarlama
`src/watchlist.py` dosyasında:

```python
GRACE_PERIOD_DAYS = 5  # Sinyal sonrası bekleme süresi (iş günü)
```

## 🔧 Sorun Giderme

### "No module named 'src'" Hatası
```bash
# Doğru dizinde olduğunuzdan emin olun
cd /Users/yalintumer/Desktop/Telegram\ Proje

# Virtual environment aktif mi?
source venv/bin/activate
```

### Tesseract OCR Hatası
```bash
# Tesseract yüklü mü kontrol edin
tesseract --version

# Yüklü değilse:
brew install tesseract
```

### Telegram Mesaj Gönderilmiyor
```bash
# Bot token ve chat ID'yi kontrol edin
cat .env

# Test edin
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

### Capture Çalışmıyor
```bash
# Ekran kayıt izinlerini kontrol edin
# System Preferences > Security & Privacy > Privacy > Screen Recording
# Terminal'i ekleyin

# Dry run ile test edin
python -m src.main capture --dry-run
```

## 🎯 Best Practices (macOS)

### 1. Manuel Çalıştırma Önerilir
macOS'ta servis yerine terminal'de manuel çalıştırma daha stabil:

```bash
# iTerm2 veya Terminal'de
cd /Users/yalintumer/Desktop/Telegram\ Proje
source venv/bin/activate
python -m src.main run --interval 3600
```

### 2. Screen Saver'ı Devre Dışı Bırakın
Capture çalışırken ekran kilitlenmemeli:
- System Preferences > Desktop & Screen Saver
- Screen Saver: Never

### 3. Energy Saver Ayarları
Mac'in uyku moduna geçmesini engelleyin:
- System Preferences > Energy Saver
- Prevent computer from sleeping automatically: ON

### 4. Cron Job Alternatifi
Saatlik tarama için cron kullanabilirsiniz:

```bash
# Crontab'ı düzenle
crontab -e

# Her saat başı çalıştır
0 * * * * cd /Users/yalintumer/Desktop/Telegram\ Proje && /Users/yalintumer/Desktop/Telegram\ Proje/venv/bin/python -m src.main scan >> logs/cron.log 2>&1
```

## 📱 Telegram Bot Kurulumu

1. **Bot Oluştur**:
   - Telegram'da [@BotFather](https://t.me/BotFather) ile konuşun
   - `/newbot` komutunu kullanın
   - Bot token'ı kopyalayın

2. **Chat ID Bul**:
   - [@userinfobot](https://t.me/userinfobot) ile konuşun
   - Chat ID'nizi alın

3. **Yapılandır**:
   ```bash
   nano .env
   # TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ekleyin
   ```

## 🚀 Güncellemeler

```bash
cd /Users/yalintumer/Desktop/Telegram\ Proje

# Servisi durdur (eğer çalışıyorsa)
python deploy_macos.py stop

# Kodu güncelle
git pull

# Bağımlılıkları güncelle
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Servisi başlat
python deploy_macos.py start

# Veya manuel çalıştır
python -m src.main run --interval 3600
```

## 💡 İpuçları

1. **iTerm2 Kullanın**: Terminal'den daha iyi bir deneyim
2. **Tmux/Screen Kullanın**: Arka planda çalıştırmak için
3. **Alfred Workflow**: Hızlı komutlar için Alfred workflow oluşturun
4. **Notification Center**: macOS bildirimlerini etkinleştirin

## 🆘 Destek

Sorun yaşarsanız:
1. `python -m src.main status` - Sistem durumunu kontrol edin
2. `logs/` klasöründeki logları inceleyin
3. GitHub Issues açın
4. `python -m src.main debug SEMBOL` ile test edin
