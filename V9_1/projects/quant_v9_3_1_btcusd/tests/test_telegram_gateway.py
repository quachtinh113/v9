"""
tests/test_telegram_gateway.py

Unit tests for the Telegram Command Gateway.

Tests cover:
  - Unauthorized chat_id rejection
  - Command secret enforcement
  - /pause disabling new entries (no force-close)
  - /resume blocked by RiskGateway
  - /resume allowed when RiskGateway clears
  - /kill triggering emergency stop flag
  - /status reflecting runtime state
  - Audit logging for every command
  - /buy and /sell blocked
"""

from __future__ import annotations

import json
import os
import threading
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Environment setup (must happen before importing gateway modules)
# ---------------------------------------------------------------------------

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-123")
os.environ.setdefault("TELEGRAM_CHAT_ID", "111222333")
os.environ.setdefault("TELEGRAM_COMMAND_SECRET", "")  # disabled by default

from src.telegram.telegram_auth import TelegramAuth, TelegramAuthError
from src.telegram.telegram_command_gateway import (
    GatewayState,
    TelegramAuditLogger,
    TelegramCommandGateway,
)
from src.core.risk_engine import RiskGateway


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory tree."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "config").mkdir()
    return tmp_path


@pytest.fixture()
def state() -> GatewayState:
    return GatewayState()


@pytest.fixture()
def risk_gateway() -> RiskGateway:
    return RiskGateway({
        "daily_loss_limit_pct": 2.0,
        "weekly_soft_stop_pct": 4.0,
        "hard_drawdown_pct": 8.0,
        "loss_streak_pause": 3,
        "max_open_positions": 5,
        "max_daily_trades": 20,
    })


def make_gateway(
    tmp_project: Path,
    risk_gateway: RiskGateway,
    state: GatewayState,
    account_fn=None,
    positions_fn=None,
) -> TelegramCommandGateway:
    gw = TelegramCommandGateway(
        project_root=tmp_project,
        risk_gateway=risk_gateway,
        state=state,
        symbol="BTCUSD",
        account_fn=account_fn,
        positions_fn=positions_fn,
    )
    return gw


# ---------------------------------------------------------------------------
# Helper to simulate an update dispatch without live HTTP
# ---------------------------------------------------------------------------

def dispatch_command(
    gateway: TelegramCommandGateway,
    text: str,
    chat_id: str = "111222333",
) -> None:
    """Directly call _handle_update with a synthetic Telegram update dict."""
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": int(chat_id)},
            "text": text,
        },
    }
    gateway._handle_update(update)


# ===========================================================================
# 1. Authorization tests
# ===========================================================================

