# 🚀 Oracle Cloud Deployment Guide

## 📋 Genel Bakış

Bu proje Oracle Cloud'da 7/24 çalışacak. OCR ekran görüntüsü sunucuda çalışmadığı için **hybrid yaklaşım** kullanıyoruz:

- **Mac (yerel)**: TradingView'dan ticker'ları OCR ile çek → watchlist.json güncelle
- **Oracle Cloud VM**: Watchlist'i tara → Buy sinyalleri bul → Telegram'a gönder

## 🎯 Avantajlar

✅ **Tamamen bedava** - Sonsuza kadar  
✅ **7/24 çalışır** - Hiç kapanmaz  
✅ **Otomatik restart** - Hata durumunda kendini düzeltir  
✅ **Günlük 3 tarama** - 8 saatte bir otomatik  

---

## 1️⃣ Oracle Cloud Hesap Oluşturma

1. **https://www.oracle.com/cloud/free/** adresine git
2. "Start for free" butonuna tıkla
3. Bilgilerini gir:
   - Email
   - Ülke: Turkey
   - **Kredi kartı gerekli** (sadece doğrulama, ücret yok)
4. Email'i onayla
5. Cloud Console'a giriş yap

---

## 2️⃣ VM Instance Oluşturma

### Adımlar:

1. **Compute → Instances** bölümüne git
2. **"Create Instance"** tıkla
3. Ayarlar:
   - **Name**: `telegram-screener`
   - **Image**: Ubuntu 22.04 (Oracle Linux de olur)
   - **Shape**: `VM.Standard.E2.1.Micro` (Always Free)
   - **Network**: Default VCN kullan
   - **Public IP**: Evet (SSH için gerekli)
   - **SSH Keys**: Generate a new key pair → Private key'i indir (`.pem` dosyası)

4. **Create** tıkla (2-3 dakika sürer)

5. Instance'ın **Public IP** adresini not et (örn: `123.456.78.90`)

---

## 3️⃣ SSH Bağlantısı

### Mac/Linux:

```bash
# SSH key dosyasının izinlerini düzelt
chmod 600 ~/Downloads/ssh-key-*.key

# VM'e bağlan
ssh -i ~/Downloads/ssh-key-*.key ubuntu@123.456.78.90
# veya Oracle Linux kullandıysanız:
ssh -i ~/Downloads/ssh-key-*.key opc@123.456.78.90
```

İlk bağlantıda "Are you sure?" sorusuna `yes` yaz.

---

## 4️⃣ VM Kurulumu

SSH bağlantısı kurduktan sonra:

### A) Setup Script'i İndir ve Çalıştır

```bash
# Script'i oluştur
cat > setup.sh << 'EOF'
# (oracle_setup.sh içeriğini buraya yapıştır)
EOF

# Çalıştırılabilir yap
chmod +x setup.sh

# Çalıştır
./setup.sh
```

**VEYA** projeyi doğrudan GitHub'dan çek (önerilen):

### B) GitHub Üzerinden Deploy (Daha Kolay)

```bash
# Projeyi GitHub'a push et (yerel Mac'inizde)
cd "/Users/yalintumer/Desktop/Telegram Proje"
git init
git add .
git commit -m "Initial commit for Oracle Cloud"
git remote add origin https://github.com/KULLANICI_ADINIZ/telegram-screener.git
git push -u origin main
```

```bash
# VM'de projeyi çek
git clone https://github.com/KULLANICI_ADINIZ/telegram-screener.git
cd telegram-screener
bash deploy/deploy.sh
```

---

## 5️⃣ Manuel Watchlist Güncelleme

Oracle Cloud VM'de ekran görüntüsü çekemediğiniz için **watchlist'i Mac'inizden güncelleyeceksiniz**:

### Mac'inizde (her gün veya haftada bir):

```bash
cd "/Users/yalintumer/Desktop/Telegram Proje"
bash deploy/update_watchlist_local.sh

# Çıktıyı kopyala veya dosyayı upload et:
scp -i ~/Downloads/ssh-key-*.key watchlist.json ubuntu@123.456.78.90:~/telegram-screener/

# Service'i restart et (SSH ile)
ssh -i ~/Downloads/ssh-key-*.key ubuntu@123.456.78.90
sudo systemctl restart telegram-screener
```

---

## 6️⃣ Servis Yönetimi

```bash
# Durumu kontrol et
sudo systemctl status telegram-screener

# Başlat
sudo systemctl start telegram-screener

# Durdur
sudo systemctl stop telegram-screener

# Restart
sudo systemctl restart telegram-screener

# Logları izle (canlı)
sudo journalctl -u telegram-screener -f

# Son 100 satır log
sudo journalctl -u telegram-screener -n 100
```

---

## 7️⃣ Güncelleme Yapmak

```bash
# VM'de
cd ~/telegram-screener
git pull
sudo systemctl restart telegram-screener
```

---

## 🔧 Sorun Giderme

### Servis başlamıyor:

```bash
# Logları kontrol et
sudo journalctl -u telegram-screener -n 50

# Manuel test
cd ~/telegram-screener
source venv/bin/activate
python -m src.main --config config.yaml scan --dry-run
```

### Bağlantı kesilmiş:

```bash
# VM'in public IP'si değişmiş olabilir (restart sonrası)
# Oracle Console'dan yeni IP'yi kontrol et
```

### Python hataları:

```bash
# Dependencies'i tekrar yükle
cd ~/telegram-screener
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

---

## 📊 Kullanım Akışı

1. **Günde 1-2 kez** (Mac'inizden):
   ```bash
   bash deploy/update_watchlist_local.sh
   scp watchlist.json ubuntu@VM_IP:~/telegram-screener/
   ssh ubuntu@VM_IP 'sudo systemctl restart telegram-screener'
   ```

2. **Oracle VM**: Her 8 saatte bir otomatik olarak:
   - Watchlist'teki sembolleri tarar
   - Stochastic RSI hesaplar
   - Buy sinyali bulursa Telegram'a gönderir

3. **Telegram**: Bildirimler gelir! 🚀

---

## 💰 Maliyet

**$0.00** - Tamamen bedava, sonsuza kadar!

Oracle Always Free Tier:
- 2x AMD Micro VM
- 1 GB RAM her biri
- 200 GB block storage
- 10 TB bandwidth/ay

---

## 🔒 Güvenlik

1. **Firewall**: Sadece SSH (port 22) açık
2. **SSH Key**: Password authentication kapalı
3. **Updates**: 
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo reboot  # Gerekirse
   ```

---

## 📚 Faydalı Komutlar

```bash
# Disk kullanımı
df -h

# RAM kullanımı
free -h

# CPU kullanımı
top

# Network testi
ping google.com

# Python paketleri
pip list

# Service restart after config change
sudo systemctl restart telegram-screener

# Watch logs live with filter
sudo journalctl -u telegram-screener -f | grep -i "signal\|error"
```

---

## ✅ Son Kontrol Listesi

- [ ] Oracle Cloud hesabı oluşturuldu
- [ ] VM instance başlatıldı
- [ ] SSH bağlantısı kuruldu
- [ ] Proje deploy edildi
- [ ] config.yaml düzenlendi
- [ ] watchlist.json upload edildi
- [ ] Systemd service aktif
- [ ] Telegram bot çalışıyor
- [ ] İlk test sinyali alındı

---

**Hazırsınız! 🎉**

Artık sisteminiz 7/24 çalışacak ve buy sinyalleri gelecek!
