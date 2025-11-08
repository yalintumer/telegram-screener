import argparse
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from .config import Config
from .capture import capture
from .ocr import extract_tickers, configure_tesseract
from . import watchlist
from .telegram_client import TelegramClient
from .indicators import stochastic_rsi, stoch_rsi_buy
from .logger import logger
from .exceptions import TVScreenerError, DataSourceError

# Import the correct data source based on config
def get_data_source(provider: str):
    """Get the appropriate data source function"""
    if provider == "yfinance":
        from .data_source_yfinance import daily_ohlc
        return daily_ohlc
    else:
        from .data_source import daily_ohlc
        return daily_ohlc


def cmd_capture(cfg: Config, dry_run: bool = False, click_coords: tuple[int, int] = None):
    """Capture screenshot, extract tickers, update watchlist"""
    try:
        logger.info("cmd.capture.start", dry_run=dry_run, click_coords=click_coords)
        
        # Configure tesseract if custom path provided
        if cfg.tesseract.path:
            configure_tesseract(cfg.tesseract.path, cfg.tesseract.lang)
        
        print("📸 Taking screenshot...")
        img = capture(cfg.screen.region, app_name=cfg.screen.app_name, click_before=click_coords)
        
        print("🔍 Extracting tickers with OCR...")
        tickers = extract_tickers(img, cfg.tesseract.config_str)
        
        # Cleanup screenshot
        try:
            os.remove(img)
            logger.debug("screenshot.removed", path=img)
        except Exception as e:
            logger.warning("screenshot.remove_failed", error=str(e))
        
        if dry_run:
            print(f"\n[DRY RUN] Found {len(tickers)} ticker(s): {', '.join(tickers)}")
            logger.info("cmd.capture.dry_run", tickers=tickers)
            return
        
        print(f"\n📋 Found {len(tickers)} ticker(s): {', '.join(tickers)}")
        
        added = watchlist.add(tickers)
        removed = watchlist.prune(cfg.data.max_watch_days)
        
        print(f"➕ Added to watchlist: {len(added)}")
        if added:
            for t in added:
                print(f"   • {t}")
        
        print(f"➖ Removed (expired): {len(removed)}")
        if removed:
            for t in removed:
                print(f"   • {t}")
        
        logger.info("cmd.capture.complete", 
                   captured=len(tickers),
                   added=len(added),
                   removed=len(removed))
        
    except TVScreenerError as e:
        logger.error("cmd.capture.failed", error=str(e))
        print(f"\n❌ Capture failed: {e}")
        raise


def _scan_symbol(symbol: str, cfg: Config) -> tuple[str, bool, str | None]:
    """
    Scan single symbol for buy signal
    
    Returns:
        (symbol, has_signal, error_message)
    """
    try:
        # Get appropriate data source function
        daily_ohlc_func = get_data_source(cfg.api.provider)
        df = daily_ohlc_func(symbol)
        
        if df is None or len(df) < 30:
            return symbol, False, "insufficient data"
        
        ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        if stoch_rsi_buy(ind):
            return symbol, True, None
        
        return symbol, False, None
        
    except DataSourceError as e:
        return symbol, False, str(e)
    except Exception as e:
        logger.exception("scan.symbol_error", symbol=symbol)
        return symbol, False, str(e)


