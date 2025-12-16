"""Telegram Stock Screener - Main entry point.

This is the main module that ties everything together.
Most functionality has been extracted to:
- cli.py: Command-line interface
- scanner.py: Scan orchestration
- filters.py: Market and WaveTrend filters
"""

import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from .filters import (
    check_wavetrend_signal,
)
from .logger import logger
from .scanner import (
    run_continuous,
    run_market_scan,
    run_wavetrend_scan,
)

# =============================================================================
# Sentry Initialization (Error Tracking)
# =============================================================================
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

if SENTRY_DSN:
    sentry_logging = LoggingIntegration(
        level=None,
        event_level=None
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        release="telegram-screener@1.0.0",
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        integrations=[sentry_logging],
        before_send=lambda event, hint: event if event.get('level') in ('error', 'fatal') else None
    )
    logger.info("sentry.initialized", environment=ENVIRONMENT)


# =============================================================================
# Backwards compatibility aliases
# =============================================================================
# Alias for backwards compatibility
check_symbol_wavetrend = check_wavetrend_signal


# =============================================================================
# CLI Entry Point
# =============================================================================
def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Delegates to cli.py for argument parsing and dispatch.
    """
    from .cli import run_cli

    return run_cli(
        argv,
        market_scan_fn=run_market_scan,
        wavetrend_scan_fn=run_wavetrend_scan,
        continuous_fn=run_continuous,
    )


if __name__ == "__main__":
    exit(main())
