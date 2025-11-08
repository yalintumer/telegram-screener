#!/bin/bash
# Oracle Cloud VM Hızlı Kurulum Script'i
# SSH'a bağlandıktan sonra bu komutu çalıştırın:
# curl -sSL https://raw.githubusercontent.com/yalintumer/telegram-screener/main/deploy/quick_install.sh | bash

set -e

echo "🚀 Telegram Screener - Hızlı Kurulum"
echo "===================================="
echo ""

# Sistem güncelle
echo "📦 Sistem güncelleniyor..."
sudo apt update
sudo apt upgrade -y

# Gerekli paketler
echo "📚 Gerekli paketler yükleniyor..."
sudo apt install -y git python3 python3-pip python3-venv tesseract-ocr

# Proje indir
echo "📥 Proje GitHub'dan indiriliyor..."
if [ -d "$HOME/telegram-screener" ]; then
    echo "⚠️  telegram-screener dizini zaten var, güncelleniyor..."
    cd "$HOME/telegram-screener"
    git pull
else
    git clone https://github.com/yalintumer/telegram-screener.git "$HOME/telegram-screener"
    cd "$HOME/telegram-screener"
fi

# Virtual environment
echo "🐍 Python virtual environment oluşturuluyor..."
python3 -m venv venv
source venv/bin/activate

# Dependencies
echo "📦 Python paketleri yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt

# Config
echo "⚙️  Config dosyası hazırlanıyor..."
if [ ! -f config.yaml ]; then
    cp deploy/config.production.yaml config.yaml
    echo "✅ config.yaml oluşturuldu"
else
    echo "⚠️  config.yaml zaten var, değiştirilmedi"
fi

# Watchlist
echo "📝 Watchlist oluşturuluyor..."
if [ ! -f watchlist.json ]; then
    echo '{}' > watchlist.json
    echo "✅ Boş watchlist.json oluşturuldu"
else
    echo "⚠️  watchlist.json zaten var, değiştirilmedi"
fi

# Logs dizini
mkdir -p logs

# Systemd service
echo "🔧 Systemd service kuruluyor..."
sudo bash -c "cat > /etc/systemd/system/telegram-screener.service << 'EOF'
[Unit]
Description=Telegram Stock Screener Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/telegram-screener
Environment=\"PATH=$HOME/telegram-screener/venv/bin\"
ExecStart=$HOME/telegram-screener/venv/bin/python -m src.main --config config.yaml run --interval 28800
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Service aktif et
echo "🚀 Service başlatılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable telegram-screener
sudo systemctl start telegram-screener

echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo "📊 Servis durumu:"
sudo systemctl status telegram-screener --no-pager -l
echo ""
echo "📝 Sıradaki adımlar:"
echo "1. Watchlist'i Mac'inizden güncelleyin:"
echo "   bash deploy/update_watchlist_local.sh"
echo "   scp -i ~/Downloads/ssh-key-2025-11-08.key watchlist.json ubuntu@79.72.45.149:~/telegram-screener/"
echo ""
echo "2. Service'i restart edin:"
echo "   sudo systemctl restart telegram-screener"
echo ""
echo "3. Logları izleyin:"
echo "   sudo journalctl -u telegram-screener -f"
