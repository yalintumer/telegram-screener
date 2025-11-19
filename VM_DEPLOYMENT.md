# VM Deployment Rehberi

## 🚀 Yeni VM'e Deployment

### Yöntem 1: Otomatik Deployment (Önerilen)

#### VM'de tek komutla kur:

```bash
# VM'e SSH ile bağlan
ssh root@YENi_VM_IP

# Script'i indir ve çalıştır
curl -sL https://raw.githubusercontent.com/yalintumer/telegram-screener/main/deploy_simple.sh | bash

# Veya repo'yu klonla ve script'i çalıştır
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
bash deploy_simple.sh
```

Script otomatik olarak:
- ✅ Python ve bağımlılıkları kurar
- ✅ Virtual environment oluşturur
- ✅ Systemd service ayarlar
- ✅ Config dosyası oluşturur

#### Config'i düzenle:

```bash
nano config.yaml
```

Şu bilgileri gir:
```yaml
telegram:
  bot_token: "123456:ABC..."
  chat_id: "-100123456789"

notion:
  api_token: "secret_xxx..."
  database_id: "abc123..."

data:
  max_watch_days: 5

api:
  provider: "yfinance"
  token: ""
```

Kaydet: `Ctrl+O` → `Enter` → `Ctrl+X`

#### Test et:

```bash
source venv/bin/activate
python -m src.main --once
```

#### Service'i başlat:

```bash
systemctl start telegram-screener
systemctl enable telegram-screener    # Otomatik başlat
systemctl status telegram-screener    # Durum kontrol
```

#### Logları izle:

```bash
tail -f logs/service.log
```

---

### Yöntem 2: Manuel Deployment

#### 1. VM'e bağlan:

```bash
ssh root@YENi_VM_IP
```

#### 2. Sistem paketlerini güncelle:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git
```

#### 3. Repo'yu klonla:

```bash
cd ~
git clone https://github.com/yalintumer/telegram-screener.git
cd telegram-screener
```

#### 4. Virtual environment oluştur:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. Config dosyası oluştur:

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

Bilgileri gir (yukarıdaki gibi) ve kaydet.

#### 6. Test et:

```bash
python -m src.main --once
```

#### 7. Systemd service oluştur:

```bash
nano /etc/systemd/system/telegram-screener.service
```

İçeriği yapıştır:
```ini
[Unit]
Description=Telegram Screener - Simple
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-screener
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 3600
Restart=always
RestartSec=60
StandardOutput=append:/root/telegram-screener/logs/service.log
StandardError=append:/root/telegram-screener/logs/service.log

[Install]
WantedBy=multi-user.target
```

Kaydet ve çık.

#### 8. Logs klasörü oluştur:

```bash
mkdir -p /root/telegram-screener/logs
```

#### 9. Service'i başlat:

```bash
systemctl daemon-reload
systemctl enable telegram-screener
systemctl start telegram-screener
systemctl status telegram-screener
```

---

## 📊 VM Yönetimi

### Service Komutları:

```bash
# Başlat
systemctl start telegram-screener

# Durdur
systemctl stop telegram-screener

# Yeniden başlat
systemctl restart telegram-screener

# Durum kontrol
systemctl status telegram-screener

# Logları göster
journalctl -u telegram-screener -f
```

### Log Dosyaları:

```bash
# Service logları
tail -f /root/telegram-screener/logs/service.log

# Tüm loglar
tail -f /root/telegram-screener/logs/app.log

# Son 100 satır
tail -100 /root/telegram-screener/logs/service.log
```

### Kodu Güncelleme:

```bash
cd /root/telegram-screener
git pull
systemctl restart telegram-screener
```

### Manuel Test (Service durdurup):

```bash
systemctl stop telegram-screener
cd /root/telegram-screener
source venv/bin/activate
python -m src.main --once
```

---

## 🔧 Scan Aralığını Değiştir

Service dosyasını düzenle:

```bash
nano /etc/systemd/system/telegram-screener.service
```

`ExecStart` satırındaki `--interval` değerini değiştir:

```ini
# Her 30 dakika
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 1800

# Her 2 saat
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 7200

# Her 15 dakika
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 900
```

Kaydet ve reload et:

```bash
systemctl daemon-reload
systemctl restart telegram-screener
```

---

## ❓ Sorun Giderme

### Service başlamıyor:

```bash
# Hata loglarını kontrol et
systemctl status telegram-screener -l
journalctl -u telegram-screener -n 50

# Config'i kontrol et
cat config.yaml

# Manuel test
cd /root/telegram-screener
source venv/bin/activate
python -m src.main --once
```

### "Module not found" hatası:

```bash
cd /root/telegram-screener
source venv/bin/activate
pip install -r requirements.txt
systemctl restart telegram-screener
```

### Config hatası:

```bash
# Config syntax kontrolü
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Örnek config'i kopyala
cp config.example.yaml config.yaml
nano config.yaml
```

### Git pull çalışmıyor:

```bash
cd /root/telegram-screener
git status
git stash              # Local değişiklikleri sakla
git pull
git stash pop          # Değişiklikleri geri getir
```

---

## 🔒 Güvenlik

### Firewall (opsiyonel):

```bash
# SSH'yi koru
ufw allow 22/tcp
ufw enable
```

### SSH Key ile giriş (daha güvenli):

Mac'inden:
```bash
# SSH key oluştur (yoksa)
ssh-keygen -t ed25519

# Public key'i VM'e kopyala
ssh-copy-id root@YENi_VM_IP
```

Artık şifresiz girebilirsin:
```bash
ssh root@YENi_VM_IP
```

---

## 📦 Hızlı Komutlar

```bash
# Tek seferlik kurulum
curl -sL https://raw.githubusercontent.com/yalintumer/telegram-screener/main/deploy_simple.sh | bash

# Config düzenle
nano ~/telegram-screener/config.yaml

# Test
cd ~/telegram-screener && source venv/bin/activate && python -m src.main --once

# Başlat
systemctl start telegram-screener && systemctl enable telegram-screener

# İzle
tail -f ~/telegram-screener/logs/service.log
```

---

## 📚 Faydalı Linkler

- GitHub Repo: https://github.com/yalintumer/telegram-screener
- Notion API: https://developers.notion.com
- Systemd Docs: https://www.freedesktop.org/software/systemd/man/systemd.service.html
