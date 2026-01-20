"""Scanner orchestration for two-stage stock screening.

This module contains the high-level scan orchestration:
- Stage 1 (Market Scan): S&P 500 → filters → Signals DB
- Stage 2 (WaveTrend Scan): Signals DB → WaveTrend confirmation → Buy DB

Extracted from main.py for better separation of concerns.
"""

import time
from datetime import date, datetime

import sentry_sdk
import yfinance as yf

from .analytics import Analytics
from .backup import NotionBackup
from .cache import MarketCapCache
from .config import Config
from .constants import BATCH_SLEEP_SECONDS
from .data_source_yfinance import daily_ohlc
from .filters import check_market_filter, check_wavetrend_signal
from .health import get_health
from .indicators import mfi, mfi_uptrend, stoch_rsi_buy, stochastic_rsi, wavetrend
from .logger import logger, set_correlation_id
from .market_symbols import get_sp500_symbols
from .notion_client import NotionClient
from .signal_tracker import SignalTracker
from .telegram_client import TelegramClient


def update_signal_performance(signal_tracker: SignalTracker, lookback_days: int = 7) -> dict:
    """
    Update performance metrics for recent signals.

    Args:
        signal_tracker: SignalTracker instance
        lookback_days: Number of days to wait before evaluating signal (default 7)

    Returns:
        Dictionary with update statistics
    """
    updated = 0
    failed = 0

    for signal in signal_tracker.data.get("signal_history", []):
        symbol = signal.get("symbol")
        if not symbol:
            continue

        if signal.get("performance"):
            continue

        try:
            signal_date = signal.get("date") or signal.get("tracking_start")
            if not signal_date:
                continue

            signal_datetime = datetime.fromisoformat(signal_date)
            days_since = (datetime.now() - signal_datetime).days

            if days_since < lookback_days:
                continue

            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice')

            if current_price:
                signal_tracker.update_signal_performance(symbol, lookback_days)
                updated += 1
        except Exception as e:
            logger.warning("performance_update_failed", symbol=symbol, error=str(e))
            failed += 1

    return {"updated": updated, "failed": failed}


