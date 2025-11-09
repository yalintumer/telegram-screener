# 🚀 TELEGRAM SCREENER - KOMUT KILAVUZU

## 📡 VM BAĞLANTI

```bash
# SSH ile VM'ye bağlan
ssh -i ~/screener root@167.99.252.127

# Hızlı komutlar (tek satır)
ssh root@167.99.252.127 "cd ~/telegram-screener && systemctl status telegram-screener --no-pager"
ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json"
```

## 📸 SCREENSHOT & WATCHLIST YÖNETİMİ

### Manuel Screenshot + Sync
```bash
cd "/Users/yalintumer/Desktop/Telegram Proje" && ./capture_and_sync.sh
```

### Manuel Sembol Ekleme/Çıkarma
```bash
# Ekle
python3 quick_add.py AAPL MSFT GOOGL --sync

# Çıkar
python3 quick_add.py --remove NOW LMT --sync

# Sadece sync (değişiklik yapmadan mevcut durumu gönder)
python3 quick_add.py --sync-only
```

### Watchlist Görüntüle
```bash
# Lokal
cat watchlist.json | python3 -c "import sys,json; [print(k) for k in sorted(json.load(sys.stdin).keys())]"

# VM'de
ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json | python3 -c \"import sys,json; [print(k) for k in sorted(json.load(sys.stdin).keys())]\""
```

## 🔍 SERVİS YÖNETİMİ (VM'de)

```bash
# Servis durumu
sudo systemctl status telegram-screener

# Log izle (canlı)
sudo journalctl -u telegram-screener -f

# Son 50 log satırı
sudo journalctl -u telegram-screener -n 50

# Servisi restart
sudo systemctl restart telegram-screener

# Servisi durdur
sudo systemctl stop telegram-screener

# Servisi başlat
sudo systemctl start telegram-screener
```

## 🔧 MANUEL SCAN (VM'de)

```bash
# Test debug script
cd ~/telegram-screener && ./deploy/test_debug.sh

# Manuel scan (venv ile)
cd ~/telegram-screener
source venv/bin/activate
python -m src.main --config config.yaml scan
deactivate

# Dry-run (değişiklik yapmadan test)
source venv/bin/activate
python -m src.main --config config.yaml scan --dry-run
deactivate
```

## 📊 DEBUGGİNG & MONİTORİNG

```bash
# Watchlist'e sembol ekle (VM)
cd ~/telegram-screener
source venv/bin/activate
python -m src.main --config config.yaml add AAPL MSFT
deactivate

# Watchlist göster (VM)
source venv/bin/activate
python -m src.main --config config.yaml list
deactivate

# Tek sembol debug (VM)
source venv/bin/activate
python -m src.main --config config.yaml debug AAPL
deactivate
```

## 🔄 GİT SYNC

```bash
# Lokal değişiklikleri VM'ye gönder
cd "/Users/yalintumer/Desktop/Telegram Proje"
git add .
git commit -m "Update"
git push

# VM'de güncelle
ssh root@167.99.252.127 "cd ~/telegram-screener && git pull && sudo systemctl restart telegram-screener"

# Tek satırda (Mac'den)
cd "/Users/yalintumer/Desktop/Telegram Proje" && git add . && git commit -m "Update" && git push && ssh root@167.99.252.127 "cd ~/telegram-screener && git pull && sudo systemctl restart telegram-screener"
```

## 💡 HIZLI ERİŞİM ALİASLAR

Mac'inizde `.zshrc` veya `.bashrc` dosyanıza ekleyin:

```bash
# Telegram Screener Aliases - VM Management
alias tvm='ssh root@167.99.252.127'
alias tvstatus='ssh root@167.99.252.127 "systemctl status telegram-screener --no-pager"'
alias tvlogs='ssh root@167.99.252.127 "journalctl -u telegram-screener -f"'
alias tvrestart='ssh root@167.99.252.127 "systemctl restart telegram-screener"'
alias tvstop='ssh root@167.99.252.127 "systemctl stop telegram-screener"'
alias tvstart='ssh root@167.99.252.127 "systemctl start telegram-screener"'

# Watchlist Operations
alias tvlist='ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json"'
alias tvcapture='cd "/Users/yalintumer/Desktop/Telegram Proje" && ./capture_and_sync.sh'
alias tvadd='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_add.py'

# Monitoring & Debug
alias tvgrace='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 check_grace_periods.py'
alias tvcompare='cd "/Users/yalintumer/Desktop/Telegram Proje" && ./compare_watchlists.sh'
alias tvhealth='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_health_check.py'

# Git & Sync
alias tvpush='cd "/Users/yalintumer/Desktop/Telegram Proje" && git add . && git commit -m "Update" && git push'
alias tvsync='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_add.py --sync-only'
alias tvcd='cd "/Users/yalintumer/Desktop/Telegram Proje"'
```

