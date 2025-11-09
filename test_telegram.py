#!/usr/bin/env python3
"""
Telegram bot test script
Gerçek bot token ve chat ID ekleyerek test edin
"""

import sys
from src.telegram_client import TelegramClient

# Buraya kendi bot token ve chat ID'nizi girin
BOT_TOKEN = input("Telegram Bot Token: ").strip()
CHAT_ID = input("Chat ID: ").strip()

if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
    print("❌ Lütfen geçerli bir bot token girin!")
    sys.exit(1)

if not CHAT_ID or CHAT_ID == "your_chat_id_here":
    print("❌ Lütfen geçerli bir chat ID girin!")
    sys.exit(1)

print(f"\n🤖 Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print(f"💬 Chat ID: {CHAT_ID}")
print("\n📤 Test mesajı gönderiliyor...")

try:
    tg = TelegramClient(BOT_TOKEN, CHAT_ID)
    
    message = """
🧪 **Telegram Test Mesajı**

✅ Bot başarıyla çalışıyor!
📊 Screener uygulaması hazır

_Bu bir test mesajıdır._
"""
    
    tg.send(message)
    print("\n✅ Test mesajı başarıyla gönderildi!")
    print("📱 Telegram'ınızı kontrol edin")
    
except Exception as e:
    print(f"\n❌ Hata: {e}")
    sys.exit(1)
