"""Simplified Telegram screener - Notion → Stoch RSI → Telegram"""

import os
import time
import argparse
from datetime import date, datetime
from .config import Config
from .notion_client import NotionClient
from .telegram_client import TelegramClient
from .indicators import stochastic_rsi, stoch_rsi_buy, mfi, mfi_uptrend, wavetrend, wavetrend_buy, bollinger_bands
from .data_source_yfinance import daily_ohlc, weekly_ohlc
from .data_source_alpha_vantage import alpha_vantage_ohlc
from .logger import logger, set_correlation_id
from .market_symbols import get_sp500_symbols, get_market_cap_threshold
from .signal_tracker import SignalTracker
from .cache import MarketCapCache
from .analytics import Analytics
from .backup import NotionBackup
from .health import get_health
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import yfinance as yf

# Initialize Sentry for error tracking
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

if SENTRY_DSN:
    sentry_logging = LoggingIntegration(
        level=None,           # Capture nothing from logging
        event_level=None      # Send nothing as events (we'll capture manually)
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        release=f"telegram-screener@1.0.0",
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,
        send_default_pii=False,
        integrations=[sentry_logging],
        # Capture errors but not info/warning
        before_send=lambda event, hint: event if event.get('level') in ('error', 'fatal') else None
    )
    logger.info("sentry.initialized", environment=ENVIRONMENT)


def update_signal_performance(signal_tracker: SignalTracker, lookback_days: int = 7) -> dict:
    """
    Update performance metrics for recent signals
    
    Args:
        signal_tracker: SignalTracker instance
        lookback_days: Number of days to wait before evaluating signal (default 7)
    
    Returns:
        Dictionary with update statistics
    """
    updated = 0
    failed = 0
    
    # Iterate over signal_history (list of signal dicts)
    for signal in signal_tracker.data.get("signal_history", []):
        symbol = signal.get("symbol")
        if not symbol:
            continue
        
        # Skip if already evaluated
        if signal.get("performance"):
            continue
        
        # Check if enough time has passed
        try:
            signal_date = signal.get("date") or signal.get("tracking_start")
            if not signal_date:
                continue
            
            signal_datetime = datetime.fromisoformat(signal_date)
            days_since = (datetime.now() - signal_datetime).days
            
            if days_since < lookback_days:
                continue
            
            # Get current price and update performance
            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice')
            
            if current_price:
                signal_tracker.update_signal_performance(symbol, lookback_days)
                updated += 1
        except Exception as e:
            logger.warning("performance_update_failed", symbol=symbol, error=str(e))
            failed += 1
    
    return {"updated": updated, "failed": failed}


def check_symbol_wavetrend(symbol: str, use_multi_timeframe: bool = True) -> bool:
    """
    Check if symbol has WaveTrend buy signal (second-stage filter)
    
    Conditions:
    1. Daily: WaveTrend WT1 crosses above WT2 in oversold zone (< -53)
    2. Weekly (optional): WaveTrend must NOT be extremely overbought (WT1 < 60)
    
    Args:
        symbol: Stock ticker symbol
        use_multi_timeframe: If True, confirms daily signal with weekly trend
    
    Returns True if WaveTrend signal detected
    """
    try:
        logger.info("checking_wavetrend", symbol=symbol, multi_timeframe=use_multi_timeframe)
        
        # Get daily price data
        df_daily = daily_ohlc(symbol)
        
        if df_daily is None or len(df_daily) < 30:
            logger.warning("insufficient_data", symbol=symbol)
            return False
        
        # Calculate daily WaveTrend
        wt_daily = wavetrend(df_daily, channel_length=10, average_length=21)
        
        # Check for daily WaveTrend buy signal
        has_daily_signal = wavetrend_buy(wt_daily, lookback_days=3, oversold_level=-53)
        
        if not has_daily_signal:
            return False
        
        # Multi-timeframe confirmation (optional)
        if use_multi_timeframe:
            df_weekly = weekly_ohlc(symbol, weeks=52)
            
            if df_weekly is not None and len(df_weekly) >= 14:
                wt_weekly = wavetrend(df_weekly, channel_length=10, average_length=21)
                weekly_wt1 = float(wt_weekly['wt1'].iloc[-1])
                
                # Reject if weekly is extremely overbought (prevents buying at tops)
                if weekly_wt1 > 60:
                    logger.info("wavetrend_rejected_weekly", symbol=symbol,
                               daily_signal=True, weekly_wt1=weekly_wt1)
                    return False
                
                logger.info("wavetrend_multi_timeframe_confirmed", symbol=symbol,
                           daily_wt1=float(wt_daily['wt1'].iloc[-1]),
                           weekly_wt1=weekly_wt1)
            else:
                logger.warning("weekly_data_unavailable", symbol=symbol)
        
        if has_daily_signal:
            logger.info("wavetrend_signal_found", symbol=symbol,
                       wt1=float(wt_daily['wt1'].iloc[-1]),
                       wt2=float(wt_daily['wt2'].iloc[-1]))
        
        return has_daily_signal
        
    except Exception as e:
        logger.error("wavetrend_check_failed", symbol=symbol, error=str(e))
        return False


