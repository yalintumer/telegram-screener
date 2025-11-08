import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from .logger import logger
from .exceptions import TelegramError


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id
        logger.info("telegram.init", chat_id=chat_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def send(self, text: str, parse_mode: str = "Markdown"):
        """
        Send Telegram message with retry logic
        
        Args:
            text: Message text
            parse_mode: Markdown or HTML
            
        Raises:
            TelegramError: If send fails after retries
        """
        url = f"{self.base}/sendMessage"
        try:
            logger.debug("telegram.sending", preview=text[:50])
            r = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                timeout=10
            )
            r.raise_for_status()
            
            result = r.json()
            if not result.get("ok"):
                raise TelegramError(f"Telegram API error: {result}")
            
            logger.info("telegram.sent", chars=len(text))
            
        except requests.RequestException as e:
            logger.error("telegram.network_error", error=str(e))
            raise TelegramError(f"Failed to send message: {e}")
        except Exception as e:
            logger.error("telegram.error", error=str(e))
            raise TelegramError(f"Telegram error: {e}")
