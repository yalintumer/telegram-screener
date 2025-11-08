# 🚀 Oracle Cloud Deployment - Hızlı Başlangıç

## Ne İçeriyor?

Bu klasörde Oracle Cloud'a deploy için gereken tüm dosyalar var:

```
deploy/
├── ORACLE_DEPLOYMENT.md       # Detaylı kurulum rehberi (buradan başla!)
├── oracle_setup.sh            # VM'de ilk kurulum script'i
├── deploy.sh                  # GitHub'dan otomatik deploy
├── update_watchlist_local.sh  # Mac'te watchlist güncelleme
└── config.production.yaml     # Sunucu config dosyası
```

## ⚡ Hızlı Kurulum (5 Adım)

### 1. Oracle Cloud Hesabı Aç
- https://www.oracle.com/cloud/free/
- Email + kredi kartı (ücret yok, sadece doğrulama)

### 2. VM Instance Oluştur
- Compute → Instances → Create Instance
- Ubuntu 22.04, VM.Standard.E2.1.Micro (Always Free)
- SSH key indir, Public IP not et

### 3. SSH Bağlan
```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@PUBLIC_IP
```

### 4. Projeyi Kur
```bash
# VM'de
sudo apt update && sudo apt install -y git python3 python3-pip python3-venv
git clone https://github.com/YOUR_USERNAME/telegram-screener.git
cd telegram-screener
bash deploy/deploy.sh
```

### 5. Watchlist'i Güncelle (Mac'te)
```bash
# Mac'te
cd "/Users/yalintumer/Desktop/Telegram Proje"
bash deploy/update_watchlist_local.sh

# Upload to VM
scp -i ~/Downloads/ssh-key-*.key watchlist.json ubuntu@PUBLIC_IP:~/telegram-screener/

# Restart service (SSH'da)
sudo systemctl restart telegram-screener
```

## ✅ Hazır!

Sistem şimdi 7/24 çalışıyor ve her 8 saatte bir:
- Watchlist'teki sembolleri tarıyor
- Stochastic RSI hesaplıyor
- Buy sinyali bulursa Telegram'a gönderiyor

## 📚 Daha Fazla Bilgi

**ORACLE_DEPLOYMENT.md** dosyasını okuyun - her şey orada!

## 💡 İpuçları

- **Watchlist'i günde 1-2 kez güncelleyin** (Mac'ten)
- **Logları izleyin**: `sudo journalctl -u telegram-screener -f`
- **Test edin**: `python -m src.main scan --dry-run`

## 🆘 Yardım

Sorun mu var?
1. `sudo systemctl status telegram-screener` - servis durumu
2. `sudo journalctl -u telegram-screener -n 50` - son loglar
3. ORACLE_DEPLOYMENT.md → "Sorun Giderme" bölümü

---

**Başarılar! 🎉**
