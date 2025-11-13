#!/bin/bash
# Quick deployment script for Linux VM
# Run with: bash quick_deploy_vm.sh

set -e  # Exit on error

echo "🚀 Telegram Screener - Quick VM Deployment"
echo "=========================================="

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "❌ This script is for Linux only!"
    echo "   For macOS, use: python3 deploy_macos.py"
    exit 1
fi

# Check if we're in the project directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

echo ""
echo "📦 Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip tesseract-ocr git

echo ""
echo "🐍 Step 2: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

echo ""
echo "📚 Step 3: Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "⚙️  Step 4: Checking configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 Please edit .env file with your credentials:"
    echo "   nano .env"
    echo ""
    echo "   Required:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_CHAT_ID"
    echo ""
    read -p "Press Enter after configuring .env file..."
else
    echo "✅ .env file exists"
fi

if [ ! -f "config.yaml" ]; then
    echo "⚠️  config.yaml not found!"
    echo "   Creating from template..."
    cp config.example.yaml config.yaml
    echo "✅ Created config.yaml"
else
    echo "✅ config.yaml exists"
fi

echo ""
echo "🧪 Step 5: Testing installation..."
python3 -m src.main --help > /dev/null 2>&1 && echo "✅ Application runs successfully" || echo "❌ Application test failed"

echo ""
echo "📊 Step 6: Installing systemd service..."
python3 deploy_service.py install

echo ""
echo "🚀 Step 7: Starting service..."
python3 deploy_service.py start

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Useful commands:"
echo "   python3 deploy_service.py status    - Check service status"
echo "   python3 deploy_service.py logs      - View logs"
echo "   python3 deploy_service.py restart   - Restart service"
echo "   python3 -m src.main status          - Check application status"
echo "   python3 -m src.main list            - Show watchlist"
echo ""
echo "🔍 Monitoring:"
echo "   sudo journalctl -u telegram-screener -f"
echo ""
