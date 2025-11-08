# 🚀 Hızlı Başlangıç Kılavuzu

## 📋 İçindekiler
1. [İlk Kurulum](#ilk-kurulum)
2. [Günlük Kullanım](#günlük-kullanım)
3. [VM Yönetimi](#vm-yönetimi)
4. [Sorun Giderme](#sorun-giderme)

---

## 🎯 İlk Kurulum

### 1. Telegram Bot Oluştur

```bash
# 1. Telegram'da @BotFather'ı aç
# 2. /newbot komutunu gönder
# 3. Bot adı ver: "My Trading Screener"
# 4. Kullanıcı adı ver: "mytrading_screener_bot"
# 5. Token'ı kopyala: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# 6. Chat ID öğren - @userinfobot'u aç
# 7. /start gönder
# 8. Id numaranı kopyala: 987654321
```

### 2. Proje'yi İndir

```bash
cd ~/Desktop
git clone https://github.com/yalintumer/telegram-screener.git "Telegram Proje"
cd "Telegram Proje"
```

### 3. Python Kurulumu

```bash
# Virtual environment oluştur
python3 -m venv venv_clean
source venv_clean/bin/activate

# Paketleri kur
pip install -r requirements.txt
```

### 4. Config Ayarla

```bash
# config.yaml dosyasını düzenle
nano config.yaml
```

**Şunları değiştir:**
```yaml
telegram:
  bot_token: "BURAYA_BOT_TOKEN_YAPISTIR"
  chat_id: "BURAYA_CHAT_ID_YAPISTIR"

api:
  provider: yfinance  # ÜCRETSİZ - değiştirme!

screen:
  app_name: TradingView
  region: [0, 200, 165, 645]  # Ekranına göre ayarla (aşağıda açıklama var)
```

### 5. Screen Region Ayarlama

TradingView'da Screener tablosunu aç, sonra:

```bash
# Test screenshot al
python -m src.main --config config.yaml capture

# shots/ klasöründeki PNG'yi aç
# Eğer tablo tam görünmüyorsa region ayarını değiştir
```

**Koordinat sistemi:**
- `[left, top, width, height]`
- Örnek: `[0, 200, 165, 645]` = Sol üst (0,200), genişlik 165px, yükseklik 645px

---

## 💻 Günlük Kullanım

### Manuel Watchlist Güncelleme

```bash
cd ~/Desktop/Telegram\ Proje
source venv_clean/bin/activate

# Screenshot al ve listeyi güncelle
python -m src.main --config config.yaml capture --click 150,50
```

### Listeyi Görüntüle

```bash
# Mevcut semboller
python -m src.main --config config.yaml list
```

### Manuel Sembol Ekle/Çıkar

```bash
# Ekle
python -m src.main --config config.yaml add AAPL MSFT TSLA

# Çıkar
python -m src.main --config config.yaml remove AAPL

# Tümünü temizle
python -m src.main --config config.yaml clear
```

### Belirli Bir Sembolü Analiz Et

```bash
# AAPL için K/D değerlerini göster
python -m src.main --config config.yaml debug AAPL
```

### Test Telegram Mesajı

```bash
# Bot çalışıyor mu test et
python -m src.main --config config.yaml scan --dry-run
```

---

## ☁️ VM Yönetimi

### VM'e Bağlan

```bash
# SSH ile bağlan (şifre yok, key kullanıyor)
ssh -i ~/screener root@167.99.252.127
```

### VM'de Debug Menüsü Aç

```bash
# VM'e bağlandıktan sonra:
cd /telegram-screener
./deploy/test_debug.sh
```

**Menü Seçenekleri:**
```
1) Watchlist'i göster           → Hangi semboller izleniyor
2) Tek bir scan yap (dry-run)   → Test (Telegram göndermez)
3) Tek bir scan yap (gerçek)    → Gerçek tarama + Telegram
4) Belirli bir sembolü test et  → Tek sembol analizi
5) Servis loglarını göster      → Son 50 log satırı
6) Servis durumunu göster       → Sistem durumu
7) Test Telegram mesajı         → Bot çalışıyor mu?
8) Config dosyasını göster      → Ayarlar
9) Çıkış
```

### Servis Komutları (VM'de)

```bash
# Servis durumu
systemctl status telegram-screener

# Servisi durdur
systemctl stop telegram-screener

# Servisi başlat
systemctl start telegram-screener

# Servisi yeniden başlat
systemctl restart telegram-screener

# Son logları göster (canlı)
journalctl -u telegram-screener -f

# Son 100 log satırı
journalctl -u telegram-screener -n 100
```

### Kod Güncelle (VM'de)

```bash
# Yeni kod çek
cd /root/telegram-screener
git pull

# Servisi yeniden başlat
systemctl restart telegram-screener

# Durumu kontrol et
systemctl status telegram-screener
```

### Watchlist'i Mac'ten VM'e Gönder

```bash
# Mac'te bu scripti çalıştır:
cd ~/Desktop/Telegram\ Proje
./auto_update_watchlist.sh
```

**Bu script şunları yapar:**
1. ✅ TradingView'dan screenshot alır
2. ✅ OCR ile sembolleri okur
3. ✅ Watchlist'i günceller
4. ✅ VM'e yükler
5. ✅ VM'deki servisi yeniden başlatır

---

## 🔧 Sorun Giderme

### "TradingView penceresi bulunamadı"

```bash
# TradingView'ı aç
open -a TradingView

# 5 saniye bekle, sonra tekrar dene
python -m src.main capture --click 150,50
```

### "Permission denied" (SSH)

```bash
# SSH key yetkisini düzelt
chmod 600 ~/screener

# Tekrar dene
ssh -i ~/screener root@167.99.252.127
```

### "ModuleNotFoundError"

```bash
# Virtual environment'ı aktif et
cd ~/Desktop/Telegram\ Proje
source venv_clean/bin/activate

# Paketleri yeniden kur
pip install -r requirements.txt
```

### "Grace period active"

Bu normal! Bir sembol sinyal verdikten sonra 5 gün tekrar eklenemez.

```bash
# Hangi semboller grace period'da görmek için:
cat signal_history.json
```

### VM'de "Service failed"

```bash
# VM'e bağlan
ssh -i ~/screener root@167.99.252.127

# Hata loglarını göster
journalctl -u telegram-screener -n 50

# Config'i kontrol et
cat /root/telegram-screener/config.yaml

# Servisi yeniden başlat
systemctl restart telegram-screener
```

### Telegram mesaj gitmiyor

```bash
# Bot token ve chat ID'yi kontrol et
cat config.yaml | grep -A 2 telegram

# Test mesajı gönder
python -m src.main --config config.yaml scan
```

---

## 📱 LaunchAgent Yönetimi (macOS)

### Durumu Kontrol Et

```bash
# Hangi agent'lar çalışıyor?
launchctl list | grep watchlist
```

Çıktı:
```
-    0    com.yalintumer.watchlist-updater  ← Zamanlanmış (10,18,22,00)
-    0    com.yalintumer.watchlist-startup   ← Startup kontrolü
```

### Agent'ı Durdur/Başlat

```bash
# Durdur
launchctl unload ~/Library/LaunchAgents/com.yalintumer.watchlist-updater.plist

# Başlat
launchctl load ~/Library/LaunchAgents/com.yalintumer.watchlist-updater.plist
```

### Log Dosyalarını Göster

```bash
cd ~/Desktop/Telegram\ Proje

# Zamanlanmış güncellemeler
tail -50 logs/watchlist_update.log

# Startup güncellemeleri
tail -50 logs/startup_update.log

# Hata logları
tail -50 logs/watchlist_update_error.log
```

---

## 🎯 Günlük Rutin

### Sabah (Otomatik)

✅ Mac açıldığında `startup_update_watchlist.sh` çalışır  
✅ Eğer 16+ saat güncelleme yoksa TradingView'ı açar  
✅ Watchlist'i günceller ve VM'e gönderir

### Gün İçinde (Otomatik)

✅ Saat 10:00, 18:00, 22:00, 00:00'da otomatik güncelleme  
✅ VM her saat başı tarama yapar  
✅ Sinyal bulduğunda Telegram'a bildirim gönderir

### Manuel Kontrol (İsteğe Bağlı)

```bash
# 1. Liste kontrolü
ssh -i ~/screener root@167.99.252.127
./deploy/test_debug.sh
# Seçenek 1: Watchlist'i göster

# 2. Log kontrolü
journalctl -u telegram-screener -n 20

# 3. Çıkış
exit
```

---

## 📞 Hızlı Komut Referansı

### Mac Komutları

```bash
# Watchlist güncelle
cd ~/Desktop/Telegram\ Proje && ./auto_update_watchlist.sh

# Listeyi göster
python -m src.main list

# Sembol ekle
python -m src.main add AAPL

# Debug
python -m src.main debug AAPL
```

### VM Komutları

```bash
# Bağlan
ssh -i ~/screener root@167.99.252.127

# Debug menü
cd /root/telegram-screener && ./deploy/test_debug.sh

# Loglar
journalctl -u telegram-screener -f

# Restart
systemctl restart telegram-screener

# Çıkış
exit
```

---

## ✅ Sistem Sağlığı Kontrolü

Günde 1 kez şunları kontrol et:

```bash
# 1. VM çalışıyor mu?
ssh -i ~/screener root@167.99.252.127 "systemctl status telegram-screener"

# 2. Son tarama ne zaman?
ssh -i ~/screener root@167.99.252.127 "journalctl -u telegram-screener -n 5"

# 3. Mac agent'ları çalışıyor mu?
launchctl list | grep watchlist

# 4. Watchlist kaç sembol?
python -m src.main list
```

Hepsi ✅ ise sistem sağlıklı! 🎉

---

## 🆘 Acil Durum

Hiçbir şey çalışmıyorsa:

```bash
# 1. Mac'i yeniden başlat
sudo reboot

# 2. VM'i yeniden başlat
ssh -i ~/screener root@167.99.252.127 "sudo reboot"

# 3. 2 dakika bekle

# 4. Tekrar test et
cd ~/Desktop/Telegram\ Proje
./auto_update_watchlist.sh
```

---

**🎓 İyi taramalar!** 📈
