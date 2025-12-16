"""
Simple rate limiter for external API calls.
Thread-safe, no external dependencies.
"""
import threading
import time
from collections import defaultdict

from .constants import (
    ALPHA_VANTAGE_RATE_LIMIT,
    NOTION_RATE_LIMIT,
    TELEGRAM_RATE_LIMIT,
    YFINANCE_RATE_LIMIT,
)
from .logger import logger


class RateLimiter:
    """
    Token bucket rate limiter with per-service tracking.
    
    Usage:
        limiter = RateLimiter()
        limiter.wait("yfinance")  # Blocks if rate limit exceeded
        # ... make API call
    """

    # Default limits per service (requests per minute)
    DEFAULT_LIMITS = {
        "yfinance": YFINANCE_RATE_LIMIT,
        "notion": NOTION_RATE_LIMIT,
        "telegram": TELEGRAM_RATE_LIMIT,
        "alpha_vantage": ALPHA_VANTAGE_RATE_LIMIT,
    }

    def __init__(self, custom_limits: dict | None = None):
        self._limits = {**self.DEFAULT_LIMITS, **(custom_limits or {})}
        self._tokens = defaultdict(lambda: {"count": 0, "last_reset": time.time()})
        self._lock = threading.Lock()

    def wait(self, service: str, cost: int = 1) -> float:
        """
        Wait if necessary to respect rate limit, then consume tokens.
        
        Args:
            service: Service name (yfinance, notion, telegram, etc.)
            cost: Number of tokens to consume (default: 1)
            
        Returns:
            Seconds waited (0 if no wait needed)
        """
        limit = self._limits.get(service, 60)
        window = 60.0  # 1 minute window

        with self._lock:
            now = time.time()
            bucket = self._tokens[service]

            # Reset bucket if window passed
            elapsed = now - bucket["last_reset"]
            if elapsed >= window:
                bucket["count"] = 0
                bucket["last_reset"] = now

            # Check if we need to wait
            if bucket["count"] + cost > limit:
                wait_time = window - elapsed
                if wait_time > 0:
                    logger.warning(
                        "rate_limit.waiting",
                        service=service,
                        wait_seconds=round(wait_time, 1),
                        current_count=bucket["count"],
                        limit=limit
                    )
                    # Release lock while sleeping
                    self._lock.release()
                    try:
                        time.sleep(wait_time)
                    finally:
                        self._lock.acquire()

                    # Reset after wait
                    bucket["count"] = 0
                    bucket["last_reset"] = time.time()

                    bucket["count"] += cost
                    return wait_time

            bucket["count"] += cost
            return 0.0

    def get_remaining(self, service: str) -> int:
        """Get remaining requests for a service in current window."""
        limit = self._limits.get(service, 60)
        with self._lock:
            bucket = self._tokens[service]
            elapsed = time.time() - bucket["last_reset"]
            if elapsed >= 60:
                return limit
            return max(0, limit - bucket["count"])

    def get_stats(self) -> dict:
        """Get current rate limit stats for all services."""
        stats = {}
        with self._lock:
            for service, bucket in self._tokens.items():
                limit = self._limits.get(service, 60)
                elapsed = time.time() - bucket["last_reset"]
                stats[service] = {
                    "used": bucket["count"],
                    "limit": limit,
                    "remaining": max(0, limit - bucket["count"]),
                    "resets_in": max(0, 60 - elapsed)
                }
        return stats


# Global singleton instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(service: str, cost: int = 1) -> float:
    """
    Convenience function to rate limit a service call.
    
    Usage:
        rate_limit("yfinance")
        response = yf.Ticker(symbol).history(...)
    """
    return get_rate_limiter().wait(service, cost)
