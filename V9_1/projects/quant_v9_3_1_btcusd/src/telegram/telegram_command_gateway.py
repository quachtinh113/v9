"""
telegram_command_gateway.py – Safe Telegram Command Gateway for Quant V9.

Design principles:
  ─────────────────────────────────────────────────────────────────────────
  1. SECURITY FIRST  – Only the authorized chat_id (from .env) can issue
     commands.  All attempts are logged regardless of success/failure.

  2. NO BYPASS       – RiskGateway is ALWAYS consulted.  /resume will fail
     if the gateway is in SOFT_BLOCK or HARD_KILL state.

  3. NO EXECUTION    – No BUY / SELL orders are issued by this gateway.
     The gateway only reads state and toggles pause/kill flags.

  4. AUDIT TRAIL     – Every incoming command (authorized or not) is appended
     to the Telegram command audit log (logs/telegram_audit.ndjson).

  5. POLLING LOOP    – Uses Telegram long-polling (getUpdates).  Run as a
     standalone thread or process alongside LivePipeline.
  ─────────────────────────────────────────────────────────────────────────

Supported commands:
  /status    – Pipeline health (running / paused / emergency-stopped)
  /report    – Send latest market research report file
  /risk      – Current risk metrics (DD, streak, exposure, gate)
  /positions – Open position summary
  /pause     – Disable new entries (positions remain open)
  /resume    – Re-enable entries, only if RiskGateway allows
  /kill      – Set emergency stop flag (irreversible via Telegram)
  /audit     – Last N command-gateway audit log entries

Blocked:
  /buy, /sell – Not implemented.  Will return a clear rejection message.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from src.telegram.telegram_auth import TelegramAuth, TelegramAuthError
from src.telegram.telegram_formatter import (
    fmt_audit,
    fmt_error,
    fmt_kill_confirmation,
    fmt_pause_confirmation,
    fmt_positions,
    fmt_report_caption,
    fmt_resume_blocked,
    fmt_resume_confirmation,
    fmt_risk,
    fmt_status,
    fmt_unauthorized,
    fmt_unknown_command,
)
from src.telegram.telegram_sender import TelegramSender

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared runtime state
# ---------------------------------------------------------------------------

class GatewayState:
    """Thread-safe runtime flags shared between pipeline and gateway."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.is_paused: bool = False
        self.emergency_stopped: bool = False
        self.last_tick_ts: Optional[str] = None
        self.start_time: datetime = datetime.now(timezone.utc)

    # --- Pause ----------------------------------------------------------

    def pause(self) -> None:
        with self._lock:
            self.is_paused = True
        logger.warning("[GatewayState] Pipeline PAUSED via Telegram command.")

    def resume(self) -> None:
        with self._lock:
            self.is_paused = False
        logger.info("[GatewayState] Pipeline RESUMED via Telegram command.")

    def kill(self) -> None:
        with self._lock:
            self.emergency_stopped = True
            self.is_paused = True  # also pause to be safe
        logger.critical("[GatewayState] EMERGENCY STOP TRIGGERED via Telegram command.")

    # --- Readable snapshots ---------------------------------------------

    @property
    def uptime(self) -> str:
        delta = datetime.now(timezone.utc) - self.start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}h {m:02d}m {s:02d}s"


# Singleton state object – import and share across modules.
GATEWAY_STATE = GatewayState()


# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------

class TelegramAuditLogger:
    """Appends every command invocation to an NDJSON file."""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        chat_id: Any,
        command: str,
        authorized: bool,
        result: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": "telegram",
            "chat_id": str(chat_id),
            "command": command,
            "authorized": authorized,
            "action": result,
            **(extra or {}),
        }
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.error("[TelegramAuditLogger] Cannot write audit log: %s", exc)

    def read_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        lines: List[Dict[str, Any]] = []
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
        return lines[-n:]


# ---------------------------------------------------------------------------
# Command Gateway
# ---------------------------------------------------------------------------

