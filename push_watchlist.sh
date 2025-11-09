#!/bin/bash
# push_watchlist.sh - Mac'inizde çalıştırın

cd "/Users/yalintumer/Desktop/Telegram Proje"

echo "📋 Current watchlist:"
cat watchlist.json | grep -o '"[^"]*":' | tr -d '":' | grep -v "added"

echo ""
read -p "🚀 Push to Git and update VM? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "📤 Pushing to Git..."
    git add watchlist.json signal_history.json
    git commit -m "Update watchlist - $(date '+%Y-%m-%d %H:%M')"
    git push
    
    echo "✅ Pushed to Git!"
    echo ""
    echo "🔧 Now run this on VM:"
    echo "   cd ~/telegram-screener && git pull && sudo systemctl restart telegram-screener"
else
    echo "❌ Cancelled"
fi
