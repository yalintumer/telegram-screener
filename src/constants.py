"""
Central constants for the Telegram Screener application.
All magic numbers and configurable thresholds are defined here.
"""

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
