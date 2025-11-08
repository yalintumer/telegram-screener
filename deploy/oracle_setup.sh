#!/bin/bash
# Oracle Cloud Ubuntu VM Kurulum Script'i
# Bu script'i SSH ile bağlandıktan sonra VM'de çalıştırın

set -e  # Hata durumunda dur

echo "🚀 Oracle Cloud VM Kurulumu Başlıyor..."

# Sistem güncellemesi
echo "📦 Sistem güncelleniyor..."
sudo apt update
sudo apt upgrade -y

# Python 3.11+ kurulumu
echo "🐍 Python kurulumu..."
sudo apt install -y python3 python3-pip python3-venv git

# Tesseract OCR kurulumu (watchlist manuel olacak ama yine de kuruyoruz)
echo "👁️ Tesseract OCR kurulumu..."
sudo apt install -y tesseract-ocr tesseract-ocr-eng

# Proje dizini oluştur
echo "📁 Proje dizini oluşturuluyor..."
mkdir -p ~/telegram-screener
cd ~/telegram-screener

# Virtual environment oluştur
echo "🔧 Python virtual environment oluşturuluyor..."
python3 -m venv venv
source venv/bin/activate

# Requirements yükle (bu dosyayı sonra upload edeceğiz)
echo "📚 Python paketleri yüklenecek..."
echo "⚠️  requirements.txt dosyasını upload ettikten sonra:"
echo "    pip install -r requirements.txt"

# Systemd service oluştur (otomatik başlatma için)
echo "⚙️ Systemd service oluşturuluyor..."
sudo tee /etc/systemd/system/telegram-screener.service > /dev/null <<EOF
[Unit]
Description=Telegram Stock Screener Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/telegram-screener
Environment="PATH=/home/$USER/telegram-screener/venv/bin"
ExecStart=/home/$USER/telegram-screener/venv/bin/python -m src.main --config config.yaml run --interval 28800
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Kurulum tamamlandı!"
echo ""
echo "📝 Sıradaki Adımlar:"
echo "1. Projeyi bu VM'e upload et (git clone veya scp)"
echo "2. cd ~/telegram-screener"
echo "3. source venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. config.yaml dosyasını düzenle"
echo "6. Watchlist'i manuel oluştur (watchlist.json)"
echo "7. sudo systemctl enable telegram-screener"
echo "8. sudo systemctl start telegram-screener"
echo "9. sudo systemctl status telegram-screener"
