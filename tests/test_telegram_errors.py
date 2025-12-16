"""
Tests for Telegram client error handling and retry logic.

Uses `responses` library for HTTP mocking - deterministic and fast.
"""
import pytest
import responses
from unittest.mock import patch

from src.telegram_client import TelegramClient
from src.exceptions import TelegramError


@pytest.fixture
def telegram_client():
    """Create a test Telegram client."""
    # Reset session for clean state
    TelegramClient._session = None
    return TelegramClient(token="test_bot_token", chat_id="123456789")


class TestTelegramSendSuccess:
    """Tests for successful message sending."""

    @responses.activate
    def test_send_success(self, telegram_client):
        """Test successful message send."""
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": True, "result": {"message_id": 123}},
            status=200,
        )

        result = telegram_client.send("Hello, World!")

        assert result is True
        assert telegram_client._consecutive_failures == 0

    @responses.activate
    def test_send_resets_failure_counter(self, telegram_client):
        """Test that successful send resets consecutive failure counter."""
        telegram_client._consecutive_failures = 3

        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": True, "result": {}},
            status=200,
        )

        telegram_client.send("Test message")

        assert telegram_client._consecutive_failures == 0


class TestTelegramSendFailure:
    """Tests for message send failures."""

    @responses.activate
    def test_send_non_critical_returns_false(self, telegram_client):
        """Test that non-critical send failure returns False."""
        import requests

        # All retries fail
        for _ in range(3):
            responses.add(
                responses.POST,
                "https://api.telegram.org/bottest_bot_token/sendMessage",
                body=requests.exceptions.ConnectionError("Network error"),
            )

        with patch("src.telegram_client.time.sleep"):
            result = telegram_client.send("Test", critical=False)

        assert result is False
        assert telegram_client._consecutive_failures == 1

    @responses.activate
    def test_send_critical_raises_telegram_error(self, telegram_client):
        """Test that critical send failure raises TelegramError."""
        import requests

        for _ in range(3):
            responses.add(
                responses.POST,
                "https://api.telegram.org/bottest_bot_token/sendMessage",
                body=requests.exceptions.ConnectionError("Network error"),
            )

        with patch("src.telegram_client.time.sleep"):
            with pytest.raises(TelegramError) as exc_info:
                telegram_client.send("Critical message", critical=True)

        assert "Failed to send critical message" in str(exc_info.value)

    @responses.activate
    def test_consecutive_failures_trigger_critical_error(self, telegram_client):
        """Test that max consecutive failures raises critical error."""
        import requests

        # Set failures just below threshold
        telegram_client._consecutive_failures = 4

        for _ in range(3):
            responses.add(
                responses.POST,
                "https://api.telegram.org/bottest_bot_token/sendMessage",
                body=requests.exceptions.ConnectionError("Network error"),
            )

        with patch("src.telegram_client.time.sleep"):
            with pytest.raises(TelegramError) as exc_info:
                telegram_client.send("Test", critical=False)

        assert "consecutive failures" in str(exc_info.value)
        assert telegram_client._consecutive_failures == 5


class TestTelegramRateLimiting:
    """Tests for rate limit handling."""

    @responses.activate
    def test_rate_limit_429_triggers_retry(self, telegram_client):
        """Test that 429 rate limit triggers retry with backoff."""
        # First call returns 429, second succeeds
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            status=429,
            headers={"Retry-After": "0"},
        )
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": True, "result": {}},
            status=200,
        )

        with patch("src.telegram_client.time.sleep"):
            result = telegram_client.send("Test message")

        assert result is True
        assert len(responses.calls) == 2


class TestTelegramTimeout:
    """Tests for timeout handling."""

    @responses.activate
    def test_timeout_triggers_retry(self, telegram_client):
        """Test that timeout triggers retry with exponential backoff."""
        import requests

        # First call times out, second succeeds
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            body=requests.exceptions.Timeout("Read timed out"),
        )
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": True, "result": {}},
            status=200,
        )

        with patch("src.telegram_client.time.sleep"):
            result = telegram_client.send("Test message")

        assert result is True
        assert len(responses.calls) == 2


class TestTelegramAPIErrors:
    """Tests for Telegram API error responses."""

    @responses.activate
    def test_api_not_ok_raises_error(self, telegram_client):
        """Test that API returning ok=False raises error."""
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": False, "description": "Bad Request: chat not found"},
            status=200,  # HTTP 200 but API error
        )

        with pytest.raises(TelegramError) as exc_info:
            telegram_client.send("Test", critical=True)

        assert "Telegram API error" in str(exc_info.value)


class TestTelegramHealthCheck:
    """Tests for health check functionality."""

    def test_is_healthy_when_no_failures(self, telegram_client):
        """Test health check returns True with no failures."""
        telegram_client._consecutive_failures = 0
        assert telegram_client.is_healthy() is True

    def test_is_healthy_below_threshold(self, telegram_client):
        """Test health check returns True below failure threshold."""
        telegram_client._consecutive_failures = 4
        assert telegram_client.is_healthy() is True

    def test_is_not_healthy_at_threshold(self, telegram_client):
        """Test health check returns False at failure threshold."""
        telegram_client._consecutive_failures = 5
        assert telegram_client.is_healthy() is False
