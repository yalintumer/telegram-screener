"""Beautiful UI components using rich library"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.text import Text
from rich.live import Live
from typing import List, Dict, Any
from datetime import datetime

console = Console()


def print_header(title: str, subtitle: str = "") -> None:
    """Print a beautiful header banner"""
    text = Text(title, style="bold cyan", justify="center")
    if subtitle:
        text.append("\n" + subtitle, style="dim")
    
    panel = Panel(
        text,
        border_style="bright_blue",
        padding=(1, 2)
    )
    console.print(panel)


def print_success(message: str) -> None:
    """Print success message with checkmark"""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    """Print error message with X mark"""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print warning message with warning icon"""
    console.print(f"[bold yellow]⚠[/bold yellow]  {message}")


def print_info(message: str) -> None:
    """Print info message with info icon"""
    console.print(f"[bold blue]ℹ[/bold blue]  {message}")


def print_section(title: str) -> None:
    """Print a section separator"""
    console.print(f"\n[bold cyan]{'─' * 60}[/bold cyan]")
    console.print(f"[bold white]{title}[/bold white]")
    console.print(f"[bold cyan]{'─' * 60}[/bold cyan]\n")


def create_watchlist_table(watchlist: Dict[str, Any]) -> Table:
    """Create a beautiful table for watchlist display
    
    Args:
        watchlist: Dict of {symbol: {"added": "YYYY-MM-DD"}} or {symbol: "YYYY-MM-DD"}
    """
    table = Table(
        title="📋 Watchlist",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        show_lines=True
    )
    
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Symbol", style="bold cyan", width=10)
    table.add_column("Added Date", style="green", width=12)
    table.add_column("Days Ago", style="yellow", width=10, justify="right")
    
    # Parse watchlist format (handle both dict and string values)
    items = []
    for symbol, value in watchlist.items():
        if isinstance(value, dict):
            date_str = value.get('added', '')
        else:
            date_str = value
        items.append((symbol, date_str))
    
    # Sort by date (newest first)
    sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
    
    for idx, (symbol, date_str) in enumerate(sorted_items, 1):
        try:
            added_date = datetime.fromisoformat(date_str)
            days_ago = (datetime.now() - added_date).days
            
            # Color code based on age
            if days_ago < 2:
                days_style = "bold green"
            elif days_ago < 4:
                days_style = "yellow"
            else:
                days_style = "red"
            
            table.add_row(
                str(idx),
                symbol,
                date_str,
                f"[{days_style}]{days_ago}d[/{days_style}]"
            )
        except (ValueError, TypeError):
            table.add_row(str(idx), symbol, date_str, "[dim]?[/dim]")
    
    return table


def create_signal_table(signals: List[Dict[str, Any]]) -> Table:
    """Create a beautiful table for signal display"""
    table = Table(
        title="🎯 Buy Signals Detected",
        title_style="bold green",
        show_header=True,
        header_style="bold magenta",
        border_style="green",
        show_lines=True
    )
    
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Symbol", style="bold cyan", width=10)
    table.add_column("RSI", style="yellow", width=8, justify="right")
    table.add_column("K", style="blue", width=8, justify="right")
    table.add_column("D", style="blue", width=8, justify="right")
    table.add_column("Signal", style="bold green", width=10)
    
    for idx, signal in enumerate(signals, 1):
        rsi = signal.get('rsi', 'N/A')
        k = signal.get('k', 'N/A')
        d = signal.get('d', 'N/A')
        
        # Format values
        rsi_str = f"{rsi:.1f}" if isinstance(rsi, (int, float)) else str(rsi)
        k_str = f"{k:.2f}" if isinstance(k, (int, float)) else str(k)
        d_str = f"{d:.2f}" if isinstance(d, (int, float)) else str(d)
        
        table.add_row(
            str(idx),
            signal['symbol'],
            rsi_str,
            k_str,
            d_str,
            "🚀 BUY"
        )
    
    return table


def create_scan_progress() -> Progress:
    """Create a beautiful progress bar for scanning"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
        TimeRemainingColumn(),
        console=console,
        expand=True
    )


def print_stats_panel(stats: Dict[str, Any]) -> None:
    """Print statistics in a beautiful panel"""
    content = []
    
    for key, value in stats.items():
        # Format key (capitalize and add spaces)
        formatted_key = key.replace('_', ' ').title()
        
        # Format value
        if isinstance(value, float):
            formatted_value = f"{value:.2f}"
        else:
            formatted_value = str(value)
        
        content.append(f"[bold cyan]{formatted_key}:[/bold cyan] {formatted_value}")
    
    panel = Panel(
        "\n".join(content),
        title="📊 Statistics",
        title_align="left",
        border_style="yellow",
        padding=(1, 2)
    )
    console.print(panel)


def print_summary_box(
    title: str,
    added: List[str],
    removed: List[str],
    style: str = "green"
) -> None:
    """Print a summary box with added/removed items"""
    content = []
    
    if added:
        content.append(f"[bold green]➕ Added ({len(added)}):[/bold green]")
        for item in added[:10]:  # Show max 10
            content.append(f"   • {item}")
        if len(added) > 10:
            content.append(f"   [dim]... and {len(added) - 10} more[/dim]")
    
    if removed:
        if content:
            content.append("")  # Separator
        content.append(f"[bold red]➖ Removed ({len(removed)}):[/bold red]")
        for item in removed[:10]:  # Show max 10
            content.append(f"   • {item}")
        if len(removed) > 10:
            content.append(f"   [dim]... and {len(removed) - 10} more[/dim]")
    
    if not content:
        content.append("[dim]No changes[/dim]")
    
    panel = Panel(
        "\n".join(content),
        title=f"📋 {title}",
        title_align="left",
        border_style=style,
        padding=(1, 2)
    )
    console.print(panel)


def print_dry_run_banner() -> None:
    """Print a prominent DRY RUN banner"""
    text = Text("DRY RUN MODE", style="bold yellow on red", justify="center")
    text.append("\n", style="")
    text.append("No real changes will be made", style="dim", justify="center")
    
    panel = Panel(
        text,
        border_style="red",
        padding=(1, 4)
    )
    console.print(panel)
