import argparse
import time
import os
import subprocess
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
from .health import HealthMonitor
from . import ui

# Import the correct data source based on config
def get_data_source(provider: str) -> Callable[[str, int], pd.DataFrame]:
    """Get the appropriate data source function
    
    Args:
        provider: Data provider name (currently only 'yfinance' is supported)
        
    Returns:
        Data fetching function that takes (symbol: str, days: int) -> DataFrame
        
    Raises:
        ValueError: If unsupported provider is specified
    """
    if provider == "yfinance":
        from .data_source_yfinance import daily_ohlc
        return daily_ohlc
    else:
        # Only yfinance is supported now - it's free and unlimited
        raise ValueError(f"Unsupported data provider: {provider}. Only 'yfinance' is supported.")


def send_tickers_to_vm(tickers: list[str], cfg: Config) -> tuple[list[str], list[str]]:
    """Send extracted tickers to VM via SSH
    
    This function connects to the VM and executes the 'add' command remotely.
    The VM will handle grace period validation and watchlist updates.
    
    Args:
        tickers: List of ticker symbols to add
        cfg: Application configuration with vm_ssh settings
        
    Returns:
        Tuple of (added_symbols, skipped_symbols)
        
    Raises:
        TVScreenerError: If SSH connection or remote command fails or vm_ssh not configured
    """
    if not tickers:
        return [], []
    
    if not cfg.vm_ssh:
        raise TVScreenerError("vm_ssh not configured in config.yaml - cannot send tickers to VM")
    
    host = cfg.vm_ssh.host
    user = cfg.vm_ssh.user
    path = cfg.vm_ssh.project_path
    
    # Build SSH command to add tickers on VM
    # Format: ssh user@host "cd path && ./venv/bin/python -m src.main add SYMBOL1 SYMBOL2 ..."
    tickers_str = " ".join(tickers)
    ssh_cmd = [
        "ssh",
        f"{user}@{host}",
        f'cd {path} && ./venv/bin/python -m src.main add {tickers_str}'
    ]
    
    logger.info("vm.send_tickers", tickers=tickers, host=host)
    
    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            logger.error("vm.send_failed", error=error_msg)
            raise TVScreenerError(f"Failed to send tickers to VM: {error_msg}")
        
        # Parse output to determine which were added vs skipped
        # Expected output format from cmd_add includes lines like:
        # "✓ Added: SYMBOL" or "⊗ Skipped (grace period): SYMBOL"
        added = []
        skipped = []
        for line in result.stdout.splitlines():
            if "Added:" in line or "✓" in line:
                # Extract symbol from line
                for ticker in tickers:
                    if ticker in line:
                        added.append(ticker)
                        break
            elif "Skipped" in line or "grace period" in line.lower():
                for ticker in tickers:
                    if ticker in line:
                        skipped.append(ticker)
                        break
        
        # If we couldn't parse specific results, assume all were processed
        if not added and not skipped:
            added = tickers
        
        logger.info("vm.send_complete", added=len(added), skipped=len(skipped))
        return added, skipped
        
    except subprocess.TimeoutExpired:
        logger.error("vm.send_timeout")
        raise TVScreenerError("SSH command timed out after 30 seconds")
    except Exception as e:
        logger.error("vm.send_exception", error=str(e))
        raise TVScreenerError(f"Failed to connect to VM: {e}")


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
        
        # Record capture statistics
        HealthMonitor.record_capture(len(tickers))
        
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
        
        # Send tickers to VM via SSH - VM owns watchlist and handles grace periods
        ui.print_info("Sending tickers to VM...")
        added, skipped = send_tickers_to_vm(tickers, cfg)
        
        # Show results
        if added:
            ui.print_success(f"✅ Sent to VM: {', '.join(added)}")
        if skipped:
            ui.print_warning(f"⏭️  Skipped (grace period): {', '.join(skipped)}")
        if not added and not skipped:
            ui.print_info("No tickers processed")
        
        logger.info("cmd.capture.complete", 
                   captured=len(tickers),
                   added=len(added),
                   skipped=len(skipped))
        
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
        
        # Record scan statistics
        HealthMonitor.record_scan(
            symbols_scanned=len(symbols),
            signals_found=len(signals),
            errors=len(errors)
        )
        
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


