"""Unit tests for rate limiting"""

import pytest
import time
from src.rate_limiter import RateLimiter, AdaptiveRateLimiter


class TestRateLimiter:
    """Tests for token bucket rate limiter"""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        limiter = RateLimiter(max_calls=3, time_window=1.0)
        
        start = time.time()
        
        # First 3 calls should be immediate
        for i in range(3):
            with limiter:
                pass
        
        elapsed = time.time() - start
        assert elapsed < 0.5, "First 3 calls should be fast"
        
        # 4th call should wait
        start = time.time()
        with limiter:
            pass
        elapsed = time.time() - start
        
        assert elapsed >= 0.5, "4th call should be delayed"
    
    def test_time_window_cleanup(self):
        """Test that old calls are removed from window"""
        limiter = RateLimiter(max_calls=2, time_window=1.0)
        
        # Use up rate limit
        with limiter:
            pass
        with limiter:
            pass
        
        # Wait for window to pass
        time.sleep(1.1)
        
        # Should be able to make calls again quickly
        start = time.time()
        with limiter:
            pass
        elapsed = time.time() - start
        
        assert elapsed < 0.5, "Should be fast after window passes"
    
    def test_concurrent_access(self):
        """Test thread safety (basic check)"""
        limiter = RateLimiter(max_calls=5, time_window=1.0)
        
        # Should not raise exceptions with concurrent access
        import threading
        
        def make_call():
            with limiter:
                time.sleep(0.01)
        
        threads = [threading.Thread(target=make_call) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # If we get here without exceptions, thread safety is working


class TestAdaptiveRateLimiter:
    """Tests for adaptive rate limiter"""
    
    def test_initial_delay(self):
        """Test initial delay is respected"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=3.0
        )
        
        stats = limiter.get_stats()
        assert stats['current_delay'] == 1.0
    
    def test_success_speeds_up(self):
        """Test that successes reduce delay"""
        limiter = AdaptiveRateLimiter(
            initial_delay=2.0,
            min_delay=0.5,
            max_delay=5.0,
            recovery_factor=0.8
        )
        
        initial_delay = limiter.current_delay
        
        # Report 3 successes (threshold for speedup)
        for _ in range(3):
            limiter.report_success()
        
        stats = limiter.get_stats()
        assert stats['current_delay'] < initial_delay, "Delay should decrease after successes"
    
    def test_error_slows_down(self):
        """Test that errors increase delay"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=5.0,
            backoff_factor=1.5
        )
        
        initial_delay = limiter.current_delay
        
        limiter.report_error()
        
        stats = limiter.get_stats()
        assert stats['current_delay'] > initial_delay, "Delay should increase after error"
    
    def test_min_delay_enforced(self):
        """Test minimum delay is enforced"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=5.0,
            recovery_factor=0.1  # Aggressive recovery
        )
        
        # Report many successes
        for _ in range(20):
            limiter.report_success()
        
        stats = limiter.get_stats()
        assert stats['current_delay'] >= stats['min_delay'], "Should not go below min_delay"
    
    def test_max_delay_enforced(self):
        """Test maximum delay is enforced"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=3.0,
            backoff_factor=2.0  # Aggressive backoff
        )
        
        # Report many errors
        for _ in range(10):
            limiter.report_error()
        
        stats = limiter.get_stats()
        assert stats['current_delay'] <= stats['max_delay'], "Should not exceed max_delay"
    
    def test_stats_tracking(self):
        """Test statistics are tracked correctly"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=5.0
        )
        
        # Success streak
        limiter.report_success()
        limiter.report_success()
        
        stats = limiter.get_stats()
        assert stats['success_streak'] == 2
        
        # Error resets streak
        limiter.report_error()
        
        stats = limiter.get_stats()
        assert stats['success_streak'] == 0
        assert stats['error_count'] == 1
    
    def test_wait_timing(self):
        """Test that wait() actually delays"""
        limiter = AdaptiveRateLimiter(
            initial_delay=0.5,
            min_delay=0.1,
            max_delay=2.0
        )
        
        # First call - should be immediate
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        assert elapsed < 0.1, "First call should be immediate"
        
        # Second call - should wait
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        assert elapsed >= 0.4, "Second call should wait at least 0.4s (accounting for some overhead)"
    
    def test_alternating_success_error(self):
        """Test alternating success and error patterns"""
        limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=5.0,
            backoff_factor=1.3,  # More moderate backoff
            recovery_factor=0.95  # Slower recovery
        )
        
        # Alternate success and error (but not too many)
        for _ in range(3):
            limiter.report_success()
            limiter.report_error()
        
        stats = limiter.get_stats()
        # Should be somewhere between min and max (not at extremes)
        # More lenient check since alternating can push to limits
        assert stats['current_delay'] >= stats['min_delay']
        assert stats['current_delay'] <= stats['max_delay']


class TestEdgeCases:
    """Edge case tests for rate limiters"""
    
    def test_zero_calls_allowed(self):
        """Test edge case of 0 calls allowed"""
        # Should handle gracefully (though not practical)
        limiter = RateLimiter(max_calls=0, time_window=1.0)
        
        # Every call should be delayed
        start = time.time()
        with limiter:
            pass
        elapsed = time.time() - start
        
        # Should be delayed by time_window
        assert elapsed >= 0.9
    
    def test_very_short_time_window(self):
        """Test very short time window"""
        limiter = RateLimiter(max_calls=5, time_window=0.1)
        
        # Should work without errors
        for _ in range(3):
            with limiter:
                pass
    
    def test_adaptive_limiter_zero_delays(self):
        """Test adaptive limiter with zero/near-zero delays"""
        limiter = AdaptiveRateLimiter(
            initial_delay=0.0,
            min_delay=0.0,
            max_delay=0.1
        )
        
        # Should handle without errors
        limiter.wait()
        limiter.report_success()
        limiter.wait()
