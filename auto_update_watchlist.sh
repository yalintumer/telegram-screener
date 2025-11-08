#!/bin/bash
# Otomatik Watchlist Güncelleyici
# Mac'te çalışır - capture → upload → restart

set -e

PROJECT_DIR="/Users/yalintumer/Desktop/Telegram Proje"
SSH_KEY="$HOME/screener"
SERVER="root@167.99.252.127"
SERVER_PATH="/root/telegram-screener"

cd "$PROJECT_DIR"

echo "🔄 Otomatik Watchlist Güncelleme Başladı"
echo "========================================"
echo ""

# 1. Virtual environment aktif et
echo "📦 Virtual environment aktif ediliyor..."
source venv_clean/bin/activate

# 2. TradingView'dan capture yap
echo "📸 TradingView'dan screenshot alınıyor ve OCR yapılıyor..."
echo "🖱️  TradingView penceresine tıklanıyor (150,50)..."
python -m src.main --config config.yaml capture --click 150,50

if [ ! -f "watchlist.json" ]; then
    echo "❌ Hata: watchlist.json oluşturulamadı!"
    exit 1
fi

echo ""
echo "✅ Watchlist güncellendi!"
echo "📋 İçerik:"
cat watchlist.json
echo ""

# 3. Sunucuya upload et
echo "📤 Watchlist sunucuya gönderiliyor..."
scp -i "$SSH_KEY" watchlist.json "$SERVER:$SERVER_PATH/"

if [ $? -ne 0 ]; then
    echo "❌ Hata: Sunucuya upload başarısız!"
    exit 1
fi

echo "✅ Upload başarılı!"
echo ""

# 4. Sunucuda service'i restart et
echo "🔄 Sunucuda service restart ediliyor..."
ssh -i "$SSH_KEY" "$SERVER" 'systemctl restart telegram-screener'

if [ $? -ne 0 ]; then
    echo "❌ Hata: Service restart başarısız!"
    exit 1
fi

echo "✅ Service restart edildi!"
echo ""

# 5. Sunucuda durumu kontrol et
echo "📊 Sunucu durumu:"
ssh -i "$SSH_KEY" "$SERVER" 'systemctl status telegram-screener --no-pager | head -15'

echo ""
echo "🎉 Tamamlandı! Watchlist başarıyla güncellendi ve sunucuya yüklendi!"
echo ""
echo "⏰ Sonraki güncelleme: Dilediğiniz zaman bu script'i tekrar çalıştırın"
echo "   veya cron/launchd ile otomatikleştirin!"