def check_market_filter(symbol: str, cache: MarketCapCache = None, alpha_vantage_key: str = None) -> dict:
    """
    Check if symbol passes market scanner filters (Stage 0).
    
    Uses hybrid approach:
    - yfinance: Market cap (fast, unlimited)
    - Alpha Vantage: Technical indicators (precise, if key provided)
    
    Filters:
    1. Market Cap >= 50B USD (cached for 24h)
    2. Stoch RSI (3,3,14,14) - D < 20
    3. Price < Bollinger Lower Band (20 period)
    4. MFI (14) <= 40
    
    Args:
        symbol: Stock symbol
        cache: Optional MarketCapCache instance for performance
        alpha_vantage_key: Optional Alpha Vantage API key for precise indicators
    
    Returns:
        dict with 'passed' (bool) and indicator values, or None if data unavailable
    """
    try:
        logger.info("market_filter_check", symbol=symbol, 
                   using_alpha_vantage=bool(alpha_vantage_key))
        
        # Get price data - use Alpha Vantage if available, else yfinance
        if alpha_vantage_key:
            df = alpha_vantage_ohlc(symbol, alpha_vantage_key, days=100)
            if df is None:
                # Fallback to yfinance
                logger.warning("alpha_vantage_failed_fallback_yfinance", symbol=symbol)
                df = daily_ohlc(symbol)
        else:
            df = daily_ohlc(symbol)
        
        if df is None or len(df) < 30:
            logger.warning("market_filter_insufficient_data", symbol=symbol)
            return None
        
        # 1. Check Market Cap >= 50B USD (with caching)
        market_cap = None
        if cache:
            market_cap = cache.get(symbol)
        
        if market_cap is None:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                market_cap = info.get('marketCap', 0)
                
                # Cache the result
                if cache and market_cap > 0:
                    cache.set(symbol, market_cap)
            
            except Exception as e:
                logger.warning("market_filter_market_cap_error", symbol=symbol, error=str(e))
                return None
        
        if market_cap < get_market_cap_threshold():
            logger.info("market_filter_market_cap_too_low", symbol=symbol, 
                       market_cap=market_cap, threshold=get_market_cap_threshold())
            return {'passed': False, 'reason': 'market_cap_too_low'}
        
        # 2. Calculate Stochastic RSI (3,3,14,14)
        stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        stoch_d = float(stoch_ind['d'].iloc[-1])
        stoch_k = float(stoch_ind['k'].iloc[-1])
        
        if stoch_d >= 20:
            logger.info("market_filter_stoch_not_oversold", symbol=symbol, stoch_d=stoch_d)
            return {'passed': False, 'reason': 'stoch_d_not_oversold', 'stoch_d': stoch_d}
        
        # 3. Check Bollinger Bands - Price < Lower Band
        bb = bollinger_bands(df['Close'], period=20, std_dev=2.0)
        current_price = float(df['Close'].iloc[-1])
        bb_lower = float(bb['lower'].iloc[-1])
        
        if current_price >= bb_lower:
            logger.info("market_filter_price_not_below_bb", symbol=symbol, 
                       price=current_price, bb_lower=bb_lower)
            return {'passed': False, 'reason': 'price_not_below_bb', 
                   'price': current_price, 'bb_lower': bb_lower}
        
        # 4. Check MFI <= 40
        mfi_values = mfi(df, period=14)
        mfi_current = float(mfi_values.iloc[-1])
        
        if mfi_current > 40:
            logger.info("market_filter_mfi_too_high", symbol=symbol, mfi=mfi_current)
            return {'passed': False, 'reason': 'mfi_too_high', 'mfi': mfi_current}
        
        # All filters passed!
        logger.info("market_filter_passed", symbol=symbol, 
                   market_cap=market_cap, stoch_d=stoch_d, stoch_k=stoch_k,
                   price=current_price, bb_lower=bb_lower, mfi=mfi_current)
        
        return {
            'passed': True,
            'market_cap': market_cap,
            'stoch_d': stoch_d,
            'stoch_k': stoch_k,
            'price': current_price,
            'bb_lower': bb_lower,
            'mfi': mfi_current
        }
        
    except Exception as e:
        logger.error("market_filter_check_failed", symbol=symbol, error=str(e))
        return None


