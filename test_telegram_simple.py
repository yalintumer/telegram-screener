#!/usr/bin/env python3
"""
Telegram bot test script - config.yaml'dan okur
"""

import sys
from src.config import Config
from src.telegram_client import TelegramClient

# Config dosyasını yükle
try:
    cfg = Config.load("config.yaml")
except Exception as e:
    print(f"❌ Config yükleme hatası: {e}")
    sys.exit(1)

# Bot bilgilerini kontrol et
if cfg.telegram.bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
    print("❌ Lütfen config.yaml dosyasına gerçek bot token ekleyin!")
    print("\n📝 Nasıl alınır:")
    print("   1. Telegram'da @BotFather'ı aç")
    print("   2. /newbot komutunu gönder")
    print("   3. Bot adını ve kullanıcı adını belirle")
    print("   4. Token'ı kopyala ve config.yaml'a yapıştır")
    sys.exit(1)

if cfg.telegram.chat_id == "YOUR_TELEGRAM_CHAT_ID":
    print("❌ Lütfen config.yaml dosyasına gerçek chat ID ekleyin!")
    print("\n📝 Nasıl alınır:")
    print("   1. Telegram'da @userinfobot'u aç")
    print("   2. Bot'a herhangi bir mesaj gönder")
    print("   3. 'Id:' satırındaki numarayı kopyala")
    print("   4. Chat ID'yi config.yaml'a yapıştır")
    sys.exit(1)

print(f"🤖 Bot Token: {cfg.telegram.bot_token[:10]}...{cfg.telegram.bot_token[-5:]}")
print(f"💬 Chat ID: {cfg.telegram.chat_id}")
print("\n📤 Test mesajı gönderiliyor...")

try:
    tg = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
    
    message = """
🧪 **Telegram Test Mesajı**

✅ Bot başarıyla çalışıyor!
📊 Screener uygulaması hazır
🔒 Güvenlik güncellemesi tamamlandı

_Bu bir test mesajıdır._
"""
    
    tg.send(message)
    print("\n✅ Test mesajı başarıyla gönderildi!")
    print("📱 Telegram'ınızı kontrol edin")
    
except Exception as e:
    print(f"\n❌ Hata: {e}")
    print("\n💡 İpucu:")
    print("   - Bot token doğru mu?")
    print("   - Chat ID doğru mu?")
    print("   - İnternet bağlantınız var mı?")
    sys.exit(1)