def cmd_status(cfg: Config):
    """Show system health and statistics"""
    ui.print_header("📊 System Status", "Health monitoring and statistics")
    
    try:
        status = HealthMonitor.get_status()
        
        # Overall status
        ui.console.print(f"\n[bold cyan]⚡ System Status:[/bold cyan] ", end="")
        if status['status'] == 'healthy':
            ui.console.print("[bold green]✓ Healthy[/bold green]")
        elif status['status'] == 'idle':
            ui.console.print("[yellow]○ Idle (empty watchlist)[/yellow]")
        else:
            ui.console.print("[red]✗ Unknown[/red]")
        
        # Watchlist info
        wl_info = status['watchlist']
        ui.console.print(f"\n[bold cyan]📋 Watchlist:[/bold cyan]")
        ui.console.print(f"   Total Symbols: [yellow]{wl_info['total_symbols']}[/yellow]")
        
        if wl_info['total_symbols'] > 0:
            ui.console.print(f"   Age Distribution:")
            for age_range, count in wl_info['age_distribution'].items():
                if count > 0:
                    ui.console.print(f"      {age_range} days: [cyan]{count}[/cyan] symbol(s)")
        
        # Signal history
        hist_info = status['signal_history']
        ui.console.print(f"\n[bold cyan]📈 Signal History:[/bold cyan]")
        ui.console.print(f"   Total Records: [yellow]{hist_info['total_records']}[/yellow]")
        
        # Statistics
        stats = status['stats']
        if stats:
            ui.console.print(f"\n[bold cyan]📊 Statistics:[/bold cyan]")
            
            if 'last_capture' in stats:
                last_cap = stats['last_capture']
                ui.console.print(f"   Last Capture:")
                ui.console.print(f"      Time: [green]{last_cap['timestamp'][:19]}[/green]")
                ui.console.print(f"      Symbols: [cyan]{last_cap['symbols_extracted']}[/cyan]")
            
            if 'last_scan' in stats:
                last_scan = stats['last_scan']
                ui.console.print(f"   Last Scan:")
                ui.console.print(f"      Time: [green]{last_scan['timestamp'][:19]}[/green]")
                ui.console.print(f"      Scanned: [cyan]{last_scan['symbols_scanned']}[/cyan]")
                ui.console.print(f"      Signals: [green]{last_scan['signals_found']}[/green]")
                ui.console.print(f"      Errors: [red]{last_scan['errors']}[/red]")
            
            if 'total_scans' in stats:
                ui.console.print(f"   Totals:")
                ui.console.print(f"      Total Scans: [yellow]{stats['total_scans']}[/yellow]")
                ui.console.print(f"      Total Signals: [green]{stats.get('total_signals', 0)}[/green]")
                ui.console.print(f"      Total Captures: [yellow]{stats.get('total_captures', 0)}[/yellow]")
        else:
            ui.console.print(f"\n[dim]No statistics available yet[/dim]")
        
        # Config info
        ui.console.print(f"\n[bold cyan]⚙️  Configuration:[/bold cyan]")
        ui.console.print(f"   API Provider: [yellow]{cfg.api.provider}[/yellow]")
        ui.console.print(f"   Max Watch Days: [yellow]{cfg.data.max_watch_days}[/yellow]")
        ui.console.print(f"   Log Level: [yellow]{cfg.log_level}[/yellow]")
        
    except Exception as e:
        logger.exception("cmd.status.failed")
        ui.print_error(f"Status check failed: {e}")


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
    parser.add_argument("--config", default="config.yaml", 
                       help="Config file path (default: config.yaml)")
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
    
    # Status command
    sub.add_parser("status",
                  help="Show system health and statistics")
    
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
        
        elif args.cmd == "status":
            cmd_status(cfg)
        
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
