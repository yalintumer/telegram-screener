"""Rate limiting and throttling utilities"""

import time
import threading
from collections import deque
from typing import Callable, Any


class RateLimiter:
    """
    Token bucket rate limiter
    
    Usage:
        limiter = RateLimiter(max_calls=5, time_window=60)
        
        with limiter:
            # Make API call
            data = fetch_api()
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = threading.Lock()
    
    def __enter__(self):
        """Wait until rate limit allows"""
        with self.lock:
            now = time.time()
            
            # Remove old calls outside time window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            # If at limit, wait
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.time_window - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Re-clean after sleep
                    now = time.time()
                    while self.calls and self.calls[0] < now - self.time_window:
                        self.calls.popleft()
            
            # Record this call
            self.calls.append(now)
        
        return self
    
    def __exit__(self, *args):
        pass
    
    def wait_if_needed(self):
        """Explicit wait method (alternative to context manager)"""
        self.__enter__()


class AdaptiveRateLimiter:
    """
    Rate limiter that adapts based on errors
    
    Starts conservative, speeds up if no errors, slows down on errors
    """
    
    def __init__(self, 
                 initial_delay: float = 1.0,
                 min_delay: float = 0.5,
                 max_delay: float = 5.0,
                 backoff_factor: float = 1.5,
                 recovery_factor: float = 0.9):
        """
        Args:
            initial_delay: Starting delay between calls (seconds)
            min_delay: Minimum delay (fastest)
            max_delay: Maximum delay (slowest)
            backoff_factor: Multiplier when error occurs (>1.0)
            recovery_factor: Multiplier when successful (<1.0)
        """
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.last_call_time = 0
        self.lock = threading.Lock()
        self.success_count = 0
        self.error_count = 0
    
    def wait(self):
        """Wait appropriate delay before next call"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            
            if elapsed < self.current_delay:
                sleep_time = self.current_delay - elapsed
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()
    
    def report_success(self):
        """Report successful API call - speed up slightly"""
        with self.lock:
            self.success_count += 1
            
            # After 3 consecutive successes, reduce delay
            if self.success_count >= 3:
                self.current_delay *= self.recovery_factor
                self.current_delay = max(self.min_delay, self.current_delay)
                self.success_count = 0
                self.error_count = 0
    
    def report_error(self):
        """Report API error - slow down"""
        with self.lock:
            self.error_count += 1
            self.success_count = 0
            
            # Immediate backoff on error
            self.current_delay *= self.backoff_factor
            self.current_delay = min(self.max_delay, self.current_delay)
    
    def get_stats(self) -> dict:
        """Get current limiter stats"""
        with self.lock:
            return {
                "current_delay": round(self.current_delay, 2),
                "min_delay": self.min_delay,
                "max_delay": self.max_delay,
                "success_streak": self.success_count,
                "error_count": self.error_count
            }


def throttle(calls: int, period: float):
    """
    Decorator to throttle function calls
    
    Args:
        calls: Max calls allowed
        period: Time period in seconds
        
    Example:
        @throttle(calls=5, period=60)
        def fetch_data(symbol):
            return api.get(symbol)
    """
    limiter = RateLimiter(max_calls=calls, time_window=period)
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            with limiter:
                return func(*args, **kwargs)
        return wrapper
    return decorator
