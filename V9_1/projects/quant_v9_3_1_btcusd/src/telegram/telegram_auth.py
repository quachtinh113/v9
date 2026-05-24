"""
telegram_auth.py – Authorization layer for the Telegram Command Gateway.

Security contract:
  - Only messages from the *exact* TELEGRAM_CHAT_ID stored in .env are accepted.
  - Commands may optionally carry a TELEGRAM_COMMAND_SECRET prefix for an
    extra HMAC-free shared-secret check (defence-in-depth).
  - All auth decisions are logged via standard Python logging so they appear
    in the unified audit trail.
  - Auth state is stateless / re-evaluated on every incoming update.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_authorized_chat_id() -> Optional[str]:
    """Return the authorized chat_id string from the environment."""
    return os.getenv("TELEGRAM_CHAT_ID", "").strip() or None


def get_command_secret() -> Optional[str]:
    """Return the optional command secret from the environment.

    If TELEGRAM_COMMAND_SECRET is set, every command body must start with
    ``!<secret> `` (e.g. ``!mysecret /status``).  If the env var is empty /
    absent the secret check is skipped.
    """
    return os.getenv("TELEGRAM_COMMAND_SECRET", "").strip() or None


class TelegramAuthError(Exception):
    """Raised when an incoming update fails authorization."""


class TelegramAuth:
    """Validates incoming Telegram updates before they are dispatched."""

    def __init__(self) -> None:
        self._authorized_chat_id: Optional[str] = get_authorized_chat_id()
        self._command_secret: Optional[str] = get_command_secret()

        if not self._authorized_chat_id:
            logger.warning(
                "[TelegramAuth] TELEGRAM_CHAT_ID is not set – ALL commands will be rejected."
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_authorized(self, chat_id: str | int) -> bool:
        """Return True if chat_id matches the authorized chat."""
        if not self._authorized_chat_id:
            logger.warning("[TelegramAuth] No authorized chat_id configured. Rejecting.")
            return False

        result = str(chat_id).strip() == self._authorized_chat_id
        if not result:
            logger.warning(
                "[TelegramAuth] Unauthorized access attempt from chat_id=%s", chat_id
            )
        return result

    def validate_update(self, chat_id: str | int, text: str) -> str:
        """Full authorization gate.

        Args:
            chat_id: The Telegram chat / user ID of the sender.
            text:    The raw message text received.

        Returns:
            The command text with the secret prefix stripped (if applicable).

        Raises:
            TelegramAuthError: When authorization fails for any reason.
        """
        if not self.is_authorized(chat_id):
            raise TelegramAuthError(
                f"Unauthorized chat_id '{chat_id}'. Command rejected."
            )

        # Strip optional command secret prefix
        cleaned_text = text.strip()
        if self._command_secret:
            expected_prefix = f"!{self._command_secret} "
            if not cleaned_text.startswith(expected_prefix):
                logger.warning(
                    "[TelegramAuth] Message from chat_id=%s missing command secret.", chat_id
                )
                raise TelegramAuthError(
                    "Command secret missing or incorrect. Prefix your command with "
                    f"'!<secret> <command>'."
                )
            cleaned_text = cleaned_text[len(expected_prefix):].strip()

        return cleaned_text
