# 🚀 TELEGRAM SCREENER - HIZLI KOMUTLAR

> **Not:** Tüm komutlar Mac terminalinden çalıştırılabilir. Alias'lar `.zshrc` dosyasına yüklenmiştir.

---

## 📋 TÜM KOMUTLAR (15 Adet)

### 🖥️ **VM Yönetimi**
```bash
tvm          # SSH ile VM'e bağlan
tvstatus     # Servis durumu göster
tvlogs       # Canlı log izle
tvrestart    # Servisi restart et
tvstop       # Servisi durdur
tvstart      # Servisi başlat
```

### 📊 **Watchlist İşlemleri**
```bash
tvlist                        # VM'deki watchlist'i göster
tvcapture                     # Screenshot al + OCR + sync
tvadd AAPL MSFT --sync        # Sembol ekle + sync
tvadd AAPL --remove --sync    # Sembol sil + sync
```

### 🔍 **Monitoring & Debug**
```bash
tvgrace      # Grace period'daki sembolleri göster
tvcompare    # Local vs VM watchlist karşılaştır
tvhealth     # Sistem sağlık kontrolü
```

### 🔄 **Git & Sync**
```bash
tvsync       # Watchlist'i VM'e push et (local → VM)
tvpush       # Manuel git commit + push
tvcd         # Proje klasörüne git
```

---

## 🎯 GÜNLÜK KULLANIM SENARYOLARI

### 📸 Scenario 1: Trading View'dan Screenshot Al
```bash
# 1. TradingView'da sembolleri seç
# 2. Screenshot al ve otomatik sync et
tvcapture
```

### ➕ Scenario 2: Manuel Sembol Ekle
```bash
# Tek sembol
tvadd AAPL --sync

# Çoklu sembol
tvadd AAPL MSFT GOOGL TSLA --sync
```

### ➖ Scenario 3: Sembol Çıkar
```bash
# Tek sembol
tvadd NOW --remove --sync

# Çoklu sembol
tvadd NOW LMT DASH --remove --sync
```

### 📊 Scenario 4: Sistem Durumu Kontrol
```bash
# Servis çalışıyor mu?
tvstatus

# Hangi semboller izleniyor?
tvlist

# Grace period'da hangileri var?
tvgrace

# Local ve VM sync mi?
tvcompare
```

### 🔍 Scenario 5: Log İzle & Debug
```bash
# Canlı log izle (Ctrl+C ile çık)
tvlogs

# Son scan ne buldu görmek için
tvstatus
```

### 🚨 Scenario 6: Acil Restart
```bash
# Sorun varsa servisi yeniden başlat
tvrestart

# Durumu kontrol et
tvstatus
```

---

## 🛠️ ADVANCED KULLANIM

### Manuel VM'ye Bağlanıp İşlem Yapma
```bash
# VM'ye bağlan
tvm

# VM'de çalıştır:
cd ~/telegram-screener

# Manuel scan
source venv/bin/activate
python -m src.main --config config.yaml scan
deactivate

# Çıkış
exit
```

### Watchlist'i Manuel Düzenle
```bash
# Proje klasörüne git
tvcd

# watchlist.json'u düzenle (VS Code ile)
code watchlist.json

# Düzenledikten sonra sync et
tvsync
```

### Git İşlemleri
```bash
# Tüm değişiklikleri push et
tvpush

# Sadece watchlist sync et (git olmadan)
tvsync
```

---

## 📊 MONİTORİNG ARAÇLARI

### Grace Period Kontrolü
```bash
tvgrace

# Örnek Çıktı:
# ⏰ Grace Period Status (5 business days):
# 🟢 DASH: 4 business days left (signaled 1x)
# 🟡 AAPL: 1 business day left (signaled 2x)
```

### Watchlist Karşılaştırma
```bash
tvcompare

# Örnek Çıktı:
# 🔍 Watchlist Comparison
# ======================
# 📱 LOCAL: 3 symbols
# 🖥️  VM: 3 symbols
# 🔄 DIFF: ✅ In sync!
```

### Sistem Sağlık Kontrolü
```bash
tvhealth

# Kontrol eder:
# - Gerekli dosyalar var mı?
# - Python environment doğru mu?
# - VM bağlantısı çalışıyor mu?
# - Git sync durumu nedir?
```

---

## 🔥 ACİL DURUM KOMUTLARI

### Servis Çalışmıyorsa
```bash
tvrestart && tvstatus
```

### Watchlist Senkronizasyon Sorunu
```bash
# VM'deki watchlist'i sıfırla ve local'i gönder
tvsync

# Hala sorun varsa VM'ye bağlan
tvm
cd ~/telegram-screener
git reset --hard
git pull
systemctl restart telegram-screener
exit
```

### Watchlist'i Tamamen Temizle
```bash
tvcd
echo "{}" > watchlist.json
tvsync
```

---

## 💡 İPUÇLARI

### ⚡ Daha Hızlı Çalışma
- `tvstatus` ile hızlıca durum kontrol et
- `tvlogs` ile real-time ne oluyor gör
- `tvcapture` kullan, manuel sync uğraşma

### 🎯 Grace Period Sistemi
- Sembol sinyal verince 5 **iş günü** (weekdays) tekrar sinyal vermez
  - Örnek: Pazartesi sinyal → Pazartesi'ye kadar grace period
  - Cumartesi/Pazar sayılmaz ❌
- `tvgrace` ile kontrol et

### 🔄 Sync Mantığı
- **Local → VM:** Her ekleme/çıkarma otomatik sync olur (`--sync` flag ile)
- **Git:** Watchlist değişiklikleri otomatik commit/push edilir
- **VM:** SSH ile otomatik `git pull` + restart yapar

### 📈 Watchlist Süresi
- Her sembol **5 iş günü** (weekdays) kalır
  - Örnek: Pazartesi eklendi → Pazartesi'ye kadar kalır
  - Cumartesi/Pazar sayılmaz ❌
- 5 iş günü sonunda otomatik temizlenir (prune)
- Manuel çıkarmak için: `tvadd SYMBOL --remove --sync`

---

## 🚀 QUICKSTART

Yeni terminal açtığında sadece bunları kullan:

```bash
# 1. Durum kontrol
tvstatus

# 2. Screenshot al
tvcapture

# 3. Manuel ekle
tvadd AAPL MSFT --sync

# 4. Log izle
tvlogs

# 5. Watchlist gör
tvlist
```

---

## 📞 DESTEK

Sorun olursa:

1. `tvstatus` - Servis çalışıyor mu?
2. `tvlogs` - Hata mesajı var mı?
3. `tvhealth` - Sistem sağlıklı mı?
4. `tvcompare` - Sync sorunu var mı?

Hala sorun varsa: `tvm` ile bağlan ve manuel kontrol et.
