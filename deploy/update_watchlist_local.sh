#!/bin/bash
# Watchlist'i manuel güncelleme script'i
# Yerel Mac'inizde çalıştırıp sonucu sunucuya upload edeceksiniz

set -e

echo "📸 TradingView'dan ticker'lar çekiliyor..."

cd "/Users/yalintumer/Desktop/Telegram Proje"
source venv_clean/bin/activate

# Capture komutunu çalıştır (sadece watchlist günceller)
python -m src.main --config config.yaml capture

echo "✅ Watchlist güncellendi: watchlist.json"
echo ""
echo "📤 Şimdi bu dosyayı sunucuya upload edin:"
echo "   scp watchlist.json oraclevm:~/telegram-screener/"
echo ""
echo "   veya içeriği kopyala-yapıştır:"
cat watchlist.json
