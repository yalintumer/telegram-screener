#!/bin/bash
# Güvenlik Kontrol Scripti
# Projede hassas bilgi olup olmadığını kontrol eder

echo "🔍 Güvenlik Kontrolü Başlatılıyor..."
echo ""

# API anahtarlarını ara (gerçek anahtarlar için pattern)
echo "📋 1. API anahtarları kontrol ediliyor..."
if git ls-files | xargs grep -l "7735605186\|AAHNv0iGkp\|6155401829" 2>/dev/null | grep -v ".gitignore\|SECURITY.md\|TOKEN_YENILEME.md"; then
    echo "❌ UYARI: Git'e commit edilmiş dosyalarda gerçek API anahtarları bulundu!"
else
    echo "✅ Git'e commit edilmiş dosyalarda gerçek API anahtarı yok"
fi
echo ""

# .env dosyası kontrol
echo "📋 2. .env dosyası kontrol ediliyor..."
if [ -f ".env" ]; then
    if git ls-files --error-unmatch .env 2>/dev/null; then
        echo "❌ UYARI: .env dosyası Git'e eklenmiş!"
    else
        echo "✅ .env dosyası Git'e eklenmemiş"
    fi
else
    echo "⚠️  .env dosyası bulunamadı"
fi
echo ""

# config.yaml kontrol
echo "📋 3. config.yaml kontrol ediliyor..."
if grep -q "YOUR_TELEGRAM_BOT_TOKEN\|your_bot_token_here" config.yaml 2>/dev/null; then
    echo "✅ config.yaml placeholder değerler içeriyor"
else
    echo "❌ UYARI: config.yaml gerçek değerler içeriyor olabilir!"
fi
echo ""

# .gitignore kontrol
echo "📋 4. .gitignore kontrol ediliyor..."
if grep -q ".env" .gitignore && grep -q "config.yaml" .gitignore; then
    echo "✅ .gitignore doğru yapılandırılmış"
else
    echo "❌ UYARI: .gitignore eksik!"
fi
echo ""

# Log dosyaları kontrol
echo "📋 5. Log dosyalarında hassas bilgi kontrol ediliyor..."
if [ -d "logs" ]; then
    if grep -r "bot_token.*[0-9].*:.*[A-Za-z0-9]" logs/ 2>/dev/null | grep -v "YOUR_"; then
        echo "⚠️  UYARI: Log dosyalarında hassas bilgi olabilir!"
    else
        echo "✅ Log dosyalarında gerçek token bulunamadı"
    fi
else
    echo "✅ Log klasörü yok"
fi
echo ""

echo "🏁 Güvenlik kontrolü tamamlandı!"
