#!/bin/bash
# sync_watchlist_to_vm.sh
# Mac'inizde çalıştırın - Watchlist'i VM'ye aktarır

# VM bilgilerinizi buraya girin
VM_IP="YOUR_SERVER_IP"
VM_USER="root"
VM_PATH="~/telegram-screener/watchlist.json"

LOCAL_FILE="/Users/yalintumer/Desktop/Telegram Proje/watchlist.json"

echo "📤 Syncing watchlist to VM..."
scp "$LOCAL_FILE" "$VM_USER@$VM_IP:$VM_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Watchlist synced successfully!"
    echo "🔄 Restarting service on VM..."
    ssh "$VM_USER@$VM_IP" "sudo systemctl restart telegram-screener"
    echo "✅ Service restarted!"
else
    echo "❌ Sync failed!"
    exit 1
fi
