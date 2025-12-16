import time
import requests
from .logger import logger
from .exceptions import TelegramError
from .rate_limiter import rate_limit


class TelegramClient:
    """
    Telegram client with retry and proper error handling.
    
    Critical errors are NOT swallowed - they propagate up.
    Transient errors are retried with exponential backoff.
    """
    
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        logger.info("telegram.init", chat_id=chat_id)

    def send(self, text: str, parse_mode: str = "Markdown", critical: bool = False) -> bool:
        """
        Send Telegram message with retry logic.
        
        Args:
            text: Message text
            parse_mode: Markdown or HTML
            critical: If True, raise exception on failure. If False, log and return False.
            
        Returns:
            True if sent successfully, False if failed (only when critical=False)
            
        Raises:
            TelegramError: If send fails and critical=True, or after max consecutive failures
        """
        # Rate limit Telegram API calls
        rate_limit("telegram")
        
        url = f"{self.base}/sendMessage"
        max_attempts = 3
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug("telegram.sending", preview=text[:50], attempt=attempt)
                
                r = requests.post(
                    url,
                    json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                    timeout=10
                )
                
                # Handle rate limiting (429)
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 5))
                    logger.warning("telegram.rate_limited", retry_after=retry_after)
                    if attempt < max_attempts:
                        time.sleep(retry_after)
                        continue
                
                r.raise_for_status()
                
                result = r.json()
                if not result.get("ok"):
                    raise TelegramError(f"Telegram API error: {result}")
                
                # Success - reset failure counter
                self._consecutive_failures = 0
                logger.info("telegram.sent", chars=len(text))
                return True
                
            except requests.Timeout as e:
                last_error = e
                logger.warning("telegram.timeout", attempt=attempt)
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            except requests.RequestException as e:
                last_error = e
                logger.error("telegram.network_error", attempt=attempt, error=str(e)[:50])
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
                    continue
                    
            except Exception as e:
                last_error = e
                logger.error("telegram.error", attempt=attempt, error=str(e)[:50])
                break  # Don't retry unknown errors
        
        # All attempts failed
        self._consecutive_failures += 1
        
        # Check if we've hit max consecutive failures
        if self._consecutive_failures >= self._max_consecutive_failures:
            logger.error(
                "telegram.critical_failure",
                consecutive_failures=self._consecutive_failures,
                error=str(last_error)
            )
            raise TelegramError(
                f"Telegram critically failed: {self._consecutive_failures} consecutive failures. "
                f"Last error: {last_error}"
            )
        
        # If critical message, always raise
        if critical:
            raise TelegramError(f"Failed to send critical message: {last_error}")
        
        # Non-critical: log and return False
        logger.warning(
            "telegram.send_failed",
            consecutive_failures=self._consecutive_failures,
            error=str(last_error)[:100]
        )
        return False
    
    def send_critical(self, text: str, parse_mode: str = "Markdown"):
        """
        Send a critical message that MUST be delivered.
        Raises TelegramError on failure.
        """
        return self.send(text, parse_mode=parse_mode, critical=True)
    
    def is_healthy(self) -> bool:
        """Check if Telegram client is healthy (no consecutive failures)."""
        return self._consecutive_failures < self._max_consecutive_failures
