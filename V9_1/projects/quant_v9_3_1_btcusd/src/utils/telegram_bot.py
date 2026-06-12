import requests
import logging

class TelegramBot:
    def __init__(self, token: str, chat_id: str, enabled: bool = True):
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, text: str):
        if not self.enabled: return
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Telegram error: {e}")

    def send_photo(self, photo_path: str, caption: str = ""):
        if not self.enabled: return
        try:
            url = f"{self.base_url}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': self.chat_id, 'caption': caption, 'parse_mode': "HTML"}
                requests.post(url, files=files, data=data, timeout=20)
        except Exception as e:
            logging.error(f"Telegram Photo error: {e}")
