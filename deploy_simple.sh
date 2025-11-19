#!/bin/bash

# Simple deployment script for VM

echo "🚀 Telegram Screener - Simple Deployment"
echo "========================================="
echo ""

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Python if needed
if ! command -v python3 &> /dev/null; then
    echo "🐍 Installing Python..."
    apt install -y python3 python3-pip python3-venv
fi

# Install git if needed
if ! command -v git &> /dev/null; then
    echo "📥 Installing Git..."
    apt install -y git
fi

# Clone or pull repo
if [ -d "telegram-screener" ]; then
    echo "📥 Updating repository..."
    cd telegram-screener
    git pull
else
    echo "📥 Cloning repository..."
    git clone https://github.com/yalintumer/telegram-screener.git
    cd telegram-screener
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Setup config
if [ ! -f "config.yaml" ]; then
    echo "⚙️  Creating config file..."
    cp config.example.yaml config.yaml
    echo ""
    echo "⚠️  IMPORTANT: Edit config.yaml with your credentials:"
    echo "   - Telegram bot token & chat ID"
    echo "   - Notion API token & database ID"
    echo ""
    echo "Run: nano config.yaml"
    echo ""
fi

# Create systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/telegram-screener.service << 'EOF'
[Unit]
Description=Telegram Screener - Simple
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-screener
ExecStart=/root/telegram-screener/venv/bin/python -m src.main --interval 3600
Restart=always
RestartSec=60
StandardOutput=append:/root/telegram-screener/logs/service.log
StandardError=append:/root/telegram-screener/logs/service.log

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory
mkdir -p logs

# Reload systemd
systemctl daemon-reload

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit config: nano config.yaml"
echo "   2. Test run: source venv/bin/activate && python -m src.main --once"
echo "   3. Start service: systemctl start telegram-screener"
echo "   4. Enable autostart: systemctl enable telegram-screener"
echo "   5. Check status: systemctl status telegram-screener"
echo "   6. View logs: tail -f logs/service.log"
echo ""
