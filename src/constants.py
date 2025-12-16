"""
Central constants for the Telegram Screener application.
All magic numbers and configurable thresholds are defined here.
"""

# =============================================================================
# HTTP & NETWORKING
# =============================================================================
NOTION_TIMEOUT = 30             # Notion API timeout (seconds)
TELEGRAM_TIMEOUT = 10           # Telegram API timeout (seconds)
DEFAULT_RETRY_DELAY = 1.0       # Base delay for retries (seconds)
MAX_RETRY_DELAY = 30.0          # Maximum retry delay (seconds)
MAX_RETRY_ATTEMPTS = 3          # Maximum retry attempts
CONNECTION_POOL_SIZE = 10       # HTTP connection pool size
YFINANCE_BATCH_SIZE = 50        # Symbols per batch for yfinance
BATCH_SLEEP_SECONDS = 1.0       # Sleep between batches (seconds)


# =============================================================================
# RATE LIMITING
# =============================================================================
YFINANCE_RATE_LIMIT = 60        # Requests per minute
NOTION_RATE_LIMIT = 30          # Requests per minute
TELEGRAM_RATE_LIMIT = 20        # Requests per minute
ALPHA_VANTAGE_RATE_LIMIT = 5    # Requests per minute (free tier)


# =============================================================================
# MARKET CAP FILTER
# =============================================================================
MARKET_CAP_THRESHOLD = 50_000_000_000  # 50B USD minimum market cap


# =============================================================================
# STOCHASTIC RSI PARAMETERS
# =============================================================================
STOCH_RSI_PERIOD = 14          # RSI calculation period
STOCH_PERIOD = 14              # Stochastic period
STOCH_K_SMOOTH = 3             # K line smoothing
STOCH_D_SMOOTH = 3             # D line smoothing
STOCH_OVERSOLD = 0.2           # Oversold threshold (20%)
STOCH_OVERBOUGHT = 0.8         # Overbought threshold (80%)


# =============================================================================
# WAVETREND PARAMETERS
# =============================================================================
WAVETREND_CHANNEL_LENGTH = 10   # Channel length
WAVETREND_AVERAGE_LENGTH = 21   # Average length
WAVETREND_OVERSOLD = -53        # Oversold threshold
WAVETREND_OVERBOUGHT = 60       # Overbought threshold (for weekly rejection)
WAVETREND_EXTREME_OVERSOLD = -60  # Extreme oversold


# =============================================================================
# MFI (MONEY FLOW INDEX) PARAMETERS
# =============================================================================
MFI_PERIOD = 14                 # MFI calculation period
MFI_OVERSOLD = 40               # Oversold threshold for Stage 0 filter


# =============================================================================
# LOOKBACK PERIODS (DAYS)
# =============================================================================
SIGNAL_LOOKBACK_DAYS = 5        # Days to look back for signals
MFI_UPTREND_DAYS = 3            # Days to check MFI uptrend
SIGNAL_MAX_AGE_DAYS = 7         # Max age for signals before cleanup
ALERT_COOLDOWN_DAYS = 7         # Days between same symbol alerts
PERFORMANCE_LOOKBACK_DAYS = 7   # Days to evaluate signal performance
BACKUP_RETENTION_DAYS = 30      # Days to keep backup files


# =============================================================================
# ALERT LIMITS
# =============================================================================
DAILY_ALERT_LIMIT = 5           # Max alerts per day to prevent fatigue


# =============================================================================
# DATA REQUIREMENTS
# =============================================================================
MIN_DATA_POINTS = 30            # Minimum data points required for analysis
WEEKLY_DATA_WEEKS = 52          # Weeks of weekly data to fetch


# =============================================================================
# BOLLINGER BANDS
# =============================================================================
BOLLINGER_PERIOD = 20           # Bollinger Band period
BOLLINGER_STD_DEV = 2.0         # Standard deviation multiplier
