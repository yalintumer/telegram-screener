"""
Cache system for market cap and other semi-static data.

Features:
- Market cap caching (24 hours)
- Automatic expiration
- Persistence across restarts
"""

import json
from datetime import datetime
from pathlib import Path

from .logger import logger


class MarketCapCache:
    """Cache for market cap data with TTL"""

    def __init__(self, cache_file: str = "market_cap_cache.json", ttl_hours: int = 24):
        self.cache_file = Path(cache_file)
        self.ttl_hours = ttl_hours
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load cache from disk"""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error("cache.load_failed", error=str(e))
            return {}

    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error("cache.save_failed", error=str(e))

    def get(self, symbol: str) -> float | None:
        """
        Get cached market cap for symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Market cap value or None if not cached or expired
        """
        if symbol not in self.cache:
            return None

        entry = self.cache[symbol]
        cached_time = datetime.fromisoformat(entry["timestamp"])
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600

        if age_hours > self.ttl_hours:
            logger.debug("cache.expired", symbol=symbol, age_hours=age_hours)
            del self.cache[symbol]
            self._save_cache()
            return None

        logger.debug("cache.hit", symbol=symbol, age_hours=round(age_hours, 1))
        return entry["market_cap"]

    def set(self, symbol: str, market_cap: float):
        """
        Cache market cap for symbol.
        
        Args:
            symbol: Stock symbol
            market_cap: Market cap value in USD
        """
        self.cache[symbol] = {
            "market_cap": market_cap,
            "timestamp": datetime.now().isoformat()
        }
        self._save_cache()
        logger.debug("cache.set", symbol=symbol, market_cap=market_cap)

    def clear_expired(self):
        """Remove all expired entries from cache"""
        now = datetime.now()
        expired = []

        for symbol, entry in list(self.cache.items()):
            cached_time = datetime.fromisoformat(entry["timestamp"])
            age_hours = (now - cached_time).total_seconds() / 3600

            if age_hours > self.ttl_hours:
                expired.append(symbol)
                del self.cache[symbol]

        if expired:
            self._save_cache()
            logger.info("cache.expired_cleared", count=len(expired))

    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.cache:
            return {
                "total_entries": 0,
                "expired_entries": 0,
                "valid_entries": 0,
                "oldest_entry_hours": None,
                "newest_entry_hours": None
            }

        now = datetime.now()
        ages = []
        expired_count = 0

        for entry in self.cache.values():
            cached_time = datetime.fromisoformat(entry["timestamp"])
            age_hours = (now - cached_time).total_seconds() / 3600
            ages.append(age_hours)

            if age_hours > self.ttl_hours:
                expired_count += 1

        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "valid_entries": len(self.cache) - expired_count,
            "oldest_entry_hours": round(max(ages), 1) if ages else None,
            "newest_entry_hours": round(min(ages), 1) if ages else None,
            "cache_file": str(self.cache_file),
            "ttl_hours": self.ttl_hours
        }
