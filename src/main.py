"""Simplified Telegram screener - Notion → Stoch RSI → Telegram"""

import time
import argparse
from datetime import date
from .config import Config
from .notion_client import NotionClient
from .telegram_client import TelegramClient
from .indicators import stochastic_rsi, stoch_rsi_buy, mfi, mfi_uptrend, wavetrend, wavetrend_buy
from .data_source_yfinance import daily_ohlc
from .logger import logger
import sentry_sdk

sentry_sdk.init(
    dsn="https://419f2c57fd95ab96c48f859f9b7ed347@o4510393252839424.ingest.de.sentry.io/4510393259196496",
    traces_sample_rate=1.0,  # Capture 100% of transactions for performance monitoring
    send_default_pii=True,   # Include user IP and request data
)


def check_symbol_wavetrend(symbol: str) -> bool:
    """
    Check if symbol has WaveTrend buy signal (second-stage filter)
    
    Conditions:
    1. WaveTrend WT1 crosses above WT2 in oversold zone (< -53)
    
    Returns True if WaveTrend signal detected
    """
    try:
        logger.info("checking_wavetrend", symbol=symbol)
        
        # Get price data
        df = daily_ohlc(symbol)
        
        if df is None or len(df) < 30:
            logger.warning("insufficient_data", symbol=symbol)
            return False
        
        # Calculate WaveTrend
        wt = wavetrend(df, channel_length=10, average_length=21)
        
        # Check for WaveTrend buy signal
        has_wt_signal = wavetrend_buy(wt, lookback_days=3, oversold_level=-53)
        
        if has_wt_signal:
            logger.info("wavetrend_signal_found", symbol=symbol,
                       wt1=float(wt['wt1'].iloc[-1]),
                       wt2=float(wt['wt2'].iloc[-1]))
        
        return has_wt_signal
        
    except Exception as e:
        logger.error("wavetrend_check_failed", symbol=symbol, error=str(e))
        return False


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
        cfg.notion.signals_database_id,
        cfg.notion.buy_database_id
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
    
    # Get symbols already in signals or buy databases (to avoid duplicates)
    existing_symbols = notion.get_all_symbols()
    if existing_symbols:
        logger.info("existing_signals_found", count=len(existing_symbols), symbols=list(existing_symbols))
        print(f"ℹ️  Skipping {len(existing_symbols)} symbols already in signals/buy: {', '.join(sorted(existing_symbols))}\n")
    
    print(f"📋 Watchlist: {len(symbols)} symbols")
    print(f"   {', '.join(symbols)}\n")
    
    # Check each symbol
    signals_found = []
    skipped_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"🔍 [{i}/{len(symbols)}] Checking {symbol}...", end=" ")
        
        # Skip if already in signals or buy database
        if symbol in existing_symbols:
            print("⏭️  (already in signals/buy)")
            skipped_symbols.append(symbol)
            continue
        
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
    print(f"   Skipped: {len(skipped_symbols)} (already in signals/buy)")
    print(f"   Signals: {len(signals_found)}")
    
    if signals_found:
        print(f"\n🎯 New signals found:")
        for s in signals_found:
            print(f"   • {s}")
    
    logger.info("scan_complete", total=len(symbols), skipped=len(skipped_symbols), signals=len(signals_found))