def cmd_scan(cfg: Config, sleep_between: int = 15, dry_run: bool = False, parallel: bool = False):
    """Scan watchlist symbols for buy signals"""
    try:
        symbols = watchlist.all_symbols()
        
        if not symbols:
            print("\n⚠️  Watchlist is empty. Run 'capture' command first.")
            logger.warning("cmd.scan.empty_watchlist")
            return
        
        logger.info("cmd.scan.start",
                   symbol_count=len(symbols),
                   dry_run=dry_run,
                   parallel=parallel)
        
        print(f"\n🔍 Scanning {len(symbols)} symbol(s) for Stochastic RSI buy signals...")
        
        tg = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
        signals = []
        errors = []
        
        if parallel:
            # Parallel scanning (faster but harder on rate limits)
            print("⚡ Using parallel mode (max 3 concurrent)")
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(_scan_symbol, s, cfg): s for s in symbols}
                
                with tqdm(total=len(symbols), desc="Scanning", unit="symbol") as pbar:
                    for future in as_completed(futures):
                        symbol, has_signal, error = future.result()
                        
                        if error:
                            errors.append((symbol, error))
                            pbar.set_postfix_str(f"⚠️  {symbol}: {error[:30]}")
                        elif has_signal:
                            # Check grace period before sending
                            if watchlist.can_send_signal(symbol):
                                signals.append(symbol)
                                msg = f"🚀 *{symbol}* Stokastik RSI AL Sinyali"
                                
                                if not dry_run:
                                    try:
                                        tg.send(msg)
                                        watchlist.mark_signal_sent(symbol)  # Remove from watchlist after signal sent
                                        pbar.set_postfix_str(f"✅ {symbol} signal sent & removed from watchlist")
                                    except Exception as e:
                                        logger.error("telegram.send_failed", symbol=symbol, error=str(e))
                                        pbar.set_postfix_str(f"❌ {symbol} telegram failed")
                                else:
                                    print(f"\n[DRY RUN] {msg}")
                            else:
                                pbar.set_postfix_str(f"⏭️ {symbol} already processed")
                        
                        pbar.update(1)
        else:
            # Sequential scanning with progress bar
            with tqdm(symbols, desc="Scanning", unit="symbol") as pbar:
                for i, s in enumerate(pbar, start=1):
                    pbar.set_postfix_str(f"Checking {s}")
                    
                    symbol, has_signal, error = _scan_symbol(s, cfg)
                    
                    if error:
                        errors.append((symbol, error))
                        pbar.set_postfix_str(f"⚠️  {symbol}: {error[:30]}")
                    elif has_signal:
                        # Check grace period before sending
                        if watchlist.can_send_signal(symbol):
                            signals.append(symbol)
                            msg = f"🚀 *{symbol}* Stokastik RSI AL Sinyali"
                            
                            if not dry_run:
                                try:
                                    tg.send(msg)
                                    watchlist.mark_signal_sent(symbol)  # Remove from watchlist after signal sent
                                    pbar.set_postfix_str(f"✅ {symbol} signal sent & removed from watchlist")
                                except Exception as e:
                                    logger.error("telegram.send_failed", symbol=symbol, error=str(e))
                                    pbar.set_postfix_str(f"❌ {symbol} telegram failed")
                            else:
                                print(f"\n[DRY RUN] {msg}")
                        else:
                            pbar.set_postfix_str(f"⏭️ {symbol} already processed")
                    
                    # Rate limit delay (skip for last item)
                    if i < len(symbols):
                        time.sleep(sleep_between)
        
        # Summary
        print(f"\n✅ Scan complete!")
        print(f"📊 Buy signals found: {len(signals)}")
        if signals:
            for s in signals:
                print(f"   🎯 {s}")
        
        print(f"❌ Errors: {len(errors)}")
        if errors:
            for sym, err in errors[:5]:  # Show first 5 errors
                print(f"   ⚠️  {sym}: {err}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more")
        
        logger.info("cmd.scan.complete",
                   signals=len(signals),
                   errors=len(errors))
        
    except Exception as e:
        logger.error("cmd.scan.failed", error=str(e))
        print(f"\n❌ Scan failed: {e}")
        raise


def cmd_list(cfg: Config):
    """List current watchlist"""
    symbols = watchlist.all_symbols()
    
    if not symbols:
        print("\n📋 Watchlist is empty")
        return
    
    print(f"\n📋 Watchlist ({len(symbols)} symbol(s)):")
    for s in sorted(symbols):
        print(f"   • {s}")
    
    print(f"\n⚙️  Settings:")
    print(f"   Max watch days: {cfg.data.max_watch_days}")
    print(f"   API provider: {cfg.api.provider}")


def cmd_add(cfg: Config, symbols: list[str]):
    """Manually add symbols to watchlist"""
    symbols = [s.upper().strip() for s in symbols]
    
    print(f"\n➕ Adding {len(symbols)} symbol(s) to watchlist...")
    
    added = watchlist.add(symbols)
    
    if added:
        print(f"\n✅ Added {len(added)} symbol(s):")
        for s in added:
            print(f"   • {s}")
    else:
        print(f"\n⚠️  All symbols already in watchlist")
    
    # Show current watchlist
    all_symbols = watchlist.all_symbols()
    print(f"\n📋 Current watchlist ({len(all_symbols)} symbol(s)):")
    for s in sorted(all_symbols):
        print(f"   • {s}")


def cmd_remove(cfg: Config, symbols: list[str]):
    """Manually remove symbols from watchlist"""
    symbols = [s.upper().strip() for s in symbols]
    
    print(f"\n➖ Removing {len(symbols)} symbol(s) from watchlist...")
    
    w = watchlist._load()
    removed = []
    not_found = []
    
    for s in symbols:
        if s in w:
            del w[s]
            removed.append(s)
        else:
            not_found.append(s)
    
    watchlist._save(w)
    
    if removed:
        print(f"\n✅ Removed {len(removed)} symbol(s):")
        for s in removed:
            print(f"   • {s}")
    
    if not_found:
        print(f"\n⚠️  Not found in watchlist ({len(not_found)} symbol(s)):")
        for s in not_found:
            print(f"   • {s}")
    
    # Show current watchlist
    all_symbols = watchlist.all_symbols()
    if all_symbols:
        print(f"\n📋 Current watchlist ({len(all_symbols)} symbol(s)):")
        for s in sorted(all_symbols):
            print(f"   • {s}")
    else:
        print(f"\n📋 Watchlist is now empty")


