#!/bin/bash
cd /root/telegram-screener
source venv/bin/activate

while true; do
    echo "🔍 Starting scan cycle at $(date)"
    python -m src.main --config config.yaml scan
    echo "⏳ Waiting 3600 seconds (1 hour) before next scan..."
    sleep 3600
done
