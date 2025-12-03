"""
Test script to send a sample rich Telegram notification
Shows the new notification format with TradingView links and performance stats
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.telegram_client import TelegramClient
from datetime import date


def send_sample_notification():
    """Send a sample rich notification to test the new format"""
    
    # Load config
    cfg = Config.load("config.yaml")
    
    # Initialize Telegram client
    telegram = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
    
    # Sample data
    symbol = "AAPL"
    today_str = date.today().strftime('%Y-%m-%d')
    tradingview_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
    
    # Build rich notification message
    message_lines = [
        "🚨🚨🚨 **BUY SIGNAL CONFIRMED!** 🚨🚨🚨",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"**📈 SYMBOL: `{symbol}`**",
        f"💰 **Price:** $180.50",
        f"📊 [View on TradingView]({tradingview_link})",
        "",
        "**✅ TWO-STAGE FILTER PASSED:**",
        "",
        "**🔵 Stage 1:** Stochastic RSI + MFI",
        f"   • Stoch RSI: K=15.5% | D=12.3%",
        f"   • MFI: 35.2 (3-day uptrend ✓)",
        "",
        "**🟢 Stage 2:** WaveTrend Confirmation",
        f"   • WT1: -58.5",
        f"   • WT2: -62.3",
        f"   • **Oversold zone cross detected** 🎯",
        "",
        "📊 **Historical Performance (AAPL):**",
        "   • Win Rate: 75% | Avg Return: +12.5%",
        "   • Total Signals: 4 | Evaluated: 3",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📅 **Date:** {today_str}",
        "🚀 **ACTION: STRONG BUY CANDIDATE**",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "_This is a TEST notification showcasing the new rich format with multi-timeframe analysis and performance tracking._"
    ]
    
    message = "\n".join(message_lines)
    
    print("📤 Sending sample rich notification to Telegram...")
    print(f"📱 Chat ID: {cfg.telegram.chat_id}")
    print()
    print("=" * 60)
    print(message)
    print("=" * 60)
    print()
    
    try:
        telegram.send(message)
        print("✅ Sample notification sent successfully!")
        print()
        print("🎉 Check your Telegram to see the new format with:")
        print("   • TradingView chart link (clickable)")
        print("   • Current price")
        print("   • All indicator values")
        print("   • Historical performance stats")
        print("   • Professional formatting")
        
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send_sample_notification()