def run_market_scan(cfg: Config) -> None:
    """
    Run combined market scanner (Stage 0+1): S&P 500 → filter + signal → Signals DB.
    
    This combines the old Stage 0 (market filter) and Stage 1 (signal check) into
    a single pass. Stocks that pass both filters go directly to Signals database.
    
    Filters (must pass ALL):
    1. Market Cap >= 50B USD (cached for 24h)
    2. Stoch RSI (3,3,14,14) - D < 20 (oversold)
    3. Price < Bollinger Lower Band (20 period)
    4. MFI (14) <= 40 (oversold)
    5. Stoch RSI bullish cross (K crosses above D in oversold zone)
    6. MFI in 3-day uptrend
    
    No Telegram notification - that happens in Stage 2 (WaveTrend confirmation).
    """
    logger.info("market_scan_started")
    
    # Initialize cache for market cap data
    cache = MarketCapCache()
    cache.clear_expired()
    cache_stats = cache.get_stats()
    logger.info("cache.initialized", **cache_stats)
    
    # Initialize clients
    notion = NotionClient(
        api_token=cfg.notion.api_token,
        database_id=cfg.notion.database_id,
        signals_database_id=cfg.notion.signals_database_id,
        buy_database_id=cfg.notion.buy_database_id
    )
    
    # Get symbols already in signals or buy databases (to avoid duplicates)
    existing_symbols = notion.get_all_symbols()
    existing_set = set(existing_symbols) if existing_symbols else set()
    
    # Get S&P 500 symbols
    sp500_symbols = get_sp500_symbols()
    logger.info("market_scan_symbols_loaded", count=len(sp500_symbols))
    
    # Track results
    filter_passed_count = 0
    signal_found_count = 0
    added_count = 0
    skipped_count = 0
    
    print(f"\n🔍 Market Scanner: Analyzing {len(sp500_symbols)} S&P 500 stocks...")
    print(f"📊 Stage 0 Filters: Market Cap ≥50B, Stoch RSI D<20, Price<BB Lower, MFI≤40")
    print(f"� Stage 1 Signal: Stoch RSI bullish cross + MFI 3-day uptrend")
    print(f"� Cache: {cache_stats['valid_entries']} valid entries")
    if existing_set:
        print(f"⏭️  Skipping: {len(existing_set)} symbols already in signals/buy")
    print()
    
    # Scan each symbol
    for i, symbol in enumerate(sp500_symbols, 1):
        # Progress indicator every 50 symbols
        if i % 50 == 0:
            print(f"   Progress: {i}/{len(sp500_symbols)} symbols scanned...")
        
        # Skip if already in signals or buy database
        if symbol in existing_set:
            skipped_count += 1
            continue
        
        # === STAGE 0: Market Filter ===
        result = check_market_filter(symbol, cache=cache)
        
        if not result or not result.get('passed'):
            continue
        
        filter_passed_count += 1
        
        # === STAGE 1: Signal Check (Stoch RSI cross + MFI uptrend) ===
        # We already have Stoch RSI from filter, check for bullish cross
        try:
            df = daily_ohlc(symbol)
            if df is None or len(df) < 30:
                continue
            
            # Calculate indicators
            stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
            mfi_values = mfi(df, period=14)
            
            # Check Stochastic RSI bullish cross
            has_stoch_signal = stoch_rsi_buy(stoch_ind)
            
            # Check MFI 3-day uptrend
            mfi_trending_up = mfi_uptrend(mfi_values, days=3)
            
            if has_stoch_signal and mfi_trending_up:
                signal_found_count += 1
                
                # Add directly to Signals database
                if notion.symbol_exists_in_signals(symbol):
                    print(f"   ℹ️  {symbol}: Already in signals (skipped)")
                else:
                    success = notion.add_to_signals(symbol, date.today().isoformat())
                    if success:
                        added_count += 1
                        print(f"   🆕 {symbol}: Added to Signals DB")
                        print(f"      Market Cap: ${result['market_cap']/1e9:.1f}B")
                        print(f"      Stoch RSI D: {result['stoch_d']:.1f}, K: {result['stoch_k']:.1f}")
                        print(f"      Price: ${result['price']:.2f} < BB Lower: ${result['bb_lower']:.2f}")
                        print(f"      MFI: {result['mfi']:.1f} (3-day uptrend ✓)")
                        
        except Exception as e:
            logger.warning("signal_check_failed", symbol=symbol, error=str(e))
            continue
        
        # Rate limiting
        time.sleep(0.5)
    
    # Update signal performance (evaluate signals from 7+ days ago)
    print("\n📊 Updating signal performance metrics...")
    signal_tracker = SignalTracker()
    perf_update = update_signal_performance(signal_tracker, lookback_days=7)
    print(f"   ✅ Performance updated: {perf_update['updated']} signals evaluated")
    if perf_update['failed'] > 0:
        print(f"   ⚠️  Failed to evaluate: {perf_update['failed']} signals")
    
    # Record analytics
    analytics = Analytics()
    analytics.record_market_scan(filter_passed_count, added_count, 0)  # No updates, direct add
    
    # Backup Notion databases
    print("\n💾 Backing up Notion databases...")
    backup = NotionBackup()
    databases = {
        "signals": cfg.notion.signals_database_id,
        "buy": cfg.notion.buy_database_id
    }
    backup_files = backup.backup_all(notion, databases)
    
    deleted = backup.cleanup_old_backups(days=30)
    if deleted > 0:
        print(f"   🗑️  Cleaned up {deleted} old backups (>30 days)")
    
    backup_stats = backup.get_backup_stats()
    print(f"   📦 Total backups: {backup_stats['total_backups']} ({backup_stats['total_size_mb']:.1f} MB)")
    
    # Check weekly report
    if analytics.should_send_weekly_report():
        print("\n📧 Generating weekly report...")
        report = analytics.generate_weekly_report(signal_tracker)
        print(report)
        
        try:
            telegram = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
            telegram.send(f"```\n{report}\n```")
            analytics.mark_report_sent()
            print("   ✅ Weekly report sent via Telegram")
        except Exception as e:
            logger.error("weekly_report_failed", error=str(e))
            print(f"   ⚠️  Failed to send weekly report: {e}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"📈 Market Scan Complete!")
    print(f"=" * 60)
    print(f"   Scanned: {len(sp500_symbols)} S&P 500 stocks")
    print(f"   Skipped: {skipped_count} (already in signals/buy)")
    print(f"   Passed filters: {filter_passed_count}")
    print(f"   Signals found: {signal_found_count}")
    print(f"   Added to Signals DB: {added_count}")
    print(f"=" * 60 + "\n")
    
    logger.info("market_scan_completed", 
                scanned=len(sp500_symbols), skipped=skipped_count,
                filter_passed=filter_passed_count, signals=signal_found_count, added=added_count,
                performance_updated=perf_update['updated'])


def check_symbol(symbol: str) -> dict | None:
    """
    Check if symbol has Stochastic RSI + MFI buy signal
    
    Conditions:
    1. Stochastic RSI bullish cross in oversold zone
    2. MFI in uptrend for last 3 days (volume-weighted momentum)
    
    Returns:
        dict with indicator data if signal found, None otherwise
        Keys: 'stoch_ind', 'mfi_values', 'df'
    """
    try:
        logger.info("checking_symbol", symbol=symbol)
        
        # Get price data
        df = daily_ohlc(symbol)
        
        if df is None or len(df) < 30:
            logger.warning("insufficient_data", symbol=symbol)
            return None
        
        # Calculate Stochastic RSI
        stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        # Check Stochastic RSI signal
        has_stoch_signal = stoch_rsi_buy(stoch_ind)
        
        if not has_stoch_signal:
            return None
        
        # Calculate MFI (Money Flow Index)
        mfi_values = mfi(df, period=14)
        
        # Check if MFI is in 3-day uptrend
        mfi_trending_up = mfi_uptrend(mfi_values, days=3)
        
        if has_stoch_signal and mfi_trending_up:
            logger.info("signal_found", symbol=symbol, 
                       mfi_current=float(mfi_values.iloc[-1]),
                       stoch_k=float(stoch_ind['k'].iloc[-1]))
            # Return indicator data to avoid duplicate API calls
            return {
                'stoch_ind': stoch_ind,
                'mfi_values': mfi_values,
                'df': df
            }
        
        # Log why signal was rejected
        if has_stoch_signal and not mfi_trending_up:
            logger.info("signal_rejected_mfi", symbol=symbol, 
                       reason="MFI not in 3-day uptrend",
                       mfi_current=float(mfi_values.iloc[-1]))
        
        return None
        
    except Exception as e:
        logger.error("check_failed", symbol=symbol, error=str(e))
        return None


def run_wavetrend_scan(cfg: Config):
    """
    Second-stage scan: Check signals database for WaveTrend confirmation
    
    This scans the first-stage signals (Stoch RSI + MFI) and applies WaveTrend filter.
    Confirmed signals move to buy database.
    
    Features:
    - Alert fatigue prevention (max 5 alerts/day)
    - Symbol cooldown (7 days between same symbol alerts)
    - Signal performance tracking
    """
    
    # Initialize clients and trackers
    notion = NotionClient(
        cfg.notion.api_token,
        cfg.notion.database_id,
        cfg.notion.signals_database_id,
        cfg.notion.buy_database_id
    )
    telegram = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
    signal_tracker = SignalTracker()
    
    # Cleanup old signals (older than 7 days or without date)
    print("🧹 Cleaning up old signals...")
    removed_count = notion.cleanup_old_signals(max_age_days=7)
    if removed_count > 0:
        print(f"   Removed {removed_count} old/stale signals")
    
    # Show daily stats
    daily_stats = signal_tracker.get_daily_stats()
    logger.info("signal_tracker.daily_stats", **daily_stats)
    print(f"\n📊 Alert Stats Today: {daily_stats['alerts_sent']}/5 sent, {daily_stats['symbols_in_cooldown']} in cooldown\n")
    
    logger.info("wavetrend_scan_started")
    
    # Fetch symbols from signals database
    logger.info("fetching_signals_from_notion")
    symbols, symbol_to_page = notion.get_signals()
    
    # Remove duplicates from signals list
    unique_symbols = list(dict.fromkeys(symbols))  # Preserves order
    if len(unique_symbols) < len(symbols):
        logger.info("signal_duplicates_removed", original=len(symbols), unique=len(unique_symbols))
    symbols = unique_symbols
    
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
            # Check alert limits BEFORE confirming
            can_alert, reason = signal_tracker.can_send_alert(symbol, daily_limit=5, cooldown_days=7)
            
            if not can_alert:
                print(f"⚠️  SIGNAL BUT ALERT BLOCKED: {reason}")
                logger.warning("alert_blocked", symbol=symbol, reason=reason)
                # Still move to buy database but don't send Telegram
                confirmed_signals.append(symbol)
                
                # Remove from signals and add to buy database silently
                if cfg.notion.buy_database_id:
                    page_id = symbol_to_page.get(symbol)
                    if page_id:
                        notion.delete_page(page_id)
                    
                    if notion.symbol_exists_in_buy(symbol):
                        print(f"   ℹ️  {symbol} already in BUY (skipped)")
                    else:
                        notion.add_to_buy(symbol, date.today().isoformat())
                        print(f"   ✅ Added {symbol} to BUY (no alert)")
                continue
            
            print("✅ CONFIRMED!")
            confirmed_signals.append(symbol)
            
            # Get indicator values for message
            df = daily_ohlc(symbol)
            if df is None or len(df) < 30:
                logger.warning("confirmed_signal_data_unavailable", symbol=symbol)
                continue
            wt = wavetrend(df, channel_length=10, average_length=21)
            stoch = stochastic_rsi(df['Close'])
            mfi_val = mfi(df)
            current_price = float(df['Close'].iloc[-1])
            
            # Get historical performance stats if available
            perf_stats = signal_tracker.get_signal_stats(symbol)
            perf_text = ""
            if perf_stats['evaluated'] > 0:
                perf_text = f"\n📊 **Historical Performance ({symbol}):**\n   • Win Rate: {perf_stats['win_rate']}% | Avg Return: {perf_stats['avg_return']}%\n"
            
            # Build rich Telegram notification
            today_str = date.today().strftime('%Y-%m-%d')
            tradingview_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
            
            message_lines = [
                "🚨🚨🚨 **BUY SIGNAL CONFIRMED!** 🚨🚨🚨",
                "━━━━━━━━━━━━━━━━━━━━━━",
                "",
                f"**📈 SYMBOL: `{symbol}`**",
                f"💰 **Price:** ${current_price:.2f}",
                f"📊 [View on TradingView]({tradingview_link})",
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
            ]
            
            if perf_text:
                message_lines.append(perf_text)
            
            message_lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━",
                f"📅 **Date:** {today_str}",
                "🚀 **ACTION: STRONG BUY CANDIDATE**",
                "━━━━━━━━━━━━━━━━━━━━━━",
            ])
            
            message = "\n".join(message_lines)
            
            try:
                telegram.send(message)
                logger.info("wavetrend_telegram_sent", symbol=symbol)
                
                # Record alert in tracker
                signal_data = {
                    "price": current_price,
                    "stoch_k": float(stoch['k'].iloc[-1]),
                    "stoch_d": float(stoch['d'].iloc[-1]),
                    "mfi": float(mfi_val.iloc[-1]),
                    "wt1": float(wt['wt1'].iloc[-1]),
                    "wt2": float(wt['wt2'].iloc[-1])
                }
                signal_tracker.record_alert(symbol, signal_data)
                
                # Remove from signals database
                page_id = symbol_to_page.get(symbol)
                if page_id:
                    notion.delete_page(page_id)
                    print(f"   🗑️  Removed {symbol} from signals")
                
                # Add to buy database (if configured and not already exists)
                if cfg.notion.buy_database_id:
                    if notion.symbol_exists_in_buy(symbol):
                        print(f"   ℹ️  {symbol} already in BUY database (skipped)")
                    else:
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
    
    # Record analytics
    analytics = Analytics()
    analytics.record_stage2_scan(
        checked=len(symbols) - len(skipped_buy),
        confirmed=len(confirmed_signals)
    )
    
    logger.info("wavetrend_scan_complete", total=len(symbols), skipped=len(skipped_buy), confirmed=len(confirmed_signals))


