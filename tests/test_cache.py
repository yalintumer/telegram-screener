"""Tests for cache module."""

import json
from datetime import datetime, timedelta

import pytest

from src.cache import MarketCapCache


class TestMarketCapCacheInit:
    """Tests for MarketCapCache initialization."""

    def test_creates_empty_cache_when_file_not_exists(self, tmp_path):
        """Should create empty cache when file doesn't exist."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        assert cache.cache == {}

    def test_loads_existing_cache_from_file(self, tmp_path):
        """Should load existing cache data from file."""
        cache_file = tmp_path / "cache.json"
        existing_data = {"AAPL": {"market_cap": 3000000000000, "timestamp": datetime.now().isoformat()}}
        cache_file.write_text(json.dumps(existing_data))

        cache = MarketCapCache(cache_file=str(cache_file))

        assert "AAPL" in cache.cache
        assert cache.cache["AAPL"]["market_cap"] == 3000000000000

    def test_handles_corrupted_json_file(self, tmp_path):
        """Should return empty cache when JSON is corrupted."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json {{{")

        cache = MarketCapCache(cache_file=str(cache_file))

        assert cache.cache == {}

    def test_custom_ttl_hours(self, tmp_path):
        """Should accept custom TTL hours."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=12)

        assert cache.ttl_hours == 12


class TestCacheGet:
    """Tests for cache get method."""

    def test_returns_none_when_symbol_not_cached(self, tmp_path):
        """Should return None for uncached symbol."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        result = cache.get("AAPL")

        assert result is None

    def test_returns_cached_value_when_valid(self, tmp_path):
        """Should return cached value when not expired."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        # Set cache directly
        cache.cache["AAPL"] = {"market_cap": 3000000000000, "timestamp": datetime.now().isoformat()}

        result = cache.get("AAPL")

        assert result == 3000000000000

    def test_returns_none_when_expired(self, tmp_path):
        """Should return None when cache entry is expired."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        # Set expired cache (25 hours ago)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache.cache["AAPL"] = {"market_cap": 3000000000000, "timestamp": old_time}

        result = cache.get("AAPL")

        assert result is None
        assert "AAPL" not in cache.cache  # Entry should be deleted

    def test_removes_expired_entry_from_cache(self, tmp_path):
        """Should remove expired entry and save cache."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache.cache["AAPL"] = {"market_cap": 3000000000000, "timestamp": old_time}
        cache._save_cache()

        cache.get("AAPL")

        # Verify file was updated without the expired entry
        saved_data = json.loads(cache_file.read_text())
        assert "AAPL" not in saved_data


class TestCacheSet:
    """Tests for cache set method."""

    def test_sets_market_cap_value(self, tmp_path):
        """Should set market cap value in cache."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        cache.set("AAPL", 3000000000000)

        assert cache.cache["AAPL"]["market_cap"] == 3000000000000

    def test_adds_timestamp(self, tmp_path):
        """Should add timestamp to cache entry."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        cache.set("AAPL", 3000000000000)

        assert "timestamp" in cache.cache["AAPL"]
        # Verify timestamp is recent (within 5 seconds)
        entry_time = datetime.fromisoformat(cache.cache["AAPL"]["timestamp"])
        assert (datetime.now() - entry_time).total_seconds() < 5

    def test_persists_to_file(self, tmp_path):
        """Should save cache to file after setting value."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        cache.set("AAPL", 3000000000000)

        saved_data = json.loads(cache_file.read_text())
        assert saved_data["AAPL"]["market_cap"] == 3000000000000

    def test_overwrites_existing_entry(self, tmp_path):
        """Should overwrite existing cache entry."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        cache.set("AAPL", 2000000000000)
        cache.set("AAPL", 3000000000000)

        assert cache.cache["AAPL"]["market_cap"] == 3000000000000

    def test_handles_zero_market_cap(self, tmp_path):
        """Should handle zero market cap value."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        cache.set("PENNY", 0)

        assert cache.cache["PENNY"]["market_cap"] == 0


