#!/bin/bash
# Oracle Cloud VM'de projeyi GitHub'dan çekip başlatma script'i

set -e

echo "🚀 Telegram Screener Deploy Script'i"
echo "===================================="
echo ""

# Projeyi GitHub'dan çek (önce GitHub'a push etmelisiniz)
if [ ! -d "~/telegram-screener/.git" ]; then
    echo "📥 Proje GitHub'dan indiriliyor..."
    read -p "GitHub repo URL'nizi girin: " REPO_URL
    git clone "$REPO_URL" ~/telegram-screener
else
    echo "📥 Proje güncelleniyor..."
    cd ~/telegram-screener
    git pull
fi

cd ~/telegram-screener

# Virtual environment oluştur
if [ ! -d "venv" ]; then
    echo "🔧 Virtual environment oluşturuluyor..."
    python3 -m venv venv
fi

# Aktive et
source venv/bin/activate

# Dependencies yükle
echo "📦 Dependencies yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt
pip install yfinance  # Ensure yfinance is installed

# Config dosyasını production'a çevir
if [ ! -f "config.yaml" ]; then
    echo "⚙️ Config dosyası oluşturuluyor..."
    cp deploy/config.production.yaml config.yaml
    echo "❗ config.yaml dosyasını düzenleyin!"
fi

# Watchlist oluştur (boş)
if [ ! -f "watchlist.json" ]; then
    echo "📝 Boş watchlist oluşturuluyor..."
    echo '{}' > watchlist.json
    echo "❗ watchlist.json dosyasını manuel güncelleyin!"
fi

# Logs dizini
mkdir -p logs

# Service'i yükle ve başlat
echo "🔧 Systemd service yapılandırılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable telegram-screener
sudo systemctl restart telegram-screener

echo ""
echo "✅ Deploy tamamlandı!"
echo ""
echo "📊 Servis durumu:"
sudo systemctl status telegram-screener --no-pager
echo ""
echo "📝 Logları izle:"
echo "   sudo journalctl -u telegram-screener -f"
echo ""
echo "🔄 Watchlist'i güncellemek için:"
echo "   1. Mac'inizde: bash deploy/update_watchlist_local.sh"
echo "   2. watchlist.json dosyasını sunucuya kopyalayın"
echo "   3. sudo systemctl restart telegram-screener"