def run_continuous(cfg: Config, interval: int = 3600):
    """
    Run scanner continuously at specified interval.
    
    New simplified 2-stage architecture:
    - Stage 1: Market scan (S&P 500 → filter + signal → Signals DB) - once per day
    - Stage 2: WaveTrend confirmation (Signals DB → Buy DB) - every cycle
    """
    
    print(f"🔄 Continuous mode started")
    print(f"   Interval: {interval}s ({interval // 60} minutes)")
    print(f"   Stage 1 (Market Scan): Daily (first cycle of each day)")
    print(f"   Stage 2 (WaveTrend): Every cycle")
    print(f"   Press Ctrl+C to stop\n")
    
    cycle = 1
    last_market_scan_date = None  # Track when we last ran market scan
    health = get_health()
    
    try:
        while True:
            # Set correlation ID for this scan cycle
            cid = set_correlation_id(f"cycle-{cycle}-{datetime.now().strftime('%H%M%S')}")
            scan_start = time.time()
            symbols_scanned = 0
            signals_found = 0
            
            health.scan_started(cycle)
            logger.info("scan_cycle_started", cycle=cycle)
            
            print(f"{'='*60}")
            print(f"📊 Scan Cycle {cycle} [{cid}]")
            print(f"{'='*60}\n")
            
            try:
                # Stage 1: Market Scanner (once per day)
                # S&P 500 → filter + signal check → Signals DB
                today = date.today()
                if last_market_scan_date != today:
                    try:
                        print("🔍 Stage 1: Daily Market Scanner (S&P 500 → Signals DB)...\n")
                        result = run_market_scan(cfg)
                        if result:
                            symbols_scanned = result.get('symbols_checked', 0)
                            signals_found += result.get('signals_found', 0)
                        last_market_scan_date = today
                        print()
                    except Exception as e:
                        logger.error("stage1_market_scan_error", cycle=cycle, error=str(e))
                        print(f"❌ Error in market scan: {e}\n")
                        sentry_sdk.capture_exception(e)
                else:
                    print("ℹ️  Stage 1: Market scan already done today, skipping...\n")
                
                # Stage 2: Signals → WaveTrend → Buy
                try:
                    print("🌊 Stage 2: Checking signals (WaveTrend → Buy DB)...\n")
                    result = run_wavetrend_scan(cfg)
                    if result:
                        signals_found += result.get('confirmed', 0)
                except Exception as e:
                    logger.error("stage2_scan_error", cycle=cycle, error=str(e))
                    print(f"❌ Error in stage 2: {e}")
                    sentry_sdk.capture_exception(e)
                
                # Update health with success
                scan_duration = time.time() - scan_start
                health.scan_completed(symbols_scanned, signals_found, scan_duration)
                
            except Exception as e:
                health.scan_failed(str(e))
                logger.exception("scan_cycle_failed", cycle=cycle)
                sentry_sdk.capture_exception(e)
            
            cycle += 1
            
            print(f"\n⏳ Waiting {interval}s until next scan...")
            health.heartbeat()
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped after {cycle-1} cycles")
        logger.info("stopped_by_user", cycles=cycle-1)


