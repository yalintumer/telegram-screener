# 🔄 Watchlist Auto-Sync Kurulumu

## 📦 Kurulum

### 1. Watchdog paketini yükleyin:
```bash
pip install watchdog
```

### 2. VM IP adresinizi yapılandırın:

**quick_add.py** ve **auto_sync_watchlist.py** dosyalarını açıp şu satırı düzenleyin:
```python
VM_IP = "YOUR_SERVER_IP"  # Örnek: "123.456.789.0"
```

### 3. SSH anahtarını yapılandırın (şifresiz bağlantı için):
```bash
ssh-copy-id root@YOUR_SERVER_IP
```

## 🚀 Kullanım

### Yöntem 1: Manuel Ekleme + Auto Sync

```bash
# Sembolleri ekle ve otomatik VM'e gönder
python3 quick_add.py AAPL MSFT TSLA --sync

# Sadece lokal ekle (VM'e gönderme)
python3 quick_add.py AAPL MSFT
```

### Yöntem 2: Otomatik Watchdog (Sürekli İzleme)

Terminal'i açık tutun, watchlist.json değiştiğinde otomatik sync yapar:

```bash
# Önce watchdog yükle
pip install watchdog

# Auto-sync'i başlat
python3 auto_sync_watchlist.py
```

Artık `watchlist.json` her değiştiğinde:
1. ✅ Otomatik Git commit
2. ✅ Otomatik Git push
3. ✅ VM'de otomatik `git pull`
4. ✅ VM servisini otomatik restart

### Yöntem 3: Arka Planda Çalıştır (tmux/screen ile)

```bash
# tmux ile
tmux new -s watchlist-sync
python3 auto_sync_watchlist.py
# Ctrl+B, D ile detach

# Geri dönmek için:
tmux attach -t watchlist-sync
```

## 🎯 Workflow Örnekleri

### Senaryo 1: Hızlı Ekleme
```bash
python3 quick_add.py AAPL MSFT GOOGL --sync
# ✅ 3 sembol eklendi ve VM güncellendi
```

### Senaryo 2: Watchdog ile Sürekli Sync
```bash
# Terminal 1: Auto-sync çalıştır
python3 auto_sync_watchlist.py

# Terminal 2: İstediğiniz gibi düzenleyin
python3 quick_add.py NVDA AMD
# veya
code watchlist.json  # Manuel düzenle

# Her değişiklik otomatik VM'e gider!
```

### Senaryo 3: Git ile Manuel Kontrol
```bash
python3 quick_add.py AAPL MSFT
git add watchlist.json
git commit -m "Add tech stocks"
git push

# VM'de:
ssh root@YOUR_SERVER_IP
cd ~/telegram-screener
git pull
sudo systemctl restart telegram-screener
```

## 🔧 Sorun Giderme

### SSH bağlantısı çalışmıyor:
```bash
# Test et:
ssh root@YOUR_SERVER_IP "echo OK"

# Şifresiz giriş için:
ssh-copy-id root@YOUR_SERVER_IP
```

### Watchdog yüklü değil:
```bash
pip install watchdog
# veya
pip3 install watchdog
```

### VM güncellenmiyor:
```bash
# VM'de manuel kontrol:
ssh root@YOUR_SERVER_IP
cd ~/telegram-screener
git pull
sudo systemctl status telegram-screener
```

## 📝 Notlar

- Auto-sync her 10 saniyede bir tetiklenir (spam önlemek için)
- Signal history de otomatik sync edilir
- VM servisi her sync'te otomatik restart olur
- Watchdog çalışırken terminal'i kapatmayın veya tmux kullanın

## 🎉 Özet

**En kolay yöntem:**
```bash
python3 quick_add.py AAPL MSFT --sync
```

**En güçlü yöntem:**
```bash
python3 auto_sync_watchlist.py
# Artık her değişiklik otomatik!
```
