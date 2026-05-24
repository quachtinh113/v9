"""
telegram_formatter.py – Message formatting helpers for the Telegram Command Gateway.

All formatting is isolated here so the gateway logic stays clean and display
changes don't require touching business logic.

HTML parse_mode is used throughout (Telegram supports bold, italic, code, etc.).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe(val: Any, decimals: int = 2) -> str:
    """Safely format a numeric value or return 'N/A'."""
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


# ---------------------------------------------------------------------------
# Status / health
# ---------------------------------------------------------------------------

def fmt_status(
    symbol: str,
    is_paused: bool,
    emergency_stopped: bool,
    last_tick_ts: Optional[str] = None,
    pipeline_uptime: Optional[str] = None,
) -> str:
    state_icon = "🔴 EMERGENCY STOP" if emergency_stopped else ("⏸ PAUSED" if is_paused else "✅ RUNNING")
    lines = [
        f"<b>📊 Pipeline Status – {symbol}</b>",
        f"State : {state_icon}",
        f"Last tick : {last_tick_ts or 'unknown'}",
        f"Uptime    : {pipeline_uptime or 'N/A'}",
        f"Queried   : {_now_utc()}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Risk snapshot
# ---------------------------------------------------------------------------

def fmt_risk(
    daily_dd_pct: float,
    weekly_dd_pct: float,
    loss_streak: int,
    open_exposure_pct: float,
    risk_action: str,
    risk_reasons: Optional[List[str]] = None,
    daily_dd_limit: float = 2.0,
    weekly_dd_limit: float = 4.0,
    loss_streak_limit: int = 3,
) -> str:
    def pct_bar(val: float, limit: float) -> str:
        ratio = min(val / limit, 1.0) if limit > 0 else 0.0
        filled = int(ratio * 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"[{bar}] {val:.2f}% / {limit:.2f}%"

    action_icon = {"ALLOW": "✅", "SOFT_BLOCK": "⚠️", "HARD_KILL": "🚨"}.get(risk_action, "❓")
    reasons_str = ", ".join(risk_reasons) if risk_reasons else "none"

    lines = [
        "<b>🛡 Risk Snapshot</b>",
        "",
        f"<b>Daily DD   :</b> {pct_bar(daily_dd_pct, daily_dd_limit)}",
        f"<b>Weekly DD  :</b> {pct_bar(weekly_dd_pct, weekly_dd_limit)}",
        f"<b>Loss streak:</b> {loss_streak} / {loss_streak_limit}",
        f"<b>Open exp.  :</b> {_safe(open_exposure_pct)}%",
        "",
        f"<b>Gate status:</b> {action_icon} {risk_action}",
        f"<b>Reasons    :</b> <code>{reasons_str}</code>",
        f"<i>{_now_utc()}</i>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def fmt_positions(positions: List[Dict[str, Any]]) -> str:
    if not positions:
        return "<b>📂 Open Positions</b>\n\nNo open positions."

    lines = [f"<b>📂 Open Positions ({len(positions)})</b>", ""]
    for i, pos in enumerate(positions, 1):
        direction = pos.get("direction", "N/A").upper()
        icon = "🟢" if direction == "LONG" else "🔴"
        lines.append(
            f"{i}. {icon} {direction} | "
            f"Entry: {_safe(pos.get('entry'))} | "
            f"Size: {_safe(pos.get('size'))} | "
            f"PnL: {_safe(pos.get('unrealized_pnl'))} | "
            f"Since: {pos.get('entry_time', 'N/A')}"
        )
    lines.append(f"\n<i>{_now_utc()}</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit log tail
# ---------------------------------------------------------------------------

def fmt_audit(entries: List[Dict[str, Any]], max_lines: int = 10) -> str:
    if not entries:
        return "<b>📋 Audit Log</b>\n\nNo recent entries."

    lines = [f"<b>📋 Audit Log – last {min(len(entries), max_lines)} entries</b>", ""]
    for entry in entries[-max_lines:]:
        ts = entry.get("timestamp", entry.get("bar_ts", "?"))
        actor = entry.get("actor", "pipeline")
        action = entry.get("action", entry.get("risk_action", "?"))
        detail = entry.get("detail", entry.get("command", ""))
        lines.append(f"<code>{ts}</code> [{actor}] <b>{action}</b> {detail}")

    lines.append(f"\n<i>{_now_utc()}</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Control confirmations
# ---------------------------------------------------------------------------

def fmt_pause_confirmation(symbol: str) -> str:
    return (
        f"⏸ <b>PAUSED – {symbol}</b>\n\n"
        "New entries are <b>disabled</b>.\n"
        "Existing positions remain open.\n"
        "RiskGateway continues monitoring.\n\n"
        f"<i>{_now_utc()}</i>"
    )


def fmt_resume_confirmation(symbol: str) -> str:
    return (
        f"▶️ <b>RESUMED – {symbol}</b>\n\n"
        "New entries are <b>re-enabled</b> (subject to RiskGateway approval).\n\n"
        f"<i>{_now_utc()}</i>"
    )


def fmt_resume_blocked(risk_action: str, reasons: List[str]) -> str:
    reasons_str = ", ".join(reasons) if reasons else "none"
    return (
        f"❌ <b>RESUME BLOCKED by RiskGateway</b>\n\n"
        f"Gate status : <code>{risk_action}</code>\n"
        f"Reasons     : <code>{reasons_str}</code>\n\n"
        "Fix the risk condition first, then try <code>/resume</code> again.\n"
        f"<i>{_now_utc()}</i>"
    )


def fmt_kill_confirmation(symbol: str) -> str:
    return (
        f"🚨 <b>EMERGENCY STOP TRIGGERED – {symbol}</b>\n\n"
        "• New entries: <b>DISABLED</b>\n"
        "• Emergency stop flag: <b>SET</b>\n"
        "• Operator action required to clear.\n\n"
        f"<i>{_now_utc()}</i>"
    )


# ---------------------------------------------------------------------------
# Error / unauthorized
# ---------------------------------------------------------------------------

def fmt_unauthorized(chat_id: Any) -> str:
    return f"⛔ <b>Unauthorized</b>\nChat ID <code>{chat_id}</code> is not permitted."


def fmt_unknown_command(cmd: str) -> str:
    supported = ["/status", "/report", "/risk", "/positions", "/pause", "/resume", "/kill", "/audit"]
    return (
        f"❓ Unknown command: <code>{cmd}</code>\n\n"
        f"Supported commands:\n" + "\n".join(f"  • {c}" for c in supported)
    )


def fmt_error(command: str, detail: str) -> str:
    return (
        f"❌ <b>Error executing {command}</b>\n"
        f"<code>{detail}</code>\n\n"
        "Please check the logs."
    )


# ---------------------------------------------------------------------------
# Report caption
# ---------------------------------------------------------------------------

def fmt_report_caption(report_path: Path) -> str:
    mtime = datetime.fromtimestamp(report_path.stat().st_mtime, tz=timezone.utc)
    return (
        f"📄 <b>Latest Market Research Report</b>\n"
        f"File: <code>{report_path.name}</code>\n"
        f"Generated: {mtime.strftime('%Y-%m-%d %H:%M UTC')}"
    )
