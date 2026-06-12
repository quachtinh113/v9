"""
telegram_sender.py – Low-level Telegram HTTP sender.

Responsibilities:
  - Send text messages (HTML parse mode).
  - Send documents / file attachments (for reports).
  - Retry on transient network errors with exponential back-off.
  - Completely decoupled from business logic – only knows about the Bot API.

Dependencies:
  - TELEGRAM_BOT_TOKEN must be set in .env (loaded by the caller or dotenv).
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_DEFAULT_TIMEOUT = 15  # seconds
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 1.5  # seconds


def _get_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set in environment.")
    return token


def _api_url(method: str, token: Optional[str] = None) -> str:
    return _TELEGRAM_API.format(token=token or _get_token(), method=method)


class TelegramSender:
    """Handles all outbound communication to the Telegram Bot API."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        self._token: str = token or _get_token()
        self._chat_id: str = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not self._chat_id:
            raise EnvironmentError("TELEGRAM_CHAT_ID is not set in environment.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send_message(self, text: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> bool:
        """Send a text message. Returns True on success."""
        payload = {
            "chat_id": chat_id or self._chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        return self._post_with_retry("sendMessage", json=payload)

    def send_document(
        self,
        file_path: str | Path,
        caption: str = "",
        chat_id: Optional[str] = None,
    ) -> bool:
        """Send a file as a Telegram document attachment."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error("[TelegramSender] Document not found: %s", file_path)
            return False

        try:
            with file_path.open("rb") as fh:
                files = {"document": (file_path.name, fh)}
                data = {
                    "chat_id": chat_id or self._chat_id,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                return self._post_with_retry("sendDocument", files=files, data=data)
        except OSError as exc:
            logger.error("[TelegramSender] Could not open document %s: %s", file_path, exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_with_retry(self, method: str, **kwargs) -> bool:
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = requests.post(url, timeout=_DEFAULT_TIMEOUT, **kwargs)
                if resp.status_code == 200:
                    return True
                logger.warning(
                    "[TelegramSender] API error %s on %s (attempt %d): %s",
                    resp.status_code,
                    method,
                    attempt,
                    resp.text[:200],
                )
            except requests.RequestException as exc:
                logger.warning(
                    "[TelegramSender] Network error on %s (attempt %d): %s",
                    method,
                    attempt,
                    exc,
                )

            if attempt < _MAX_RETRIES:
                sleep_s = _RETRY_BACKOFF_BASE ** attempt
                logger.debug("[TelegramSender] Retrying in %.1fs …", sleep_s)
                time.sleep(sleep_s)

        logger.error("[TelegramSender] All %d attempts failed for method '%s'.", _MAX_RETRIES, method)
        return False