class TelegramCommandGateway:
    """
    Long-polling Telegram bot that processes operator commands.

    Intended to run in a background thread alongside LivePipeline.

    Args:
        project_root:    Root path of the quant project (for finding reports/logs).
        risk_gateway:    An initialised RiskGateway instance.
        state:           Shared GatewayState object (defaults to the module singleton).
        symbol:          Symbol string for display (e.g. "BTCUSD").
        account_fn:      Optional callable that returns the current account dict
                         (used by /risk and /resume to get fresh drawdown numbers).
        positions_fn:    Optional callable that returns list of open position dicts.
    """

    POLL_TIMEOUT = 30          # Telegram long-poll timeout seconds
    BLOCKED_COMMANDS = {"/buy", "/sell"}
    KNOWN_COMMANDS = {
        "/status", "/report", "/risk", "/positions",
        "/pause", "/resume", "/kill", "/audit",
    }

    def __init__(
        self,
        project_root: Path,
        risk_gateway: Any,           # src.core.risk_engine.RiskGateway
        state: Optional[GatewayState] = None,
        symbol: str = "BTCUSD",
        account_fn: Optional[Callable[[], Dict[str, Any]]] = None,
        positions_fn: Optional[Callable[[], List[Dict[str, Any]]]] = None,
    ) -> None:
        self._root = Path(project_root)
        self._risk_gateway = risk_gateway
        self._state = state or GATEWAY_STATE
        self._symbol = symbol
        self._account_fn = account_fn
        self._positions_fn = positions_fn

        self._auth = TelegramAuth()
        self._sender = TelegramSender()
        self._audit = TelegramAuditLogger(self._root / "logs" / "telegram_audit.ndjson")

        self._token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not self._token:
            raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set.")

        self._offset: int = 0
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the long-polling loop (blocking).  Call in a thread."""
        logger.info("[TelegramCommandGateway] Starting long-poll loop for %s…", self._symbol)
        self._running = True
        while self._running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._handle_update(update)
            except Exception as exc:
                logger.error("[TelegramCommandGateway] Poll error: %s", exc)
                time.sleep(5)

    def stop(self) -> None:
        self._running = False
        logger.info("[TelegramCommandGateway] Stopped.")

    def start_in_thread(self) -> threading.Thread:
        t = threading.Thread(target=self.start, daemon=True, name="TelegramGateway")
        t.start()
        return t

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _get_updates(self) -> List[Dict[str, Any]]:
        url = f"https://api.telegram.org/bot{self._token}/getUpdates"
        params = {"timeout": self.POLL_TIMEOUT, "offset": self._offset}
        resp = requests.get(url, params=params, timeout=self.POLL_TIMEOUT + 5)
        data = resp.json()
        updates = data.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return updates

    # ------------------------------------------------------------------
    # Update dispatch
    # ------------------------------------------------------------------

    def _handle_update(self, update: Dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat_id = str(message.get("chat", {}).get("id", ""))
        raw_text: str = (message.get("text") or "").strip()

        if not raw_text:
            return

        logger.debug("[TelegramCommandGateway] Received from chat=%s: %s", chat_id, raw_text[:80])

        # ── Authorization ─────────────────────────────────────────────
        try:
            clean_text = self._auth.validate_update(chat_id, raw_text)
        except TelegramAuthError as exc:
            logger.warning("[TelegramCommandGateway] Auth failed for chat_id=%s: %s", chat_id, exc)
            self._audit.log(chat_id, raw_text, authorized=False, result="AUTH_REJECTED")
            # Do NOT send any response to unauthorized senders (do not confirm bot existence)
            return

        # ── Extract base command (ignore args and @BotName suffix) ────
        parts = clean_text.split()
        if not parts:
            return
        cmd = parts[0].split("@")[0].lower()

        # ── Blocked commands ──────────────────────────────────────────
        if cmd in self.BLOCKED_COMMANDS:
            self._audit.log(chat_id, cmd, authorized=True, result="BLOCKED_COMMAND")
            self._sender.send_message(
                "🚫 <b>Command not permitted in this phase.</b>\n"
                "/buy and /sell are disabled for safety.\n"
                "All trade execution goes through RiskGateway only."
            )
            return

        # ── Dispatch known commands ───────────────────────────────────
        handlers = {
            "/status": self._cmd_status,
            "/report": self._cmd_report,
            "/risk": self._cmd_risk,
            "/positions": self._cmd_positions,
            "/pause": self._cmd_pause,
            "/resume": self._cmd_resume,
            "/kill": self._cmd_kill,
            "/audit": self._cmd_audit,
        }

        handler = handlers.get(cmd)
        if handler is None:
            self._audit.log(chat_id, cmd, authorized=True, result="UNKNOWN_COMMAND")
            self._sender.send_message(fmt_unknown_command(cmd))
            return

        # ── Execute & audit ───────────────────────────────────────────
        try:
            result_str = handler()
            self._audit.log(chat_id, cmd, authorized=True, result="OK")
        except Exception as exc:
            logger.exception("[TelegramCommandGateway] Error in handler for %s: %s", cmd, exc)
            self._audit.log(chat_id, cmd, authorized=True, result="ERROR", extra={"error": str(exc)})
            self._sender.send_message(fmt_error(cmd, str(exc)))

    # ------------------------------------------------------------------
    # Command handlers (each returns a result string for audit)
    # ------------------------------------------------------------------

    def _cmd_status(self) -> str:
        msg = fmt_status(
            symbol=self._symbol,
            is_paused=self._state.is_paused,
            emergency_stopped=self._state.emergency_stopped,
            last_tick_ts=self._state.last_tick_ts,
            pipeline_uptime=self._state.uptime,
        )
        self._sender.send_message(msg)
        return "OK"

    def _cmd_report(self) -> str:
        report_dir = self._root / "reports"
        # Find the most recently modified file in reports/**
        candidates = sorted(
            (p for p in report_dir.rglob("*") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            self._sender.send_message("📭 No report files found in <code>reports/</code>.")
            return "NO_REPORT"

        latest = candidates[0]
        caption = fmt_report_caption(latest)
        # Try to send as document; fall back to a text message with path
        sent = self._sender.send_document(latest, caption=caption)
        if not sent:
            self._sender.send_message(
                f"⚠️ Could not send document.\n{caption}\nPath: <code>{latest}</code>"
            )
        return "OK"

    def _cmd_risk(self) -> str:
        account = self._account_fn() if self._account_fn else {}
        market = {
            "spread_bps": 0.0,
            "slippage_bps": 0.0,
            "atr_ratio": 1.0,
            "session_flag": "unknown",
        }
        risk_decision = self._risk_gateway.full_gate(account, market)

        msg = fmt_risk(
            daily_dd_pct=risk_decision.daily_dd_pct,
            weekly_dd_pct=risk_decision.weekly_dd_pct,
            loss_streak=risk_decision.loss_streak,
            open_exposure_pct=account.get("open_exposure_pct", 0.0),
            risk_action=risk_decision.action,
            risk_reasons=risk_decision.reasons,
            daily_dd_limit=self._risk_gateway.daily_loss_limit_pct,
            weekly_dd_limit=self._risk_gateway.weekly_soft_stop_pct,
            loss_streak_limit=self._risk_gateway.loss_streak_pause,
        )
        self._sender.send_message(msg)
        return "OK"

    def _cmd_positions(self) -> str:
        positions = self._positions_fn() if self._positions_fn else []
        self._sender.send_message(fmt_positions(positions))
        return "OK"

    def _cmd_pause(self) -> str:
        self._state.pause()
        self._sender.send_message(fmt_pause_confirmation(self._symbol))
        return "PAUSED"

    def _cmd_resume(self) -> str:
        """Re-enable entries only if RiskGateway allows."""
        account = self._account_fn() if self._account_fn else {}
        market = {
            "spread_bps": 0.0,
            "slippage_bps": 0.0,
            "atr_ratio": 1.0,
            "session_flag": account.get("session_flag", "unknown"),
        }
        risk_decision = self._risk_gateway.full_gate(account, market)

        if risk_decision.action in {"SOFT_BLOCK", "HARD_KILL"}:
            self._sender.send_message(
                fmt_resume_blocked(risk_decision.action, risk_decision.reasons)
            )
            return f"RESUME_BLOCKED:{risk_decision.action}"

        self._state.resume()
        self._sender.send_message(fmt_resume_confirmation(self._symbol))
        return "RESUMED"

    def _cmd_kill(self) -> str:
        """Trigger emergency stop.  Irreversible via Telegram – requires manual restart."""
        self._state.kill()
        self._sender.send_message(fmt_kill_confirmation(self._symbol))
        logger.critical(
            "[TelegramCommandGateway] /kill executed. Emergency stop flag is SET."
        )
        return "EMERGENCY_STOP"

    def _cmd_audit(self) -> str:
        entries = self._audit.read_recent(n=10)
        self._sender.send_message(fmt_audit(entries))
        return "OK"
