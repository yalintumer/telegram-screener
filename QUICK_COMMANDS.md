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
# Telegram Screener Aliases
alias tvm='ssh root@167.99.252.127'
alias tvstatus='ssh root@167.99.252.127 "systemctl status telegram-screener --no-pager"'
alias tvlogs='ssh root@167.99.252.127 "journalctl -u telegram-screener -f"'
alias tvrestart='ssh root@167.99.252.127 "systemctl restart telegram-screener"'
alias tvlist='ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json"'
alias tvcapture='cd "/Users/yalintumer/Desktop/Telegram Proje" && ./capture_and_sync.sh'
alias tvadd='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_add.py'
alias tvcd='cd "/Users/yalintumer/Desktop/Telegram Proje"'
```

Sonra:
```bash
source ~/.zshrc

# Artık kullanabilirsiniz:
tvstatus        # Servis durumu
tvlogs          # Log izle
tvrestart       # Restart
tvlist          # Watchlist göster
tvcapture       # Screenshot al ve sync et
tvadd AAPL --sync  # Sembol ekle
```

## 📝 HIZLI TESTLERİ

```bash
# Sistem sağlık kontrolü (Mac)
cd "/Users/yalintumer/Desktop/Telegram Proje"
python3 quick_health_check.py

# VM bağlantı testi (Mac)
ssh root@167.99.252.127 "echo OK"

# Watchlist sayısı (lokal)
cat watchlist.json | grep -c "added"

# Watchlist sayısı (VM)
ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json | grep -c 'added'"
```

## 🔥 ACİL DURUM

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

# 2. Manuel sembol ekle
python3 quick_add.py AAPL MSFT --sync

# 3. Sembol çıkar
python3 quick_add.py --remove AAPL --sync

# 4. VM durumu kontrol
ssh root@167.99.252.127 "systemctl status telegram-screener"

# 5. Log izle
ssh root@167.99.252.127 "journalctl -u telegram-screener -f"
```
