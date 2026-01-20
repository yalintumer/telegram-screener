"""
Tests for retry utilities with exponential backoff
"""

import time
from unittest.mock import patch

import pytest

from src.retry import RetryableRequestException, RetryError, is_retryable_http_status, retry_with_backoff


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator"""

    def test_succeeds_on_first_attempt(self):
        """Test that successful call returns immediately"""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_exception(self):
        """Test that function retries on exception"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01, jitter=False)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_raises_retry_error_after_max_attempts(self):
        """Test that RetryError is raised after all attempts fail"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            always_fails()

        assert call_count == 3
        assert "after 3 attempts" in str(exc_info.value)
        assert exc_info.value.last_exception is not None

    def test_only_retries_specified_exceptions(self):
        """Test that only specified exceptions are retried"""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,))
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        # TypeError should propagate immediately, not be retried
        with pytest.raises(TypeError):
            raises_type_error()

        assert call_count == 1

    def test_exponential_backoff_increases_delay(self):
        """Test that delay increases exponentially"""
        delays = []

        @retry_with_backoff(max_attempts=4, base_delay=1.0, max_delay=100.0, jitter=False)
        def capture_delays():
            # Capture time between calls
            delays.append(time.time())
            raise ValueError("Fail")

        with patch("src.retry.time.sleep") as mock_sleep:
            with pytest.raises(RetryError):
                capture_delays()

            # Check delays: 1, 2, 4 (exponential)
            assert mock_sleep.call_count == 3
            calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert calls[0] == pytest.approx(1.0, rel=0.1)
            assert calls[1] == pytest.approx(2.0, rel=0.1)
            assert calls[2] == pytest.approx(4.0, rel=0.1)

    def test_max_delay_caps_backoff(self):
        """Test that delay is capped at max_delay"""

        @retry_with_backoff(max_attempts=5, base_delay=10.0, max_delay=15.0, jitter=False)
        def always_fails():
            raise ValueError("Fail")

        with patch("src.retry.time.sleep") as mock_sleep:
            with pytest.raises(RetryError):
                always_fails()

            # All delays should be <= max_delay
            for call in mock_sleep.call_args_list:
                assert call[0][0] <= 15.0

    def test_jitter_varies_delay(self):
        """Test that jitter adds variation to delay"""

        @retry_with_backoff(max_attempts=10, base_delay=1.0, jitter=True)
        def capture_with_jitter():
            raise ValueError("Fail")

        with patch("src.retry.time.sleep") as mock_sleep:
            with pytest.raises(RetryError):
                capture_with_jitter()

        calls = [call[0][0] for call in mock_sleep.call_args_list]

        # With jitter, delays should vary (not all identical)
        first_attempt_delays = list(calls)
        # Check there's some variation (jitter is ±25%)
        assert len({round(d, 2) for d in first_attempt_delays}) > 1

    def test_on_retry_callback_called(self):
        """Test that on_retry callback is called before each retry"""
        callback_calls = []

        def on_retry_callback(attempt, exception, delay):
            callback_calls.append({"attempt": attempt, "error": str(exception), "delay": delay})

        @retry_with_backoff(max_attempts=3, base_delay=0.01, jitter=False, on_retry=on_retry_callback)
        def flaky():
            raise ValueError("Test error")

        with pytest.raises(RetryError):
            flaky()

        # Should have 2 callbacks (before retry 2 and 3)
        assert len(callback_calls) == 2
        assert callback_calls[0]["attempt"] == 1
        assert callback_calls[1]["attempt"] == 2
        assert "Test error" in callback_calls[0]["error"]

    def test_preserves_function_name(self):
        """Test that decorator preserves function name"""

        @retry_with_backoff()
        def my_function():
            return "result"

        assert my_function.__name__ == "my_function"


class TestIsRetryableHttpStatus:
    """Test is_retryable_http_status function"""

    @pytest.mark.parametrize(
        "status,expected",
        [
            (429, True),  # Rate limited
            (500, True),  # Internal server error
            (502, True),  # Bad gateway
            (503, True),  # Service unavailable
            (504, True),  # Gateway timeout
            (200, False),  # OK
            (201, False),  # Created
            (400, False),  # Bad request
            (401, False),  # Unauthorized
            (403, False),  # Forbidden
            (404, False),  # Not found
            (422, False),  # Unprocessable entity
        ],
    )
    def test_http_status_codes(self, status, expected):
        """Test various HTTP status codes"""
        assert is_retryable_http_status(status) == expected


class TestRetryableRequestException:
    """Test RetryableRequestException"""

    def test_stores_status_code(self):
        """Test that exception stores status code"""
        exc = RetryableRequestException("Server error", 503)
        assert exc.status_code == 503
        assert "Server error" in str(exc)


class TestRetryWithDifferentExceptions:
    """Test retry behavior with different exception types"""

    def test_retries_multiple_exception_types(self):
        """Test that multiple exception types can be retried"""
        call_count = 0

        @retry_with_backoff(max_attempts=4, base_delay=0.01, retryable_exceptions=(ValueError, TypeError, RuntimeError))
        def mixed_exceptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First")
            if call_count == 2:
                raise TypeError("Second")
            if call_count == 3:
                raise RuntimeError("Third")
            return "success"

        result = mixed_exceptions()
        assert result == "success"
        assert call_count == 4
