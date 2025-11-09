# 🎨 Telegram Screener - Modern CLI Kullanımı

> **� Not:** Bu proje artık beautiful UI ve alias sistemi ile modernize edildi!

## 🚀 Hızlı Başlangıç

Tüm komutları görmek için:
```bash
tvhelp
```

## 🎨 Local Komutlar (Beautiful UI)

### Watchlist Yönetimi
```bash
# Watchlist'i göster (güzel tablo ile)
tvlist

# Sembol ekle
tvadd AAPL MSFT TSLA

# Sembol çıkar
tvremove AAPL

# Tüm watchlist'i temizle (onay ister)
tvclear
```

### Tarama ve Analiz
```bash
# Tarama yap (progress bar ile)
tvscan

# Debug bilgisi göster
tvdebug AAPL

# Sürekli mod (1 saatte bir tarama)
tvrun
```

### Ekran Görüntüsü
```bash
# Ekran görüntüsü al ve OCR yap (sadece Mac'te)
tvcapture
```

## 🌐 VM Yönetimi

### Service Kontrol
```bash
# Service durumu
tvstatus

# Service başlat
tvstart

# Service durdur
tvstop

# Service yeniden başlat
tvrestart

# Log görüntüle (son 50 satır)
tvlogs

# Canlı log takibi
tvlogs-live

# VM'e SSH bağlan
tvm
```

### System Health Check
```bash
# Kapsamlı sistem kontrolü
tvhealth
```

Kontrol edilen:
- ✅ Local watchlist durumu
- ✅ Config dosyası
- ✅ Signal history
- ✅ VM service durumu
- ✅ VM watchlist karşılaştırma
- ✅ Git durumu

## 🔄 Sync Komutları

### Otomatik Sync
```bash
# Pull + Push + VM güncelle + restart
tvsync

# Commit + Push + VM güncelle + restart
tvpush "commit message"

# Sadece git pull
tvpull

# Local ve VM watchlist'i karşılaştır
tvcompare
```

### Manuel Sync Workflow
```bash
# 1. Sembolleri ekle
tvadd AAPL MSFT

# 2. Commit ve push
git add watchlist.json
git commit -m "Add tech stocks"
git push

# 3. VM'i güncelle
ssh root@167.99.252.127 "cd ~/telegram-screener && git pull && sudo systemctl restart telegram-screener.service"

# Veya tek komutla:
tvsync
```

## 🔧 Utilities

```bash
# Proje klasörüne git
tvcd

# Yardım mesajı
tvhelp
```

## 🎯 Workflow Örnekleri

### Senaryo 1: Hızlı Sembol Ekleme ve Tarama
```bash
tvadd AAPL MSFT GOOGL
tvscan
```

### Senaryo 2: VM'i Güncelleme
```bash
# Lokal değişikliklerden sonra:
tvpush "Add new tech stocks"

# VM durumunu kontrol:
tvstatus
tvhealth
```

### Senaryo 3: Debug ve Analiz
```bash
# Watchlist'i göster
tvlist

# Belirli sembolü debug et
tvdebug AAPL

# Log'ları izle
tvlogs-live
```

### Senaryo 4: Sürekli İzleme
```bash
# Local'de sürekli mod
tvrun

# VM'de zaten çalışıyor (1 saatte bir scan)
tvstatus
```

## 📦 Kurulum (Alias Sistemi)

Alias'lar zaten `.zshrc` dosyasına eklendi. Yeni bir terminal açtığınızda otomatik yüklenir.

Manuel yükleme için:
```bash
source ~/.zshrc
```

## 🔧 Sorun Giderme

### Komutlar çalışmıyor:
```bash
# Config'i yeniden yükle
source ~/.zshrc

# Alias'ları kontrol et
alias | grep tv
```

### VM bağlantısı çalışmıyor:
```bash
# SSH test et
ssh root@167.99.252.127 "echo OK"

# Şifresiz giriş için (eğer yoksa):
ssh-copy-id root@167.99.252.127
```

### Service çalışmıyor:
```bash
# Durumu kontrol et
tvstatus

# Log'ları incele
tvlogs

# Yeniden başlat
tvrestart

# Kapsamlı health check
tvhealth
```

## 🎨 UI Özellikleri

### Güzel Tablolar
- 📊 Color-coded age indicators (yeşil < 2 gün, sarı 2-4 gün, kırmızı >= 4 gün)
- 📋 Bordered headers
- 🎯 Clear symbol listing

### Progress Bars
- ⏳ Spinners ile canlı progress
- 📈 Yüzdelik gösterge
- ⏱️ Tahmini kalan süre

### Status Messages
- ✅ Success (yeşil)
- ❌ Error (kırmızı)
- ⚠️ Warning (sarı)
- ℹ️ Info (mavi)

### Panels
- 📊 İstatistik panelleri
- 🔍 Debug bilgileri
- ⚙️ Konfigürasyon bilgileri

## 📝 Environment Variables

Alias sistemi otomatik şu değişkenleri kullanır:
```bash
TV_PROJECT="$HOME/Desktop/Telegram Proje"
TV_VM_IP="167.99.252.127"
TV_VM_USER="root"
TV_VM_PATH="~/telegram-screener"
```

## 🎉 Özet

**En sık kullanılan komutlar:**
```bash
tvlist          # Watchlist'i gör
tvadd AAPL      # Sembol ekle
tvscan          # Tarama yap
tvhealth        # System check
tvstatus        # VM durumu
tvsync          # Sync yap
```

**Yardım:**
```bash
tvhelp          # Tüm komutlar
```

## 🔗 Diğer Dökümanlar

- `QUICKSTART.md` - Hızlı başlangıç rehberi
- `README.md` - Proje genel bilgisi
- `CHEATSHEET.txt` - Komut referansı
