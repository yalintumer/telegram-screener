#!/bin/bash
# Compare local and VM watchlists

echo "🔍 Watchlist Comparison"
echo "======================"

echo -e "\n📱 LOCAL:"
cat watchlist.json | grep -oE '"[A-Z]+"' | tr -d '"' | sort

echo -e "\n🖥️  VM:"
ssh root@167.99.252.127 "cat ~/telegram-screener/watchlist.json" | grep -oE '"[A-Z]+"' | tr -d '"' | sort

echo -e "\n🔄 DIFF:"
diff <(cat watchlist.json | grep -oE '"[A-Z]+"' | tr -d '"' | sort) \
     <(ssh root@167.99.252.127 "cat ~/telegram-screener/watchlist.json" | grep -oE '"[A-Z]+"' | tr -d '"' | sort) || echo "✅ In sync!"