def run_wavetrend_scan(cfg: Config):
    """
    Second-stage scan: Check signals database for WaveTrend confirmation
    
    This scans the first-stage signals (Stoch RSI + MFI) and applies WaveTrend filter.
    Confirmed signals move to buy database.
    """
    
    # Initialize clients
    notion = NotionClient(
        cfg.notion.api_token,
        cfg.notion.database_id,
        cfg.notion.signals_database_id,
        cfg.notion.buy_database_id
    )
    telegram = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
    
    logger.info("wavetrend_scan_started")
    
    # Fetch symbols from signals database
    logger.info("fetching_signals_from_notion")
    symbols, symbol_to_page = notion.get_signals()
    
    if not symbols:
        print("⚠️  Signals database is empty")
        return
    
    # Get symbols already in buy database (to avoid re-adding)
    buy_symbols = set()
    if cfg.notion.buy_database_id:
        try:
            buy_symbols = set(notion._get_symbols_from_database(cfg.notion.buy_database_id))
            if buy_symbols:
                logger.info("existing_buy_symbols", count=len(buy_symbols), symbols=list(buy_symbols))
                print(f"ℹ️  Skipping {len(buy_symbols)} symbols already in buy: {', '.join(sorted(buy_symbols))}\n")
        except Exception as e:
            logger.warning("get_buy_symbols_failed", error=str(e))
    
    print(f"📋 Signals to check: {len(symbols)} symbols")
    print(f"   {', '.join(symbols)}\n")
    
    # Check each symbol for WaveTrend
    confirmed_signals = []
    skipped_buy = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"🌊 [{i}/{len(symbols)}] Checking WaveTrend for {symbol}...", end=" ")
        
        # Skip if already in buy database
        if symbol in buy_symbols:
            print("⏭️  (already in buy)")
            skipped_buy.append(symbol)
            continue
        
        has_wt_signal = check_symbol_wavetrend(symbol)
        
        if has_wt_signal:
            print("✅ CONFIRMED!")
            confirmed_signals.append(symbol)
            
            # Get WaveTrend values for message
            df = daily_ohlc(symbol)
            wt = wavetrend(df, channel_length=10, average_length=21)
            stoch = stochastic_rsi(df['Close'])
            mfi_val = mfi(df)
            
            # Send Telegram notification
            today_str = date.today().strftime('%Y-%m-%d')
            
            message_lines = [
                "🚨🚨🚨 **BUY SIGNAL CONFIRMED!** 🚨🚨🚨",
                "━━━━━━━━━━━━━━━━━━━━━━",
                "",
                f"**📈 SYMBOL: `{symbol}`**",
                "",
                "**✅ TWO-STAGE FILTER PASSED:**",
                "",
                "**🔵 Stage 1:** Stochastic RSI + MFI",
                f"   • Stoch RSI: K={stoch['k'].iloc[-1]*100:.2f}% | D={stoch['d'].iloc[-1]*100:.2f}%",
                f"   • MFI: {mfi_val.iloc[-1]:.2f} (3-day uptrend ✓)",
                "",
                "**🟢 Stage 2:** WaveTrend Confirmation",
                f"   • WT1: {wt['wt1'].iloc[-1]:.2f}",
                f"   • WT2: {wt['wt2'].iloc[-1]:.2f}",
                f"   • **Oversold zone cross detected** 🎯",
                "",
                "━━━━━━━━━━━━━━━━━━━━━━",
                f"📅 **Date:** {today_str}",
                "🚀 **ACTION: STRONG BUY CANDIDATE**",
                "━━━━━━━━━━━━━━━━━━━━━━",
            ]
            message = "\n".join(message_lines)
            
            try:
                telegram.send(message)
                logger.info("wavetrend_telegram_sent", symbol=symbol)
                
                # Remove from signals database
                page_id = symbol_to_page.get(symbol)
                if page_id:
                    notion.delete_page(page_id)
                    print(f"   🗑️  Removed {symbol} from signals")
                
                # Add to buy database (if configured)
                if cfg.notion.buy_database_id:
                    notion.add_to_buy(symbol, date.today().isoformat())
                    print(f"   ✅ Added {symbol} to BUY database")
            except Exception as e:
                logger.error("wavetrend_telegram_failed", symbol=symbol, error=str(e))
                print(f"   ⚠️  Failed to send Telegram: {e}")
        else:
            print("—")
        
        # Small delay to avoid rate limits
        if i < len(symbols):
            time.sleep(2)
    
    # Summary
    print(f"\n✅ WaveTrend scan complete!")
    print(f"   Checked: {len(symbols)} symbols")
    print(f"   Skipped: {len(skipped_buy)} (already in buy)")
    print(f"   Confirmed: {len(confirmed_signals)}")
    
    if confirmed_signals:
        print(f"\n🎯 Confirmed buy signals:")
        for s in confirmed_signals:
            print(f"   • {s}")
    
    logger.info("wavetrend_scan_complete", total=len(symbols), skipped=len(skipped_buy), confirmed=len(confirmed_signals))


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
            
            # Stage 1: Watchlist → Stoch RSI + MFI → Signals
            try:
                print("🔍 Stage 1: Checking watchlist (Stoch RSI + MFI)...\n")
                run_scan(cfg)
            except Exception as e:
                logger.error("stage1_scan_error", cycle=cycle, error=str(e))
                print(f"❌ Error in stage 1: {e}")
            
            print()  # Blank line between stages
            
            # Stage 2: Signals → WaveTrend → Buy
            try:
                print("🌊 Stage 2: Checking signals (WaveTrend)...\n")
                run_wavetrend_scan(cfg)
            except Exception as e:
                logger.error("stage2_scan_error", cycle=cycle, error=str(e))
                print(f"❌ Error in stage 2: {e}")
            
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
            print("🔍 Running two-stage scan once...\n")
            print("=" * 60)
            print("📊 Stage 1: Watchlist (Stoch RSI + MFI)")
            print("=" * 60 + "\n")
            run_scan(cfg)
            
            print("\n" + "=" * 60)
            print("🌊 Stage 2: Signals (WaveTrend)")
            print("=" * 60 + "\n")
            run_wavetrend_scan(cfg)
            
            print("\n✅ Two-stage scan complete!")
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