Sonra:
```bash
source ~/.zshrc

# Artık kullanabilirsiniz:
# VM Yönetimi
tvm             # SSH ile VM'e bağlan
tvstatus        # Servis durumu
tvlogs          # Canlı log izle
tvrestart       # Servisi restart et
tvstop          # Servisi durdur
tvstart         # Servisi başlat

# Watchlist İşlemleri
tvlist          # VM'deki watchlist göster
tvcapture       # Screenshot al + sync
tvadd AAPL MSFT --sync      # Sembol ekle + sync
tvadd AAPL --remove --sync  # Sembol sil + sync

# Monitoring & Debug
tvgrace         # Grace period'daki sembolleri göster
tvcompare       # Local vs VM karşılaştır
tvhealth        # Sistem sağlık kontrolü

# Git & Sync
tvpush          # Git commit + push
tvsync          # Sadece sync (watchlist'i VM'e gönder)
tvcd            # Proje klasörüne git
```

## 📝 HIZLI TESTLERİ

```bash
# Sistem sağlık kontrolü (Mac)
cd "/Users/yalintumer/Desktop/Telegram Proje"
python3 quick_health_check.py

# Grace period kontrolü (Mac)
cd "/Users/yalintumer/Desktop/Telegram Proje"
python3 check_grace_periods.py

# Local vs VM karşılaştır (Mac)
cd "/Users/yalintumer/Desktop/Telegram Proje"
./compare_watchlists.sh

# VM bağlantı testi (Mac)
ssh root@167.99.252.127 "echo OK"

# Watchlist sayısı (lokal)
cat watchlist.json | grep -c "added"

# Watchlist sayısı (VM)
ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json | grep -c 'added'"
```

## � MONİTORİNG ARAÇLARI

### Grace Period Kontrolü
Hangi semboller grace period'da (5 iş günü sinyal gönderilmez):

```bash
cd "/Users/yalintumer/Desktop/Telegram Proje"
python3 check_grace_periods.py

# Çıktı örneği:
# ⏰ Grace Period Status (5 business days):
# 🟢 DASH: 5 business days left (signaled 1x)
```

### Watchlist Karşılaştırma
Local ve VM'deki watchlist'leri karşılaştır:

```bash
cd "/Users/yalintumer/Desktop/Telegram Proje"
./compare_watchlists.sh

# Çıktı örneği:
# 🔍 Watchlist Comparison
# ======================
# 📱 LOCAL:
# AAPL
# CRH
# LMT
# 
# 🖥️  VM:
# AAPL
# CRH
# LMT
# 
# 🔄 DIFF:
# ✅ In sync!
```

## �🔥 ACİL DURUM

```bash
# Servisi acil restart (sorun varsa)
ssh root@167.99.252.127 "systemctl restart telegram-screener && systemctl status telegram-screener"

# Watchlist'i temizle (lokal)
echo "{}" > watchlist.json
python3 quick_add.py --sync-only

# Log'ları temizle (VM)
ssh root@167.99.252.127 "sudo journalctl --vacuum-time=1d"

# Git'i hard reset (dikkat!)
git reset --hard origin/main
```

## 📈 PERFORMANS

```bash
# Kaç sembol tarıyor? (VM)
ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json | grep -c 'added'"

# Son scan ne zaman? (VM log)
ssh root@167.99.252.127 "journalctl -u telegram-screener -n 1 --no-pager"

# Disk kullanımı (VM)
ssh root@167.99.252.127 "df -h"

# Memory kullanımı (VM)
ssh root@167.99.252.127 "free -h"
```

---

## 🎯 EN ÇOK KULLANACAKLARINIZ

```bash
# 1. Screenshot al ve gönder
./capture_and_sync.sh
# VEYA: tvcapture

# 2. Manuel sembol ekle
python3 quick_add.py AAPL MSFT --sync
# VEYA: tvadd AAPL MSFT --sync

# 3. Sembol çıkar
python3 quick_add.py --remove AAPL --sync
# VEYA: tvadd AAPL --remove --sync

# 4. VM durumu kontrol
ssh root@167.99.252.127 "systemctl status telegram-screener"
# VEYA: tvstatus

# 5. Log izle
ssh root@167.99.252.127 "journalctl -u telegram-screener -f"
# VEYA: tvlogs

# 6. Grace period kontrol
python3 check_grace_periods.py
# VEYA: tvgrace

# 7. Local vs VM karşılaştır
./compare_watchlists.sh
# VEYA: tvcompare

# 8. Servisi restart
ssh root@167.99.252.127 "systemctl restart telegram-screener"
# VEYA: tvrestart
```
