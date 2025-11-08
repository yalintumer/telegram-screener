#!/bin/bash
# Test ve Debug Script'leri - DigitalOcean VM için

SCRIPT_DIR="/root/telegram-screener"
cd "$SCRIPT_DIR"
source venv/bin/activate

echo "🧪 Telegram Screener - Test & Debug"
echo "===================================="
echo ""

# Menü
cat << 'MENU'
Seçenekler:
-----------
1) Watchlist'i göster
2) Tek bir scan yap (dry-run)
3) Tek bir scan yap (gerçek - Telegram gönderir)
4) Belirli bir sembolü test et
5) Servis loglarını göster
6) Servis durumunu göster
7) Test Telegram mesajı gönder
8) Config dosyasını göster
9) Çıkış

MENU

read -p "Seçiminiz (1-9): " choice

case $choice in
    1)
        echo ""
        echo "📋 Watchlist İçeriği:"
        echo "===================="
        cat watchlist.json | python3 -m json.tool
        echo ""
        python -m src.main --config config.yaml list
        ;;
    
    2)
        echo ""
        echo "🔍 Test Scan Başlatılıyor (Telegram göndermiyor)..."
        echo "===================================================="
        echo ""
        echo "⚠️  Not: Gerçek bir dry-run yok, ama watchlist boşsa hiçbir şey olmaz"
        echo ""
        read -p "Devam? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            python -m src.main --config config.yaml scan --sleep 5
        else
            echo "İptal edildi."
        fi
        ;;
    
    3)
        echo ""
        echo "🚀 Gerçek Scan Başlatılıyor..."
        echo "=============================="
        read -p "Emin misiniz? Buy sinyali varsa Telegram'a gönderilecek! (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            python -m src.main --config config.yaml scan --sleep 15
        else
            echo "İptal edildi."
        fi
        ;;
    
    4)
        echo ""
        read -p "Sembol adı (örn: AAPL): " symbol
        echo ""
        echo "🔍 $symbol için test..."
        echo "======================="
        python3 << EOF
import sys
sys.path.insert(0, '/root/telegram-screener')
from src.config import Config
from src.data_source_yfinance import daily_ohlc
from src.indicators import stochastic_rsi, stoch_rsi_buy

cfg = Config.load('config.yaml')
symbol = '$symbol'

try:
    print(f"📊 {symbol} verisi çekiliyor...")
    df = daily_ohlc(symbol)
    
    if df is None or len(df) < 30:
        print(f"❌ Yetersiz veri!")
        sys.exit(1)
    
    print(f"✅ {len(df)} günlük veri alındı")
    print(f"📈 Son fiyat: \${df['Close'].iloc[-1]:.2f}")
    print()
    
    print("📊 Stochastic RSI hesaplanıyor...")
    ind = stochastic_rsi(df['Close'], rsi_period=14, stoch_period=14, k=3, d=3)
    
    last = ind.iloc[-1]
    print(f"   RSI: {last['rsi']:.2f}")
    print(f"   K: {last['k']:.2f}")
    print(f"   D: {last['d']:.2f}")
    print()
    
    if stoch_rsi_buy(ind):
        print("🚀 BUY SİNYALİ! (K < 20 veya D < 20 VE K > D cross)")
    else:
        print("⏸️  Şu an sinyal yok")
        if last['k'] < 20 or last['d'] < 20:
            print("   (Oversold bölgesinde ama cross yok)")
        
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
EOF
        ;;
    
    5)
        echo ""
        echo "📜 Son 50 Satır Log:"
        echo "==================="
        sudo journalctl -u telegram-screener -n 50 --no-pager
        echo ""
        read -p "Canlı izle? (y/n): " watch
        if [ "$watch" = "y" ]; then
            sudo journalctl -u telegram-screener -f
        fi
        ;;
    
    6)
        echo ""
        echo "📊 Servis Durumu:"
        echo "================"
        sudo systemctl status telegram-screener --no-pager
        ;;
    
    7)
        echo ""
        read -p "Test mesajı metni: " msg
        python3 << EOF
import sys
sys.path.insert(0, '/root/telegram-screener')
from src.config import Config
from src.telegram_client import TelegramClient

cfg = Config.load('config.yaml')
client = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)

message = "$msg" if "$msg" else "🧪 Test mesajı - $(date)"
client.send(message)
print("✅ Mesaj gönderildi!")
EOF
        ;;
    
    8)
        echo ""
        echo "⚙️  Config Dosyası:"
        echo "=================="
        cat config.yaml
        ;;
    
    9)
        echo "Çıkış yapılıyor..."
        exit 0
        ;;
    
    *)
        echo "❌ Geçersiz seçenek!"
        ;;
esac

echo ""
read -p "Devam etmek için Enter'a basın..."