class TestClearExpired:
    """Tests for clear_expired method."""

    def test_removes_all_expired_entries(self, tmp_path):
        """Should remove all expired entries."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        recent_time = datetime.now().isoformat()

        cache.cache = {
            "AAPL": {"market_cap": 3000000000000, "timestamp": old_time},
            "GOOGL": {"market_cap": 2000000000000, "timestamp": old_time},
            "MSFT": {"market_cap": 2500000000000, "timestamp": recent_time},
        }

        cache.clear_expired()

        assert "AAPL" not in cache.cache
        assert "GOOGL" not in cache.cache
        assert "MSFT" in cache.cache

    def test_saves_cache_after_clearing(self, tmp_path):
        """Should save cache to file after clearing expired entries."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        cache.cache = {"AAPL": {"market_cap": 3000000000000, "timestamp": old_time}}

        cache.clear_expired()

        saved_data = json.loads(cache_file.read_text())
        assert "AAPL" not in saved_data

    def test_does_nothing_when_no_expired_entries(self, tmp_path):
        """Should do nothing when all entries are valid."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        recent_time = datetime.now().isoformat()
        cache.cache = {"AAPL": {"market_cap": 3000000000000, "timestamp": recent_time}}
        cache._save_cache()

        cache.clear_expired()

        assert "AAPL" in cache.cache


class TestGetStats:
    """Tests for get_stats method."""

    def test_returns_empty_stats_when_cache_empty(self, tmp_path):
        """Should return zero stats for empty cache."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        stats = cache.get_stats()

        assert stats["total_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["oldest_entry_hours"] is None
        assert stats["newest_entry_hours"] is None

    def test_calculates_entry_counts(self, tmp_path):
        """Should calculate total, expired, and valid entry counts."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        recent_time = datetime.now().isoformat()

        cache.cache = {
            "AAPL": {"market_cap": 3000000000000, "timestamp": old_time},
            "MSFT": {"market_cap": 2500000000000, "timestamp": recent_time},
        }

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["valid_entries"] == 1

    def test_calculates_oldest_and_newest(self, tmp_path):
        """Should calculate oldest and newest entry ages."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=48)

        time_10h = (datetime.now() - timedelta(hours=10)).isoformat()
        time_2h = (datetime.now() - timedelta(hours=2)).isoformat()

        cache.cache = {
            "AAPL": {"market_cap": 3000000000000, "timestamp": time_10h},
            "MSFT": {"market_cap": 2500000000000, "timestamp": time_2h},
        }

        stats = cache.get_stats()

        assert stats["oldest_entry_hours"] == pytest.approx(10.0, abs=0.1)
        assert stats["newest_entry_hours"] == pytest.approx(2.0, abs=0.1)

    def test_includes_cache_file_and_ttl(self, tmp_path):
        """Should include cache file path and TTL in stats (when cache has data)."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file), ttl_hours=12)

        # Add entry to get full stats
        cache.set("AAPL", 3000000000000)
        stats = cache.get_stats()

        assert stats["cache_file"] == str(cache_file)
        assert stats["ttl_hours"] == 12


class TestSaveCache:
    """Tests for _save_cache error handling."""

    def test_handles_write_error_gracefully(self, tmp_path):
        """Should handle write errors without raising."""
        cache_file = tmp_path / "nonexistent_dir" / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        # This should not raise, just log error
        cache.set("AAPL", 3000000000000)

        # Data should still be in memory
        assert cache.cache["AAPL"]["market_cap"] == 3000000000000


class TestCacheIntegration:
    """Integration tests for cache workflow."""

    def test_full_cache_workflow(self, tmp_path):
        """Should handle complete cache workflow."""
        cache_file = tmp_path / "cache.json"

        # Create cache and add entries
        cache1 = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)
        cache1.set("AAPL", 3000000000000)
        cache1.set("GOOGL", 2000000000000)

        # Verify retrieval
        assert cache1.get("AAPL") == 3000000000000
        assert cache1.get("GOOGL") == 2000000000000

        # Create new cache instance (simulating restart)
        cache2 = MarketCapCache(cache_file=str(cache_file), ttl_hours=24)

        # Data should persist
        assert cache2.get("AAPL") == 3000000000000
        assert cache2.get("GOOGL") == 2000000000000

    def test_multiple_symbols(self, tmp_path):
        """Should handle multiple symbols efficiently."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA"]
        for i, symbol in enumerate(symbols):
            cache.set(symbol, (i + 1) * 1000000000000)

        for i, symbol in enumerate(symbols):
            assert cache.get(symbol) == (i + 1) * 1000000000000

    def test_special_symbol_names(self, tmp_path):
        """Should handle symbols with special characters."""
        cache_file = tmp_path / "cache.json"
        cache = MarketCapCache(cache_file=str(cache_file))

        # Symbols with dots (like BRK.B)
        cache.set("BRK.B", 800000000000)
        assert cache.get("BRK.B") == 800000000000

        # Symbols with hyphens
        cache.set("SPY-USD", 500000000000)
        assert cache.get("SPY-USD") == 500000000000