def main(argv: list[str] | None = None):
    """CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Telegram Stock Screener: S&P 500 → Signals → Buy (2-stage)"
    )
    
    parser.add_argument("--config", default="config.yaml",
                       help="Config file path (default: config.yaml)")
    
    parser.add_argument("--interval", type=int, default=3600,
                       help="Scan interval in seconds (default: 3600 = 1 hour)")
    
    parser.add_argument("--once", action="store_true",
                       help="Run once and exit (default: continuous)")
    
    parser.add_argument("--market-scan", action="store_true",
                       help="Run market scanner (Stage 1) - S&P 500 → Signals DB")
    
    parser.add_argument("--wavetrend", action="store_true",
                       help="Run WaveTrend scan only (Stage 2) - Signals DB → Buy DB")
    
    args = parser.parse_args(argv)
    
    try:
        # Load config
        cfg = Config.load(args.config)
        
        # Run market scanner only (Stage 1)
        if args.market_scan:
            print("🔍 Running Market Scanner (Stage 1)...\n")
            print("=" * 60)
            print("📊 S&P 500 → Filter + Signal → Signals DB")
            print("=" * 60 + "\n")
            run_market_scan(cfg)
            print("\n✅ Market scan complete!")
            return 0
        
        # Run WaveTrend scan only (Stage 2)
        if args.wavetrend:
            print("🌊 Running WaveTrend Scan (Stage 2)...\n")
            print("=" * 60)
            print("📈 Signals DB → WaveTrend Confirm → Buy DB")
            print("=" * 60 + "\n")
            run_wavetrend_scan(cfg)
            print("\n✅ WaveTrend scan complete!")
            return 0
        
        # Run both stages once
        if args.once:
            print("🔍 Running two-stage scan once...\n")
            
            print("=" * 60)
            print("📊 Stage 1: Market Scanner (S&P 500 → Signals DB)")
            print("=" * 60 + "\n")
            run_market_scan(cfg)
            
            print("\n" + "=" * 60)
            print("🌊 Stage 2: WaveTrend (Signals DB → Buy DB)")
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