def run_market_scan(cfg: Config) -> dict | None:
    """
    Run Stage 1 market scanner: S&P 500 → filter + signal → Signals DB.

    Filters (must pass ALL):
    1. Market Cap >= 50B USD (cached for 24h)
    2. Stoch RSI (3,3,14,14) - D < 20 (oversold)
    3. Price < Bollinger Lower Band (20 period)
    4. MFI (14) <= 40 (oversold)
    5. Stoch RSI bullish cross (K crosses above D in oversold zone)
    6. MFI in 3-day uptrend

    Returns:
        dict with scan statistics, or None on error
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
    print("📊 Stage 0 Filters: Market Cap ≥50B, Stoch RSI D<20, Price<BB Lower, MFI≤40")
    print("📈 Stage 1 Signal: Stoch RSI bullish cross + MFI 3-day uptrend")
    print(f"💾 Cache: {cache_stats['valid_entries']} valid entries")
    if existing_set:
        print(f"⏭️  Skipping: {len(existing_set)} symbols already in signals/buy")
    print()

    # Scan each symbol
    for i, symbol in enumerate(sp500_symbols, 1):
        if i % 50 == 0:
            print(f"   Progress: {i}/{len(sp500_symbols)} symbols scanned...")

        if symbol in existing_set:
            skipped_count += 1
            continue

        # === STAGE 0: Market Filter ===
        result = check_market_filter(symbol, cache=cache)

        if not result or not result.get('passed'):
            continue

        filter_passed_count += 1

        # === STAGE 1: Signal Check (Stoch RSI cross + MFI uptrend) ===
        try:
            df = daily_ohlc(symbol)
            if df is None or len(df) < 30:
                continue

            stoch_ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
            mfi_values = mfi(df, period=14)

            has_stoch_signal = stoch_rsi_buy(stoch_ind)
            mfi_trending_up = mfi_uptrend(mfi_values, days=3)

            if has_stoch_signal and mfi_trending_up:
                signal_found_count += 1

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

    # Update signal performance
    print("\n📊 Updating signal performance metrics...")
    signal_tracker = SignalTracker()
    perf_update = update_signal_performance(signal_tracker, lookback_days=7)
    print(f"   ✅ Performance updated: {perf_update['updated']} signals evaluated")
    if perf_update['failed'] > 0:
        print(f"   ⚠️  Failed to evaluate: {perf_update['failed']} signals")

    # Record analytics
    analytics = Analytics()
    analytics.record_market_scan(filter_passed_count, added_count, 0)
    analytics.record_stage1_scan(
        checked=filter_passed_count,  # Only those that passed market filter get Stage 1 check
        passed=signal_found_count
    )

    # Backup Notion databases
    print("\n💾 Backing up Notion databases...")
    backup = NotionBackup()
    databases = {
        "signals": cfg.notion.signals_database_id,
        "buy": cfg.notion.buy_database_id
    }
    backup.backup_all(notion, databases)

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
    print("\n" + "=" * 60)
    print("📈 Market Scan Complete!")
    print("=" * 60)
    print(f"   Scanned: {len(sp500_symbols)} S&P 500 stocks")
    print(f"   Skipped: {skipped_count} (already in signals/buy)")
    print(f"   Passed filters: {filter_passed_count}")
    print(f"   Signals found: {signal_found_count}")
    print(f"   Added to Signals DB: {added_count}")
    print("=" * 60 + "\n")

    logger.info("market_scan_completed",
                scanned=len(sp500_symbols), skipped=skipped_count,
                filter_passed=filter_passed_count, signals=signal_found_count, added=added_count,
                performance_updated=perf_update['updated'])

    return {
        "symbols_checked": len(sp500_symbols),
        "skipped": skipped_count,
        "filter_passed": filter_passed_count,
        "signals_found": signal_found_count,
        "added": added_count
    }


def run_wavetrend_scan(cfg: Config) -> dict | None:
    """
    Run Stage 2 scan: Check signals database for WaveTrend confirmation.

    Features:
    - Alert fatigue prevention (max 5 alerts/day)
    - Symbol cooldown (7 days between same symbol alerts)
    - Signal performance tracking

    Returns:
        dict with scan statistics, or None on error
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

    # Cleanup old signals
    print("🧹 Cleaning up old signals...")
    removed_count = notion.cleanup_old_signals(max_age_days=7)
    if removed_count > 0:
        print(f"   Removed {removed_count} old/stale signals")

    # Cleanup old buys
    print("🧹 Cleaning up old buys...")
    removed_buys = notion.cleanup_old_buys(max_age_days=15)
    if removed_buys > 0:
        print(f"   Removed {removed_buys} old buy entries")

    # Show daily stats
    daily_stats = signal_tracker.get_daily_stats()
    logger.info("signal_tracker.daily_stats", **daily_stats)
    print(f"\n📊 Alert Stats Today: {daily_stats['alerts_sent']}/5 sent, {daily_stats['symbols_in_cooldown']} in cooldown\n")

    logger.info("wavetrend_scan_started")

    # Fetch symbols from signals database
    symbols, symbol_to_page = notion.get_signals()

    # Remove duplicates
    unique_symbols = list(dict.fromkeys(symbols))
    if len(unique_symbols) < len(symbols):
        logger.info("signal_duplicates_removed", original=len(symbols), unique=len(unique_symbols))
    symbols = unique_symbols

    if not symbols:
        print("⚠️  Signals database is empty")
        return {"checked": 0, "confirmed": 0}

    # Get symbols already in buy database
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

    # Check each symbol
    confirmed_signals = []
    skipped_buy = []

    for i, symbol in enumerate(symbols, 1):
        print(f"🌊 [{i}/{len(symbols)}] Checking WaveTrend for {symbol}...", end=" ")

        if symbol in buy_symbols:
            print("⏭️  (already in buy)")
            skipped_buy.append(symbol)
            continue

        has_wt_signal = check_wavetrend_signal(symbol)

        if has_wt_signal:
            can_alert, reason = signal_tracker.can_send_alert(symbol, daily_limit=5, cooldown_days=7)

            if not can_alert:
                print(f"⚠️  SIGNAL BUT ALERT BLOCKED: {reason}")
                logger.warning("alert_blocked", symbol=symbol, reason=reason)
                confirmed_signals.append(symbol)

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

            # Get historical performance
            perf_stats = signal_tracker.get_signal_stats(symbol)
            perf_text = ""
            if perf_stats['evaluated'] > 0:
                perf_text = f"\n📊 **Historical Performance ({symbol}):**\n   • Win Rate: {perf_stats['win_rate']}% | Avg Return: {perf_stats['avg_return']}%\n"

            # Build Telegram notification
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
                "   • **Oversold zone cross detected** 🎯",
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

                signal_data = {
                    "price": current_price,
                    "stoch_k": float(stoch['k'].iloc[-1]),
                    "stoch_d": float(stoch['d'].iloc[-1]),
                    "mfi": float(mfi_val.iloc[-1]),
                    "wt1": float(wt['wt1'].iloc[-1]),
                    "wt2": float(wt['wt2'].iloc[-1])
                }
                signal_tracker.record_alert(symbol, signal_data)

                page_id = symbol_to_page.get(symbol)
                if page_id:
                    notion.delete_page(page_id)
                    print(f"   🗑️  Removed {symbol} from signals")

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

        if i < len(symbols):
            time.sleep(BATCH_SLEEP_SECONDS)

    # Summary
    print("\n✅ WaveTrend scan complete!")
    print(f"   Checked: {len(symbols)} symbols")
    print(f"   Skipped: {len(skipped_buy)} (already in buy)")
    print(f"   Confirmed: {len(confirmed_signals)}")

    if confirmed_signals:
        print("\n🎯 Confirmed buy signals:")
        for s in confirmed_signals:
            print(f"   • {s}")

    # Record analytics
    analytics = Analytics()
    analytics.record_stage2_scan(
        checked=len(symbols) - len(skipped_buy),
        confirmed=len(confirmed_signals)
    )

    logger.info("wavetrend_scan_complete", total=len(symbols), skipped=len(skipped_buy), confirmed=len(confirmed_signals))

    return {
        "checked": len(symbols) - len(skipped_buy),
        "skipped": len(skipped_buy),
        "confirmed": len(confirmed_signals)
    }


def run_continuous(cfg: Config, interval: int = 3600) -> None:
    """
    Run scanner continuously at specified interval.

    New simplified 2-stage architecture:
    - Stage 1: Market scan (S&P 500 → filter + signal → Signals DB) - once per day
    - Stage 2: WaveTrend confirmation (Signals DB → Buy DB) - every cycle

    Args:
        cfg: Application configuration
        interval: Scan interval in seconds (default: 3600 = 1 hour)
    """
    print("🔄 Continuous mode started")
    print(f"   Interval: {interval}s ({interval // 60} minutes)")
    print("   Stage 1 (Market Scan): Daily (first cycle of each day)")
    print("   Stage 2 (WaveTrend): Every cycle")
    print("   Press Ctrl+C to stop\n")

    cycle = 1
    last_market_scan_date = None
    health = get_health()

    try:
        while True:
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
