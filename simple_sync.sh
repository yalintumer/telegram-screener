#!/bin/bash
# simple_sync.sh - SSH key olmadan da çalışır (şifre sorar)

cd "/Users/yalintumer/Desktop/Telegram Proje"

echo "📋 Adding symbols to watchlist..."
python3 quick_add.py "$@"

if [ $? -eq 0 ]; then
    echo ""
    read -p "🚀 Push to Git and update VM? (y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "📤 Pushing to Git..."
        git add watchlist.json signal_history.json
        git commit -m "Add symbols - $(date '+%Y-%m-%d %H:%M')"
        git push
        
        echo ""
        echo "🔄 Updating VM (will ask for password)..."
        ssh root@167.99.252.127 "cd ~/telegram-screener && git pull && sudo systemctl restart telegram-screener"
        
        echo "✅ Done!"
    fi
fi
