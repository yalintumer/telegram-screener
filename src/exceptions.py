"""Custom exceptions for TV OCR Screener with enhanced error context"""

from typing import Any


class TVScreenerError(Exception):
    """Base exception for screener errors with enhanced context
    
    Attributes:
        message: Error message
        context: Additional context dictionary (e.g., symbol, operation)
        original_error: Original exception if wrapped
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None,
                 original_error: Exception | None = None):
        self.message = message
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context"""
        msg = self.message
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            msg = f"{msg} [{ctx_str}]"
        if self.original_error:
            msg = f"{msg} (caused by: {type(self.original_error).__name__}: {self.original_error})"
        return msg


class OCRError(TVScreenerError):
    """OCR extraction failed
    
    Common causes:
    - Tesseract not installed or not in PATH
    - Invalid image format or corrupted file
    - Poor image quality (resolution, contrast)
    """
    pass


class DataSourceError(TVScreenerError):
    """Data source fetch failed
    
    Common causes:
    - Network connectivity issues
    - API rate limit exceeded
    - Invalid symbol or no data available
    - API key invalid or expired (for non-yfinance providers)
    """
    pass


class TelegramError(TVScreenerError):
    """Telegram API communication failed
    
    Common causes:
    - Invalid bot token or chat ID
    - Network connectivity issues
    - Rate limit exceeded (Telegram has strict limits)
    - Message too long (>4096 chars for Telegram)
    """
    pass


class ConfigError(TVScreenerError):
    """Configuration validation failed
    
    Common causes:
    - Missing or invalid config.yaml
    - Required fields missing
    - Invalid format (e.g., region coordinates)
    - Environment variables not set
    """
    pass


class ValidationError(TVScreenerError):
    """Input validation failed
    
    Common causes:
    - Invalid ticker symbol format
    - Out of range parameters
    - Invalid file paths
    """
    pass


class WatchlistError(TVScreenerError):
    """Watchlist operation failed
    
    Common causes:
    - File system permissions
    - Corrupted watchlist.json
    - Invalid date formats
    """
    pass

