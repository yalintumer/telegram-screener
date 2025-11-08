import requests

class TelegramClient:
    def __init__(self, token, chat_id):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text):
        r = requests.post(f"{self.base}/sendMessage", json={"chat_id": self.chat_id, "text": text})
        r.raise_for_status()