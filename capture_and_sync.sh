#!/bin/bash
# capture_and_sync.sh - TradingView'dan capture yap ve VM'ye gönder

cd "/Users/yalintumer/Desktop/Telegram Proje"

echo "📸 Taking screenshot from TradingView..."
python -m src.main --config config.yaml capture

if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 Syncing to VM..."
    python3 quick_add.py --sync-only
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Capture and sync complete!"
        echo ""
        echo "📋 Current watchlist:"
        python3 -c "import json; data=json.load(open('watchlist.json')); print('\n'.join(sorted(data.keys())))"
    else
        echo "⚠️  Sync failed but capture was successful"
    fi
else
    echo "❌ Capture failed"
    exit 1
fi
