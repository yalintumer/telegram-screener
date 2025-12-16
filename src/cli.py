"""CLI entry point for Telegram Stock Screener.

This module handles argument parsing and command dispatch.
Extracted from main.py for better separation of concerns.
"""

import argparse
from collections.abc import Callable

from .config import Config
from .logger import logger


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Telegram Stock Screener: S&P 500 → Signals → Buy (2-stage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --once           Run both stages once
  python -m src.main --market-scan    Run Stage 1 only (S&P 500 filter)
  python -m src.main --wavetrend      Run Stage 2 only (WaveTrend confirmation)
  python -m src.main --interval 1800  Run every 30 minutes
        """
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Config file path (default: config.yaml)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Scan interval in seconds (default: 3600 = 1 hour)"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: continuous)"
    )

    parser.add_argument(
        "--market-scan",
        action="store_true",
        help="Run market scanner (Stage 1) - S&P 500 → Signals DB"
    )

    parser.add_argument(
        "--wavetrend",
        action="store_true",
        help="Run WaveTrend scan only (Stage 2) - Signals DB → Buy DB"
    )

    return parser


def run_cli(
    argv: list[str] | None = None,
    *,
    market_scan_fn: Callable[[Config], None],
    wavetrend_scan_fn: Callable[[Config], None],
    continuous_fn: Callable[[Config, int], None],
) -> int:
    """
    Parse arguments and dispatch to appropriate scan function.
    
    Args:
        argv: Command line arguments (None for sys.argv)
        market_scan_fn: Function to run Stage 1 market scan
        wavetrend_scan_fn: Function to run Stage 2 WaveTrend scan
        continuous_fn: Function to run continuous scanning
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
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
            market_scan_fn(cfg)
            print("\n✅ Market scan complete!")
            return 0

        # Run WaveTrend scan only (Stage 2)
        if args.wavetrend:
            print("🌊 Running WaveTrend Scan (Stage 2)...\n")
            print("=" * 60)
            print("📈 Signals DB → WaveTrend Confirm → Buy DB")
            print("=" * 60 + "\n")
            wavetrend_scan_fn(cfg)
            print("\n✅ WaveTrend scan complete!")
            return 0

        # Run both stages once
        if args.once:
            print("🔍 Running two-stage scan once...\n")

            print("=" * 60)
            print("📊 Stage 1: Market Scanner (S&P 500 → Signals DB)")
            print("=" * 60 + "\n")
            market_scan_fn(cfg)

            print("\n" + "=" * 60)
            print("🌊 Stage 2: WaveTrend (Signals DB → Buy DB)")
            print("=" * 60 + "\n")
            wavetrend_scan_fn(cfg)

            print("\n✅ Two-stage scan complete!")
            return 0

        # Continuous mode (default)
        continuous_fn(cfg, args.interval)
        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 130

    except Exception as e:
        logger.exception("fatal_error")
        print(f"❌ Fatal error: {e}")
        return 1


# For backwards compatibility: direct CLI entry
def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point (backwards compatible).
    
    Note: This imports from main.py to avoid circular imports.
    """
    # Late import to avoid circular dependency
    from . import main as main_module

    return run_cli(
        argv,
        market_scan_fn=main_module.run_market_scan,
        wavetrend_scan_fn=main_module.run_wavetrend_scan,
        continuous_fn=main_module.run_continuous,
    )
