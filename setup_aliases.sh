#!/bin/bash
# setup_aliases.sh - Telegram Screener kısayollarını kur

SHELL_RC=""

# Detect shell - prioritize zsh if exists
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  Neither .zshrc nor .bashrc found. Creating .zshrc..."
    SHELL_RC="$HOME/.zshrc"
    touch "$SHELL_RC"
fi

echo "📝 Installing Telegram Screener aliases to $SHELL_RC"
echo ""

# Check if already installed
if grep -q "# Telegram Screener Aliases" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  Aliases already installed!"
    echo "   Edit $SHELL_RC manually to update."
    exit 0
fi

# Add aliases
cat >> "$SHELL_RC" << 'EOF'

# Telegram Screener Aliases
alias tvm='ssh root@167.99.252.127'
alias tvstatus='ssh root@167.99.252.127 "systemctl status telegram-screener --no-pager"'
alias tvlogs='ssh root@167.99.252.127 "journalctl -u telegram-screener -f"'
alias tvrestart='ssh root@167.99.252.127 "systemctl restart telegram-screener"'
alias tvlist='ssh root@167.99.252.127 "cd ~/telegram-screener && cat watchlist.json"'
alias tvcapture='cd "/Users/yalintumer/Desktop/Telegram Proje" && ./capture_and_sync.sh'
alias tvadd='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_add.py'
alias tvcd='cd "/Users/yalintumer/Desktop/Telegram Proje"'
alias tvpush='cd "/Users/yalintumer/Desktop/Telegram Proje" && git add . && git commit -m "Update" && git push'
alias tvsync='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_add.py --sync-only'
alias tvhealth='cd "/Users/yalintumer/Desktop/Telegram Proje" && python3 quick_health_check.py'
EOF

echo "✅ Aliases installed!"
echo ""
echo "🔄 Reload your shell:"
echo "   source $SHELL_RC"
echo ""
echo "📚 Available commands:"
echo "   tvm         - SSH to VM"
echo "   tvstatus    - Check service status"
echo "   tvlogs      - Watch logs live"
echo "   tvrestart   - Restart service"
echo "   tvlist      - Show watchlist (VM)"
echo "   tvcapture   - Take screenshot & sync"
echo "   tvadd       - Add symbols (usage: tvadd AAPL MSFT --sync)"
echo "   tvcd        - Go to project directory"
echo "   tvpush      - Quick git push"
echo "   tvsync      - Sync current state to VM"
echo "   tvhealth    - Run health check"
echo ""
echo "🎉 Setup complete! Run: source $SHELL_RC"
