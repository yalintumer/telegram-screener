#!/bin/bash
# Mac açıldığında çalışacak watchlist güncelleme script'i

SCRIPT_DIR="/Users/yalintumer/Desktop/Telegram Proje"
cd "$SCRIPT_DIR"

LOG_FILE="logs/startup_update.log"
mkdir -p logs

echo "========================================" >> "$LOG_FILE"
echo "🚀 Startup check: $(date)" >> "$LOG_FILE"

# Bugün hangi gün?
DAY_OF_WEEK=$(date +%u)  # 1=Pazartesi, 7=Pazar

# Hafta sonu kontrolü (Cumartesi=6, Pazar=7)
if [ "$DAY_OF_WEEK" -eq 6 ] || [ "$DAY_OF_WEEK" -eq 7 ]; then
    echo "⏭️  Hafta sonu - işlem yapılmıyor" >> "$LOG_FILE"
    exit 0
fi

# Son güncelleme zamanını kontrol et (watchlist.json'dan)
if [ -f "watchlist.json" ]; then
    # watchlist.json'un son değiştirilme zamanı
    LAST_UPDATE=$(stat -f %m "watchlist.json")
    CURRENT_TIME=$(date +%s)
    HOURS_SINCE=$((($CURRENT_TIME - $LAST_UPDATE) / 3600))
    
    echo "📊 Son güncelleme: $HOURS_SINCE saat önce" >> "$LOG_FILE"
    
    # 16 saatten yeniyse güncelleme yapma
    if [ $HOURS_SINCE -lt 16 ]; then
        echo "✅ Liste yeterince güncel ($HOURS_SINCE < 16 saat)" >> "$LOG_FILE"
        exit 0
    fi
else
    echo "⚠️  watchlist.json bulunamadı, güncelleme yapılacak" >> "$LOG_FILE"
fi

echo "🔄 16+ saat geçmiş, güncelleme başlatılıyor..." >> "$LOG_FILE"

# TradingView'ı aç
echo "📱 TradingView açılıyor..." >> "$LOG_FILE"
open -a "TradingView"

# TradingView'ın tamamen açılması için 60 saniye bekle
echo "⏳ TradingView'ın açılması için 60 saniye bekleniyor..." >> "$LOG_FILE"
sleep 60

# Watchlist güncelle
echo "📸 Screenshot alınıyor ve OCR yapılıyor..." >> "$LOG_FILE"
source venv_clean/bin/activate
python -m src.main --config config.yaml capture --click 150,50 >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Güncelleme başarılı!" >> "$LOG_FILE"
    
    # VM'e gönder
    echo "📤 VM'e gönderiliyor..." >> "$LOG_FILE"
    scp -i ~/screener watchlist.json root@167.99.252.127:~/telegram-screener/ >> "$LOG_FILE" 2>&1
    ssh -i ~/screener root@167.99.252.127 "systemctl restart telegram-screener" >> "$LOG_FILE" 2>&1
    echo "✅ VM güncellendi!" >> "$LOG_FILE"
else
    echo "❌ Güncelleme başarısız!" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
