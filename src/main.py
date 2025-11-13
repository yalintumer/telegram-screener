import argparse
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
import pandas as pd
from .config import Config
from . import watchlist
from .telegram_client import TelegramClient
from .indicators import stochastic_rsi, stoch_rsi_buy
from .logger import logger
from .exceptions import TVScreenerError, DataSourceError
from .validation import sanitize_symbols
from .rate_limiter import AdaptiveRateLimiter
from . import ui

# Import the correct data source based on config
def get_data_source(provider: str) -> Callable[[str, int], pd.DataFrame]:
    """Get the appropriate data source function
    
    Args:
        provider: Data provider name ('yfinance' or 'alphavantage')
        
    Returns:
        Data fetching function that takes (symbol: str, days: int) -> DataFrame
    """
    if provider == "yfinance":
        from .data_source_yfinance import daily_ohlc
        return daily_ohlc
    else:
        from .data_source import daily_ohlc
        return daily_ohlc


def cmd_capture(cfg: Config, dry_run: bool = False, click_coords: tuple[int, int] = None):
    """Capture screenshot, extract tickers, update watchlist"""
    try:
        # Lazy import - only import when capture is actually used
        from .capture import capture
        from .ocr import extract_tickers, configure_tesseract
        
        logger.info("cmd.capture.start", dry_run=dry_run, click_coords=click_coords)
        
        if dry_run:
            ui.print_dry_run_banner()
        
        ui.print_header("📸 Screen Capture", "Extract tickers from TradingView screener")
        
        # Configure tesseract if custom path provided
        if cfg.tesseract.path:
            configure_tesseract(cfg.tesseract.path, cfg.tesseract.lang)
        
        ui.print_info("Taking screenshot...")
        img = capture(cfg.screen.region, app_name=cfg.screen.app_name, click_before=click_coords)
        
        ui.print_info("Extracting tickers with OCR...")
        tickers = extract_tickers(img, cfg.tesseract.config_str)
        
        # Cleanup screenshot
        try:
            os.remove(img)
            logger.debug("screenshot.removed", path=img)
        except Exception as e:
            logger.warning("screenshot.remove_failed", error=str(e))
        
        ui.print_success(f"Found {len(tickers)} ticker(s): {', '.join(tickers)}")
        
        if dry_run:
            logger.info("cmd.capture.dry_run", tickers=tickers)
            return
        
        # Local Mac: Skip grace period check - just send tickers to VM
        # VM will handle grace period validation when it processes them
        added = watchlist.add(tickers, skip_grace_check=True)
        removed = watchlist.prune(cfg.data.max_watch_days)
        
        ui.print_summary_box(
            "Watchlist Changes",
            added=added,
            removed=removed
        )
        
        logger.info("cmd.capture.complete", 
                   captured=len(tickers),
                   added=len(added),
                   removed=len(removed))
        
    except TVScreenerError as e:
        logger.error("cmd.capture.failed", error=str(e))
        ui.print_error(f"Capture failed: {e}")
        raise


def _scan_symbol(symbol: str, cfg: Config) -> tuple[str, bool, str | None]:
    """
    Scan single symbol for buy signal
    
    Args:
        symbol: Stock ticker symbol
        cfg: Application configuration
    
    Returns:
        tuple of (symbol, has_signal, error_message)
        - has_signal: True if buy signal detected
        - error_message: None if successful, error description if failed
    """
    try:
        # Get appropriate data source function
        daily_ohlc_func = get_data_source(cfg.api.provider)
        df = daily_ohlc_func(symbol)
        
        if df is None or len(df) < 30:
            logger.warning("scan.insufficient_data", symbol=symbol, rows=len(df) if df is not None else 0)
            return symbol, False, "insufficient data"
        
        ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        if stoch_rsi_buy(ind):
            logger.info("scan.signal_found", symbol=symbol)
            return symbol, True, None
        
        return symbol, False, None
        
    except DataSourceError as e:
        logger.error("scan.data_source_error", symbol=symbol, error=str(e))
        return symbol, False, f"data error: {str(e)}"
    
    except KeyError as e:
        logger.error("scan.missing_column", symbol=symbol, column=str(e))
        return symbol, False, f"missing data column: {str(e)}"
    
    except ValueError as e:
        logger.error("scan.value_error", symbol=symbol, error=str(e))
        return symbol, False, f"calculation error: {str(e)}"
        
    except Exception as e:
        logger.exception("scan.unexpected_error", symbol=symbol)
        return symbol, False, f"unexpected: {type(e).__name__}"