def cmd_clear(cfg: Config):
    """Clear entire watchlist"""
    all_symbols = watchlist.all_symbols()
    
    if not all_symbols:
        print("\n📋 Watchlist is already empty")
        return
    
    print(f"\n⚠️  About to remove ALL {len(all_symbols)} symbol(s) from watchlist:")
    for s in sorted(all_symbols):
        print(f"   • {s}")
    
    response = input("\n❓ Are you sure? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        watchlist._save({})
        print(f"\n✅ Watchlist cleared! Removed {len(all_symbols)} symbol(s)")
    else:
        print("\n❌ Cancelled")


def cmd_debug(cfg: Config, symbol: str):
    """Debug a specific symbol - show detailed Stochastic RSI values"""
    try:
        print(f"\n🔍 Debugging {symbol}...")
        
        # Get data
        daily_ohlc_func = get_data_source(cfg.api.provider)
        df = daily_ohlc_func(symbol)
        
        if df is None or len(df) < 30:
            print(f"❌ Insufficient data for {symbol}")
            return
        
        print(f"✅ Got {len(df)} days of data")
        
        # Calculate indicators
        ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        # Show last 5 rows
        print(f"\n📊 Last 5 days of Stochastic RSI:")
        print(ind.tail(5).to_string())
        
        # Check signal
        has_signal = stoch_rsi_buy(ind)
        
        print(f"\n🎯 Signal Analysis:")
        if len(ind) >= 2:
            prev = ind.iloc[-2]
            last = ind.iloc[-1]
            
            print(f"   Previous: K={prev.k:.4f}, D={prev.d:.4f}")
            print(f"   Current:  K={last.k:.4f}, D={last.d:.4f}")
            
            cross_up = prev.k <= prev.d and last.k > last.d
            oversold = (last.k < 0.2 or last.d < 0.2 or 
                       prev.k < 0.2 or prev.d < 0.2)
            
            print(f"\n   Cross Up: {'✅ YES' if cross_up else '❌ NO'}")
            if cross_up:
                print(f"      (K crossed from {prev.k:.4f} to {last.k:.4f})")
                print(f"      (D was {prev.d:.4f}, now {last.d:.4f})")
            
            print(f"   Oversold: {'✅ YES' if oversold else '❌ NO'}")
            if oversold:
                if last.k < 0.2:
                    print(f"      Current K ({last.k:.4f}) < 0.2")
                if last.d < 0.2:
                    print(f"      Current D ({last.d:.4f}) < 0.2")
                if prev.k < 0.2:
                    print(f"      Previous K ({prev.k:.4f}) < 0.2")
                if prev.d < 0.2:
                    print(f"      Previous D ({prev.d:.4f}) < 0.2")
            
            print(f"\n   🚀 BUY SIGNAL: {'✅ YES' if has_signal else '❌ NO'}")
            
            # Grace period check
            if has_signal:
                can_send = watchlist.can_send_signal(symbol)
                print(f"   Grace Period: {'✅ Can send' if can_send else '🔇 Recently sent'}")
        
    except Exception as e:
        logger.exception("cmd.debug.failed", symbol=symbol)
        print(f"\n❌ Debug failed: {e}")


def cmd_run(cfg: Config, interval: int = 3600, dry_run: bool = False, click_coords: tuple[int, int] = None):
    """Continuous mode: capture once, then scan periodically"""
    logger.info("cmd.run.start", interval=interval, dry_run=dry_run)
    
    print(f"\n🔄 Starting continuous mode")
    print(f"   Interval: {interval}s ({interval // 60} minutes)")
    print(f"   Dry run: {dry_run}")
    print(f"   Press Ctrl+C to stop\n")
    
    # Initial capture
    print("=" * 50)
    print("INITIAL CAPTURE")
    print("=" * 50)
    cmd_capture(cfg, dry_run=dry_run, click_coords=click_coords)
    
    cycle = 1
    try:
        while True:
            print(f"\n⏳ Waiting {interval}s before next scan... (Cycle {cycle})")
            time.sleep(interval)
            
            print("=" * 50)
            print(f"SCAN CYCLE {cycle}")
            print("=" * 50)
            
            try:
                cmd_scan(cfg, dry_run=dry_run)
                cycle += 1
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.exception("cmd.run.cycle_error", cycle=cycle)
                print(f"\n❌ Cycle {cycle} error: {e}")
                print("   Continuing to next cycle...")
                cycle += 1
                
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
        logger.info("cmd.run.stopped_by_user", cycles=cycle)


def main(argv: list[str] | None = None):
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="tv-ocr-screener",
        description="TradingView OCR Screener → Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s capture                    # Take screenshot and update watchlist
  %(prog)s scan --sleep 20            # Scan with 20s delay between symbols
  %(prog)s scan --parallel            # Fast parallel scanning
  %(prog)s run --interval 7200        # Continuous mode, scan every 2 hours
  %(prog)s list                       # Show current watchlist
  %(prog)s add AAPL MSFT GOOGL        # Add symbols to watchlist
  %(prog)s remove AAPL MSFT           # Remove symbols from watchlist
  %(prog)s clear                      # Clear entire watchlist (with confirmation)
  %(prog)s debug AAPL                 # Debug a specific symbol
  %(prog)s capture --dry-run          # Test mode (no changes)
        """
    )
    parser.add_argument("--config", default="config.example.yaml", 
                       help="Config file path (default: config.example.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run mode - no actual changes or messages sent")
    
    sub = parser.add_subparsers(dest="cmd", required=True, help="Command to run")
    
    # Capture command
    pcapture = sub.add_parser("capture", 
                  help="Take screenshot, extract tickers, update watchlist")
    pcapture.add_argument("--click", type=str, metavar="X,Y",
                         help="Click at coordinates X,Y before capture (e.g., --click 150,50)")
    
    # Scan command
    pscan = sub.add_parser("scan",
                          help="Scan watchlist for Stochastic RSI buy signals")
    pscan.add_argument("--sleep", type=int, default=15,
                      help="Seconds to sleep between symbols (default: 15)")
    pscan.add_argument("--parallel", action="store_true",
                      help="Use parallel scanning (faster but risks rate limits)")
    
    # Run command
    prun = sub.add_parser("run",
                         help="Continuous mode: capture once, then scan periodically")
    prun.add_argument("--interval", type=int, default=3600,
                     help="Seconds between scans (default: 3600 = 1 hour)")
    prun.add_argument("--click", type=str, metavar="X,Y",
                     help="Click at coordinates X,Y before capture (e.g., --click 150,50)")
    
    # List command
    sub.add_parser("list",
                  help="Show current watchlist")
    
    # Add command
    padd = sub.add_parser("add",
                         help="Manually add symbols to watchlist")
    padd.add_argument("symbols", type=str, nargs="+",
                     help="Symbol(s) to add (e.g., AAPL MSFT GOOGL)")
    
    # Remove command
    premove = sub.add_parser("remove",
                            help="Manually remove symbols from watchlist")
    premove.add_argument("symbols", type=str, nargs="+",
                        help="Symbol(s) to remove (e.g., AAPL MSFT)")
    
    # Clear command
    sub.add_parser("clear",
                  help="Clear entire watchlist (with confirmation)")
    
    # Debug command
    pdebug = sub.add_parser("debug",
                           help="Debug a specific symbol - show detailed Stochastic RSI values")
    pdebug.add_argument("symbol", type=str,
                       help="Symbol to debug (e.g., AAPL)")
    
    args = parser.parse_args(argv)
    
    try:
        # Load config
        cfg = Config.load(args.config)
        
        # Parse click coordinates if provided
        click_coords = None
        if hasattr(args, 'click') and args.click:
            try:
                x, y = map(int, args.click.split(','))
                click_coords = (x, y)
                logger.info("click.coords.parsed", x=x, y=y)
            except Exception as e:
                print(f"⚠️  Invalid --click format (use X,Y): {args.click}")
                logger.error("click.coords.parse_error", error=str(e))
        
        # Execute command
        if args.cmd == "capture":
            cmd_capture(cfg, dry_run=args.dry_run, click_coords=click_coords)
        
        elif args.cmd == "scan":
            cmd_scan(cfg, 
                    sleep_between=args.sleep,
                    dry_run=args.dry_run,
                    parallel=args.parallel)
        
        elif args.cmd == "run":
            cmd_run(cfg, interval=args.interval, dry_run=args.dry_run, click_coords=click_coords)
        
        elif args.cmd == "list":
            cmd_list(cfg)
        
        elif args.cmd == "add":
            cmd_add(cfg, args.symbols)
        
        elif args.cmd == "remove":
            cmd_remove(cfg, args.symbols)
        
        elif args.cmd == "clear":
            cmd_clear(cfg)
        
        elif args.cmd == "debug":
            cmd_debug(cfg, args.symbol.upper())
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("main.fatal_error")
        print(f"\n💥 Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