class TestTelegramAuth:

    def test_authorized_chat_id_passes(self):
        auth = TelegramAuth()
        assert auth.is_authorized("111222333") is True

    def test_unauthorized_chat_id_rejected(self):
        auth = TelegramAuth()
        assert auth.is_authorized("999888777") is False

    def test_validate_update_raises_for_wrong_chat(self):
        auth = TelegramAuth()
        with pytest.raises(TelegramAuthError):
            auth.validate_update("999888777", "/status")

    def test_validate_update_passes_for_authorized_chat(self):
        auth = TelegramAuth()
        result = auth.validate_update("111222333", "/status")
        assert result == "/status"

    def test_command_secret_enforced_when_set(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_COMMAND_SECRET", "mySecret")
        auth = TelegramAuth()
        # Without secret prefix
        with pytest.raises(TelegramAuthError):
            auth.validate_update("111222333", "/status")

    def test_command_secret_strips_prefix(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_COMMAND_SECRET", "mySecret")
        auth = TelegramAuth()
        result = auth.validate_update("111222333", "!mySecret /risk")
        assert result == "/risk"


# ===========================================================================
# 2. Unauthorized command via gateway (no response sent)
# ===========================================================================

class TestUnauthorizedGateway:

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_unauthorized_chat_does_not_reply(
        self, mock_send, tmp_project, risk_gateway, state
    ):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/status", chat_id="999888777")
        # Unauthorized senders must NOT receive any response
        mock_send.assert_not_called()

    def test_unauthorized_command_logged_to_audit(self, tmp_project, risk_gateway, state):
        with patch("src.telegram.telegram_sender.TelegramSender.send_message"):
            gw = make_gateway(tmp_project, risk_gateway, state)
            dispatch_command(gw, "/status", chat_id="999888777")

        audit_path = tmp_project / "logs" / "telegram_audit.ndjson"
        assert audit_path.exists()
        entries = [json.loads(l) for l in audit_path.read_text().splitlines() if l]
        assert any(e["authorized"] is False for e in entries)


# ===========================================================================
# 3. /pause command
# ===========================================================================

class TestPauseCommand:

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_pause_sets_is_paused_flag(self, mock_send, tmp_project, risk_gateway, state):
        assert state.is_paused is False
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/pause")
        assert state.is_paused is True

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_pause_does_not_set_emergency_stop(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/pause")
        assert state.emergency_stopped is False

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_pause_sends_confirmation(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/pause")
        mock_send.assert_called_once()
        assert "PAUSED" in mock_send.call_args[0][0]


# ===========================================================================
# 4. /resume command
# ===========================================================================

class TestResumeCommand:

    def _clean_account(self) -> Dict[str, Any]:
        return {
            "daily_dd_pct": 0.0,
            "weekly_dd_pct": 0.0,
            "loss_streak": 0,
            "open_positions": 0,
            "daily_trades_count": 0,
            "open_exposure_pct": 0.0,
        }

    def _blocked_account(self) -> Dict[str, Any]:
        return {
            "daily_dd_pct": 5.0,   # Above 2% soft limit → SOFT_BLOCK
            "weekly_dd_pct": 0.0,
            "loss_streak": 0,
            "open_positions": 0,
            "daily_trades_count": 0,
        }

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_resume_blocked_by_risk_gateway(self, mock_send, tmp_project, risk_gateway, state):
        state.pause()
        gw = make_gateway(tmp_project, risk_gateway, state, account_fn=self._blocked_account)
        dispatch_command(gw, "/resume")
        # State must remain paused
        assert state.is_paused is True
        # Message must mention blocked
        assert "BLOCKED" in mock_send.call_args[0][0] or "blocked" in mock_send.call_args[0][0].lower()

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_resume_allowed_by_risk_gateway(self, mock_send, tmp_project, risk_gateway, state):
        state.pause()
        gw = make_gateway(tmp_project, risk_gateway, state, account_fn=self._clean_account)
        dispatch_command(gw, "/resume")
        assert state.is_paused is False
        assert "RESUMED" in mock_send.call_args[0][0] or "resumed" in mock_send.call_args[0][0].lower()

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_resume_after_kill_still_blocked_by_emergency_stop(
        self, mock_send, tmp_project, risk_gateway, state
    ):
        state.kill()
        # Emergency stop is set; is_paused is also True.
        # /resume may clear is_paused if risk allows, but emergency_stopped remains True.
        gw = make_gateway(tmp_project, risk_gateway, state, account_fn=self._clean_account)
        dispatch_command(gw, "/resume")
        # Emergency stop flag must NOT be cleared by /resume
        assert state.emergency_stopped is True


# ===========================================================================
# 5. /kill command
# ===========================================================================

class TestKillCommand:

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_kill_sets_emergency_stop_flag(self, mock_send, tmp_project, risk_gateway, state):
        assert state.emergency_stopped is False
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/kill")
        assert state.emergency_stopped is True

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_kill_also_pauses(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/kill")
        assert state.is_paused is True

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_kill_sends_confirmation(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/kill")
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "EMERGENCY" in msg or "emergency" in msg.lower()


# ===========================================================================
# 6. /status command
# ===========================================================================

class TestStatusCommand:

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_status_reflects_running_state(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/status")
        msg = mock_send.call_args[0][0]
        assert "RUNNING" in msg

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_status_reflects_paused_state(self, mock_send, tmp_project, risk_gateway, state):
        state.pause()
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/status")
        msg = mock_send.call_args[0][0]
        assert "PAUSED" in msg

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_status_reflects_emergency_stop(self, mock_send, tmp_project, risk_gateway, state):
        state.kill()
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/status")
        msg = mock_send.call_args[0][0]
        assert "EMERGENCY" in msg


# ===========================================================================
# 7. Audit logging
# ===========================================================================

class TestAuditLogging:

    def _run_command(self, cmd: str, tmp_project: Path, risk_gateway: RiskGateway, state: GatewayState):
        with patch("src.telegram.telegram_sender.TelegramSender.send_message"):
            with patch("src.telegram.telegram_sender.TelegramSender.send_document", return_value=False):
                gw = make_gateway(tmp_project, risk_gateway, state)
                dispatch_command(gw, cmd)

    def _read_audit(self, tmp_project: Path) -> List[Dict[str, Any]]:
        p = tmp_project / "logs" / "telegram_audit.ndjson"
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

    def test_every_command_is_logged(self, tmp_project, risk_gateway, state):
        commands = ["/status", "/pause", "/resume", "/kill", "/audit", "/positions", "/risk"]
        for cmd in commands:
            s = GatewayState()  # fresh state for each
            self._run_command(cmd, tmp_project, risk_gateway, s)

        entries = self._read_audit(tmp_project)
        logged_commands = {e["command"] for e in entries}
        for cmd in commands:
            assert cmd in logged_commands, f"{cmd} not found in audit log"

    def test_audit_entry_has_required_fields(self, tmp_project, risk_gateway, state):
        self._run_command("/status", tmp_project, risk_gateway, state)
        entries = self._read_audit(tmp_project)
        assert entries, "Audit log is empty"
        entry = entries[-1]
        for field in ("timestamp", "actor", "chat_id", "command", "authorized", "action"):
            assert field in entry, f"Missing field '{field}' in audit entry"

    def test_unauthorized_attempt_logged_with_authorized_false(self, tmp_project, risk_gateway, state):
        with patch("src.telegram.telegram_sender.TelegramSender.send_message"):
            gw = make_gateway(tmp_project, risk_gateway, state)
            dispatch_command(gw, "/status", chat_id="000000000")

        entries = self._read_audit(tmp_project)
        unauth = [e for e in entries if not e["authorized"]]
        assert unauth, "Unauthorized attempt not logged"
        assert unauth[-1]["authorized"] is False

    def test_audit_command_via_gateway_audit_command(self, tmp_project, risk_gateway, state):
        # First generate an entry then query via /audit
        self._run_command("/status", tmp_project, risk_gateway, state)

        with patch("src.telegram.telegram_sender.TelegramSender.send_message") as mock_send:
            gw = make_gateway(tmp_project, risk_gateway, state)
            dispatch_command(gw, "/audit")
            msg = mock_send.call_args[0][0]
        # /audit response should contain at least one entry reference
        assert "/status" in msg or "audit" in msg.lower() or "Audit" in msg


# ===========================================================================
# 8. Blocked commands
# ===========================================================================

class TestBlockedCommands:

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_buy_command_blocked(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/buy BTC 0.1")
        msg = mock_send.call_args[0][0]
        assert "not permitted" in msg or "disabled" in msg or "blocked" in msg.lower()

    @patch("src.telegram.telegram_sender.TelegramSender.send_message")
    def test_sell_command_blocked(self, mock_send, tmp_project, risk_gateway, state):
        gw = make_gateway(tmp_project, risk_gateway, state)
        dispatch_command(gw, "/sell BTC 0.1")
        msg = mock_send.call_args[0][0]
        assert "not permitted" in msg or "disabled" in msg or "blocked" in msg.lower()


# ===========================================================================
# 9. GatewayState thread-safety smoke test
# ===========================================================================

class TestGatewayStateThreadSafety:

    def test_concurrent_pause_resume_is_safe(self):
        state = GatewayState()
        errors: List[Exception] = []

        def toggle():
            try:
                for _ in range(100):
                    state.pause()
                    state.resume()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=toggle) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety errors: {errors}"