def cmd_scan(cfg: Config, sleep_between: int = 15, dry_run: bool = False, parallel: bool = False):
    """Scan watchlist symbols for buy signals with adaptive rate limiting"""
    try:
        # Clean up old signal history records (30+ days)
        removed = watchlist.cleanup_old_signals()
        if removed > 0:
            logger.info("signal_history.cleanup", removed_count=removed)
        
        # Get all symbols from watchlist
        all_symbols = watchlist.all_symbols()
        
        if not all_symbols:
            ui.print_warning("Watchlist is empty. Run 'capture' command first.")
            logger.warning("cmd.scan.empty_watchlist")
            return
        
        # Filter out symbols in grace period (VM-side filtering)
        symbols = []
        filtered_count = 0
        for symbol in all_symbols:
            can_send, reason = watchlist.can_send_signal_with_reason(symbol)
            if can_send:
                symbols.append(symbol)
            else:
                logger.info("scan.grace_period_skip", symbol=symbol, reason=reason)
                filtered_count += 1
        
        if filtered_count > 0:
            ui.print_info(f"⏰ Skipped {filtered_count} symbol(s) in grace period")
        
        if not symbols:
            ui.print_warning("All symbols are in grace period. Nothing to scan.")
            logger.warning("cmd.scan.all_in_grace_period", total=len(all_symbols))
            return
        
        logger.info("cmd.scan.start",
                   total_symbols=len(all_symbols),
                   scannable_symbols=len(symbols),
                   filtered=filtered_count,
                   dry_run=dry_run,
                   parallel=parallel)
        
        if dry_run:
            ui.print_dry_run_banner()
        
        ui.print_header("🔍 Signal Scanner", f"Scanning {len(symbols)} symbols for buy signals")
        
        tg = TelegramClient(cfg.telegram.bot_token, cfg.telegram.chat_id)
        signals = []
        errors = []
        
        # Adaptive rate limiter (starts at 1s delay, adjusts based on errors)
        rate_limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=5.0,
            backoff_factor=1.5,
            recovery_factor=0.9
        )
        
        if parallel:
            # Parallel scanning with better concurrency control
            max_workers = min(3, len(symbols))  # Don't spawn more workers than needed
            ui.print_info(f"Using parallel mode ({max_workers} concurrent workers)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_scan_symbol, s, cfg): s for s in symbols}
                
                with ui.create_scan_progress() as progress:
                    task = progress.add_task("[cyan]Scanning symbols...", total=len(symbols))
                    
                    for future in as_completed(futures):
                        symbol, has_signal, error = future.result()
                        
                        if error:
                            errors.append((symbol, error))
                            rate_limiter.report_error()
                        elif has_signal:
                            rate_limiter.report_success()
                            
                            # No need to check grace period - already filtered at scan start
                            signals.append(symbol)
                            msg = f"🚀 *{symbol}* Stokastik RSI AL Sinyali"
                            
                            if not dry_run:
                                try:
                                    tg.send(msg)
                                    watchlist.mark_signal_sent(symbol)
                                except Exception as e:
                                    logger.error("telegram.send_failed", symbol=symbol, error=str(e))
                        else:
                            rate_limiter.report_success()
                        
                        progress.update(task, advance=1)
                        
                        # Update description with rate limiter stats periodically
                        completed = progress.tasks[0].completed
                        if completed % 5 == 0:
                            stats = rate_limiter.get_stats()
                            progress.update(task, description=f"[cyan]Scanning (delay: {stats['current_delay']:.1f}s)...")
        else:
            # Sequential scanning with adaptive delays
            ui.print_info(f"Sequential mode (delay: {sleep_between}s between symbols)")
            
            with ui.create_scan_progress() as progress:
                task = progress.add_task("[cyan]Scanning symbols...", total=len(symbols))
                
                for i, s in enumerate(symbols, start=1):
                    # Apply rate limiting
                    rate_limiter.wait()
                    
                    symbol, has_signal, error = _scan_symbol(s, cfg)
                    
                    if error:
                        errors.append((symbol, error))
                        rate_limiter.report_error()
                    elif has_signal:
                        rate_limiter.report_success()
                        
                        # No need to check grace period - already filtered at scan start
                        signals.append(symbol)
                        msg = f"🚀 *{symbol}* Stokastik RSI AL Sinyali"
                        
                        if not dry_run:
                            try:
                                tg.send(msg)
                                watchlist.mark_signal_sent(symbol)
                            except Exception as e:
                                logger.error("telegram.send_failed", symbol=symbol, error=str(e))
                    else:
                        rate_limiter.report_success()
                    
                    progress.update(task, advance=1)
                    
                    # Update progress description with rate limit stats
                    if i % 3 == 0:
                        stats = rate_limiter.get_stats()
                        progress.update(task, description=f"[cyan]Scanning (delay: {stats['current_delay']:.1f}s)...")
        
        # Print rate limiter final stats
        final_stats = rate_limiter.get_stats()
        ui.print_stats_panel({
            'Current Delay': f"{final_stats['current_delay']:.2f}s",
            'Success Streak': final_stats['success_streak'],
            'Total Errors': final_stats['error_count']
        })
        
        # Summary
        ui.print_success(f"Scan complete! Found {len(signals)} buy signal(s)")
        
        if signals:
            # Show signals in a nice list
            ui.console.print("\n[bold green]🎯 Buy Signals:[/bold green]")
            for s in signals:
                ui.console.print(f"   • [cyan]{s}[/cyan]")
        
        if errors:
            ui.console.print(f"\n[bold yellow]⚠️  Errors ({len(errors)}):[/bold yellow]")
            for sym, err in errors[:5]:  # Show first 5 errors
                ui.console.print(f"   • [red]{sym}[/red]: {err[:60]}")
            if len(errors) > 5:
                ui.console.print(f"   [dim]... and {len(errors) - 5} more[/dim]")
        
        logger.info("cmd.scan.complete",
                   signals=len(signals),
                   errors=len(errors))
        
    except Exception as e:
        logger.error("cmd.scan.failed", error=str(e))
        ui.print_error(f"Scan failed: {e}")
        raise



def cmd_list(cfg: Config):
    """List current watchlist"""
    wl = watchlist._load()
    
    if not wl:
        ui.print_warning("Watchlist is empty")
        return
    
    ui.print_header("📋 Watchlist", f"{len(wl)} symbols")
    
    # Create and print beautiful table
    table = ui.create_watchlist_table(wl)
    ui.console.print(table)
    
    # Print settings info
    ui.console.print(f"\n[bold cyan]⚙️  Settings:[/bold cyan]")
    ui.console.print(f"   Max watch days: [yellow]{cfg.data.max_watch_days}[/yellow]")
    ui.console.print(f"   API provider: [yellow]{cfg.api.provider}[/yellow]")


def cmd_add(cfg: Config, symbols: list[str]):
    """Manually add symbols to watchlist"""
    ui.print_header("➕ Add Symbols", "Add symbols to watchlist")
    
    # Validate and sanitize input
    valid_symbols, invalid_symbols = sanitize_symbols(symbols)
    
    if invalid_symbols:
        ui.print_warning(f"Invalid symbol format (skipped {len(invalid_symbols)}):")
        for s in invalid_symbols:
            ui.console.print(f"   • [red]{s}[/red]")
    
    if not valid_symbols:
        ui.print_error("No valid symbols to add")
        return
    
    ui.print_info(f"Adding {len(valid_symbols)} symbol(s)...")
    
    added = watchlist.add(valid_symbols)
    
    if added:
        ui.print_success(f"Added {len(added)} symbol(s)")
        for s in added:
            ui.console.print(f"   • [cyan]{s}[/cyan]")
    else:
        ui.print_warning("All symbols already in watchlist")
    
    # Show current watchlist
    symbols = watchlist.all_symbols()
    if symbols:
        ui.console.print(f"\n[dim]Current watchlist: {len(symbols)} symbols[/dim]")


def cmd_remove(cfg: Config, symbols: list[str]):
    """Manually remove symbols from watchlist"""
    ui.print_header("➖ Remove Symbols", "Remove symbols from watchlist")
    
    # Validate and sanitize input
    valid_symbols, invalid_symbols = sanitize_symbols(symbols)
    
    if invalid_symbols:
        ui.print_warning(f"Invalid symbol format (skipped {len(invalid_symbols)}):")
        for s in invalid_symbols:
            ui.console.print(f"   • [red]{s}[/red]")
    
    if not valid_symbols:
        ui.print_error("No valid symbols to remove")
        return
    
    ui.print_info(f"Removing {len(valid_symbols)} symbol(s)...")
    
    w = watchlist._load()
    removed = []
    not_found = []
    
    for s in valid_symbols:
        if s in w:
            del w[s]
            removed.append(s)
        else:
            not_found.append(s)
    
    watchlist._save(w)
    
    if removed:
        ui.print_success(f"Removed {len(removed)} symbol(s)")
        for s in removed:
            ui.console.print(f"   • [cyan]{s}[/cyan]")
    
    if not_found:
        ui.print_warning(f"Not found in watchlist ({len(not_found)} symbols)")
        for s in not_found:
            ui.console.print(f"   • [dim]{s}[/dim]")
    
    # Show current watchlist
    symbols_left = watchlist.all_symbols()
    if symbols_left:
        ui.console.print(f"\n[dim]Remaining in watchlist: {len(symbols_left)} symbols[/dim]")
    else:
        ui.console.print(f"\n[dim]Watchlist is now empty[/dim]")


def cmd_clear(cfg: Config):
    """Clear entire watchlist"""
    all_symbols = watchlist.all_symbols()
    
    if not all_symbols:
        ui.print_warning("Watchlist is already empty")
        return
    
    ui.print_header("🗑️  Clear Watchlist", f"Remove ALL {len(all_symbols)} symbols")
    
    ui.console.print(f"\n[bold yellow]⚠️  About to remove ALL symbols:[/bold yellow]")
    for s in sorted(all_symbols)[:10]:  # Show first 10
        ui.console.print(f"   • [cyan]{s}[/cyan]")
    if len(all_symbols) > 10:
        ui.console.print(f"   [dim]... and {len(all_symbols) - 10} more[/dim]")
    
    response = ui.console.input("\n[bold]❓ Are you sure? (yes/no):[/bold] ").strip().lower()
    
    if response in ['yes', 'y']:
        watchlist._save({})
        ui.print_success(f"Watchlist cleared! Removed {len(all_symbols)} symbols")
    else:
        ui.print_info("Cancelled")


def cmd_debug(cfg: Config, symbol: str):
    """Debug a specific symbol - show detailed Stochastic RSI values"""
    try:
        ui.print_header(f"🔍 Debug: {symbol}", "Detailed Stochastic RSI analysis")
        
        # Get data
        ui.print_info(f"Fetching data for {symbol}...")
        daily_ohlc_func = get_data_source(cfg.api.provider)
        df = daily_ohlc_func(symbol)
        
        if df is None or len(df) < 30:
            ui.print_error(f"Insufficient data for {symbol}")
            return
        
        ui.print_success(f"Got {len(df)} days of data")
        
        # Calculate indicators
        ind = stochastic_rsi(df["Close"], rsi_period=14, stoch_period=14, k=3, d=3)
        
        # Show last 5 rows in a table
        from rich.table import Table
        table = Table(title="📊 Last 5 Days", show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("RSI", justify="right", style="yellow")
        table.add_column("K", justify="right", style="blue")
        table.add_column("D", justify="right", style="blue")
        
        for idx, row in ind.tail(5).iterrows():
            table.add_row(
                str(idx)[:10],
                f"{row.rsi:.2f}" if hasattr(row, 'rsi') else "N/A",
                f"{row.k:.4f}",
                f"{row.d:.4f}"
            )
        
        ui.console.print(table)
        
        # Check signal
        has_signal = stoch_rsi_buy(ind)
        
        ui.console.print(f"\n[bold cyan]🎯 Signal Analysis:[/bold cyan]")
        if len(ind) >= 2:
            prev = ind.iloc[-2]
            last = ind.iloc[-1]
            
            ui.console.print(f"   Previous: K=[blue]{prev.k:.4f}[/blue], D=[blue]{prev.d:.4f}[/blue]")
            ui.console.print(f"   Current:  K=[blue]{last.k:.4f}[/blue], D=[blue]{last.d:.4f}[/blue]")
            
            cross_up = prev.k <= prev.d and last.k > last.d
            oversold = (last.k < 0.2 or last.d < 0.2 or 
                       prev.k < 0.2 or prev.d < 0.2)
            
            ui.console.print(f"\n   Cross Up: {'[bold green]✅ YES[/bold green]' if cross_up else '[red]❌ NO[/red]'}")
            if cross_up:
                ui.console.print(f"      [dim](K crossed from {prev.k:.4f} to {last.k:.4f})[/dim]")
                ui.console.print(f"      [dim](D was {prev.d:.4f}, now {last.d:.4f})[/dim]")
            
            ui.console.print(f"   Oversold: {'[bold green]✅ YES[/bold green]' if oversold else '[red]❌ NO[/red]'}")
            if oversold:
                if last.k < 0.2:
                    ui.console.print(f"      [dim]Current K ({last.k:.4f}) < 0.2[/dim]")
                if last.d < 0.2:
                    ui.console.print(f"      [dim]Current D ({last.d:.4f}) < 0.2[/dim]")
                if prev.k < 0.2:
                    ui.console.print(f"      [dim]Previous K ({prev.k:.4f}) < 0.2[/dim]")
                if prev.d < 0.2:
                    ui.console.print(f"      [dim]Previous D ({prev.d:.4f}) < 0.2[/dim]")
            
            ui.console.print(f"\n   🚀 BUY SIGNAL: {'[bold green]✅ YES[/bold green]' if has_signal else '[red]❌ NO[/red]'}")
            
            # Grace period check
            if has_signal:
                can_send = watchlist.can_send_signal(symbol)
                ui.console.print(f"   Grace Period: {'[green]✅ Can send[/green]' if can_send else '[yellow]🔇 Recently sent[/yellow]'}")
        
    except Exception as e:
        logger.exception("cmd.debug.failed", symbol=symbol)
        ui.print_error(f"Debug failed: {e}")


def cmd_run(cfg: Config, interval: int = 3600, dry_run: bool = False, click_coords: tuple[int, int] = None):
    """Continuous mode: capture once, then scan periodically"""
    logger.info("cmd.run.start", interval=interval, dry_run=dry_run)
    
    if dry_run:
        ui.print_dry_run_banner()
    
    # Show run configuration
    ui.print_header("🔄 Continuous Mode", "Capture once, then scan periodically")
    
    ui.console.print(f"\n[bold cyan]⚙️  Configuration:[/bold cyan]")
    ui.console.print(f"   Interval: [yellow]{interval}s[/yellow] ([dim]{interval // 60} minutes[/dim])")
    ui.console.print(f"   Dry run: [yellow]{'Yes' if dry_run else 'No'}[/yellow]")
    ui.console.print(f"   [dim]Press Ctrl+C to stop[/dim]\n")
    
    # Initial capture
    ui.print_section("📸 Initial Capture")
    cmd_capture(cfg, dry_run=dry_run, click_coords=click_coords)
    
    cycle = 1
    try:
        while True:
            ui.console.print(f"\n[cyan]⏳ Waiting {interval}s before next scan... [dim](Cycle {cycle})[/dim][/cyan]")
            time.sleep(interval)
            
            ui.print_section(f"🔍 Scan Cycle {cycle}")
            
            try:
                cmd_scan(cfg, dry_run=dry_run)
                cycle += 1
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.exception("cmd.run.cycle_error", cycle=cycle)
                ui.print_error(f"Cycle {cycle} error: {e}")
                ui.console.print("   [dim]Continuing to next cycle...[/dim]")
                cycle += 1
                
    except KeyboardInterrupt:
        ui.console.print("\n\n[bold yellow]👋 Stopped by user[/bold yellow]")
        ui.print_info(f"Completed {cycle} cycles")
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
                ui.print_warning(f"Invalid --click format (use X,Y): {args.click}")
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
        ui.console.print("\n\n[bold yellow]👋 Interrupted by user[/bold yellow]")
        return 130
    except Exception as e:
        logger.exception("main.fatal_error")
        ui.print_error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
