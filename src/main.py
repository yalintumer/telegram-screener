"""Simplified Telegram screener - Notion → Stoch RSI → Telegram"""

import time
import argparse
from datetime import date
from .config import Config
from .notion_client import NotionClient
from .telegram_client import TelegramClient
from .indicators import stochastic_rsi, stoch_rsi_buy, mfi, mfi_uptrend
from .data_source_yfinance import daily_ohlc
from .logger import logger
import sentry_sdk

sentry_sdk.init(
    dsn="https://419f2c57fd95ab96c48f859f9b7ed347@o4510393252839424.ingest.de.sentry.io/4510393259196496",
    traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
    send_default_pii=True,   # Include user IP and request data
)


def check_symbol(symbol: str) -> bool:
    """
    Check if symbol has Stochastic RSI + MFI buy signal
    
    Conditions:
    1. Stochastic RSI bullish cross in oversold zone
    2. MFI in uptrend for last 3 days (volume-weighted momentum)
    
    Returns True if both conditions met
    """
    try:
        logger.info("checking_symbol", symbol=symbol)
        
        # Get price data
        df = daily_ohlc(symbol)
        
        if df is None or len(df) < 30:
            logger.warning("insufficient_data", symbol=symbol)
            return False
        
        # Calculate Stochastic RSI
        stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        # Check Stochastic RSI signal
        has_stoch_signal = stoch_rsi_buy(stoch_ind)
        
        if not has_stoch_signal:
            return False
        
        # Calculate MFI (Money Flow Index)
        mfi_values = mfi(df, period=14)
        
        # Check if MFI is in 3-day uptrend
        mfi_trending_up = mfi_uptrend(mfi_values, days=3)
        
        if has_stoch_signal and mfi_trending_up:
            logger.info("signal_found", symbol=symbol, 
                       mfi_current=float(mfi_values.iloc[-1]),
                       stoch_k=float(stoch_ind['k'].iloc[-1]))
            return True
        
        # Log why signal was rejected
        if has_stoch_signal and not mfi_trending_up:
            logger.info("signal_rejected_mfi", symbol=symbol, 
                       reason="MFI not in 3-day uptrend",
                       mfi_current=float(mfi_values.iloc[-1]))
        
        return False
        
    except Exception as e:
        logger.error("check_failed", symbol=symbol, error=str(e))
        return False


def run_scan(cfg: Config):
    """Main scan loop - fetch from Notion, check signals, send to Telegram"""
    
    # Initialize clients
    notion = NotionClient(
        cfg.notion.api_token, 
        cfg.notion.database_id,
        cfg.notion.signals_database_id
    )
    telegram = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
    
    logger.info("scan_started")
    
    # Fetch watchlist from Notion
    logger.info("fetching_watchlist_from_notion")
    symbols, symbol_to_page = notion.get_watchlist()
    
    if not symbols:
        logger.warning("empty_watchlist")
        print("⚠️  Watchlist is empty in Notion")
        return
    
    print(f"📋 Watchlist: {len(symbols)} symbols")
    print(f"   {', '.join(symbols)}\n")
    
    # Check each symbol
    signals_found = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"🔍 [{i}/{len(symbols)}] Checking {symbol}...", end=" ")
        
        has_signal = check_symbol(symbol)
        
        if has_signal:
            print("✅ SIGNAL!")
            signals_found.append(symbol)
            
            # Get indicator values for message
            df = daily_ohlc(symbol)
            mfi_values = mfi(df, period=14)
            stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
            
            # Send Telegram notification
            today_str = date.today().strftime('%Y-%m-%d')
            
            message_lines = [
                "**Yeni Sinyal Tespit Edildi!** 🚀",
                "",
                f"**Sembol:** `{symbol}`",
                f"**Sinyal:** Stokastik RSI + MFI (AL)",
                f"**Tarih:** {today_str}",
                "",
                "**Göstergeler:**",
                f"• Stoch RSI K: {stoch_ind['k'].iloc[-1]:.1%}",
                f"• Stoch RSI D: {stoch_ind['d'].iloc[-1]:.1%}",
                f"• MFI: {mfi_values.iloc[-1]:.1f} (3-gün yükselişte)",
            ]
            message = "\n".join(message_lines)
            try:
                telegram.send(message)
                logger.info("telegram_sent", symbol=symbol)
                
                # Remove from watchlist and add to signals database
                page_id = symbol_to_page.get(symbol)
                if page_id:
                    notion.delete_page(page_id)
                    print(f"   🗑️  Removed {symbol} from watchlist")
                
                # Add to signals database (if configured)
                if cfg.notion.signals_database_id:
                    # use top-level `date` import (don't re-import inside function)
                    notion.add_to_signals(symbol, date.today().isoformat())
                    print(f"   ➕ Added {symbol} to signals database")
            except Exception as e:
                logger.error("telegram_failed", symbol=symbol, error=str(e))
                print(f"   ⚠️  Failed to send Telegram: {e}")
        else:
            print("—")
        
        # Small delay to avoid rate limits
        if i < len(symbols):
            time.sleep(2)
    
    # Summary
    print(f"\n✅ Scan complete!")
    print(f"   Checked: {len(symbols)} symbols")
    print(f"   Signals: {len(signals_found)}")
    
    if signals_found:
        print(f"\n🎯 Buy signals found:")
        for s in signals_found:
            print(f"   • {s}")
    
    logger.info("scan_complete", total=len(symbols), signals=len(signals_found))


def run_continuous(cfg: Config, interval: int = 3600):
    """Run scanner continuously at specified interval"""
    
    print(f"🔄 Continuous mode started")
    print(f"   Interval: {interval}s ({interval // 60} minutes)")
    print(f"   Press Ctrl+C to stop\n")
    
    cycle = 1
    
    try:
        while True:
            print(f"{'='*60}")
            print(f"📊 Scan Cycle {cycle}")
            print(f"{'='*60}\n")
            
            try:
                run_scan(cfg)
            except Exception as e:
                logger.error("scan_error", cycle=cycle, error=str(e))
                print(f"❌ Error in cycle {cycle}: {e}")
            
            cycle += 1
            
            print(f"\n⏳ Waiting {interval}s until next scan...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped after {cycle-1} cycles")
        logger.info("stopped_by_user", cycles=cycle-1)


def main(argv: list[str] | None = None):
    """CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Simple Telegram Screener: Notion → Stoch RSI → Telegram"
    )
    
    parser.add_argument("--config", default="config.yaml",
                       help="Config file path (default: config.yaml)")
    
    parser.add_argument("--interval", type=int, default=3600,
                       help="Scan interval in seconds (default: 3600 = 1 hour)")
    
    parser.add_argument("--once", action="store_true",
                       help="Run once and exit (default: continuous)")
    
    args = parser.parse_args(argv)
    
    try:
        # Load config
        cfg = Config.load(args.config)
        
        # Run
        if args.once:
            run_scan(cfg)
        else:
            run_continuous(cfg, interval=args.interval)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 130
    
    except Exception as e:
        logger.exception("fatal_error")
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
