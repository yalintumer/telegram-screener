"""
Retry utilities with exponential backoff.
Simple, no external dependencies.
"""
import random
import time
from collections.abc import Callable
from functools import wraps

from .constants import DEFAULT_RETRY_DELAY, MAX_RETRY_ATTEMPTS, MAX_RETRY_DELAY
from .logger import logger


class RetryError(Exception):
    """Raised when all retry attempts fail."""
    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry_with_backoff(
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_DELAY,
    max_delay: float = MAX_RETRY_DELAY,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception, float], None] | None = None
):
    """
    Decorator for retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to prevent thundering herd (default: True)
        retryable_exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback(attempt, exception, delay) called before retry
        
    Usage:
        @retry_with_backoff(max_attempts=3, retryable_exceptions=(requests.RequestException,))
        def call_api():
            return requests.get(url)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            "retry.exhausted",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e)[:100]
                        )
                        raise RetryError(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            last_exception=e
                        )

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter (±25%)
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.5)

                    logger.warning(
                        "retry.attempting",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=round(delay, 2),
                        error=str(e)[:50]
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    time.sleep(delay)

            # Should never reach here, but just in case
            raise RetryError(f"{func.__name__} failed", last_exception=last_exception)

        return wrapper
    return decorator


def is_retryable_http_status(status_code: int) -> bool:
    """
    Check if HTTP status code is retryable.
    
    Retryable: 429 (rate limit), 500, 502, 503, 504 (server errors)
    Not retryable: 400, 401, 403, 404 (client errors)
    """
    return status_code in (429, 500, 502, 503, 504)


class RetryableRequestException(Exception):
    """Exception for retryable HTTP errors."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code
