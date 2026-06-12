from typing import Any, Dict, Optional
import json, logging, re
from src.core.models import PositionPlan, SignalDecision, RiskDecision
from src.execution.mt5_adapter import MT5Adapter
from src.execution.trade_journal import TradeJournal
from src.utils.telegram_bot import TelegramBot

# Helper to create a deterministic, safe MT5 comment string
def sanitize_mt5_comment(symbol: str, side: str) -> str:
    """Return a comment like 'QV9_GBPUSD_LONG' limited to 31 chars.
    Non‑alphanumeric characters are stripped, result is upper‑cased.
    """
    comment = f"QV9_{symbol.upper()}_{side.upper()}"
    comment = re.sub(r"[^A-Za-z0-9_]", "", comment)
    if len(comment) > 31:
        comment = comment[:31]
    return comment if comment else "QV9_ORDER"

# Configure module logger (JSON‑friendly)
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class OrderRouter:
    def __init__(
        self,
        adapter: MT5Adapter,
        execution_config: Dict[str, Any],
        journal: Optional[TradeJournal] = None,
        telegram: Optional[TelegramBot] = None,
    ) -> None:
        self.adapter = adapter
        self.execution_config = execution_config
        self.execution_mode = self.execution_config.get("mode", "live")
        self.journal = journal
        self.telegram = telegram
        self.last_fingerprint: str | None = None

    def route_order(
        self,
        plan: PositionPlan,
        decision: SignalDecision,
        risk_decision: RiskDecision,
        bar_ts: str = "",
        audit_logger = None,
    ) -> Dict[str, Any]:
        symbol = decision.symbol

        if risk_decision.action != "ALLOW":
            if risk_decision.action == "HARD_KILL" and self.telegram:
                self.telegram.send_message(f"⚠️ <b>HARD KILL</b> [{symbol}]\nReason: {risk_decision.reasons}")
            return {"status": f"blocked_{risk_decision.action.lower()}"}

        comment = sanitize_mt5_comment(symbol, decision.direction)
        order_req = {
            "symbol": symbol,
            "direction": decision.direction,
            "price": plan.entry,
            "sl": plan.stop_loss,
            "tp": plan.take_profit,
            "volume": self.execution_config.get("volume", 0.01),
            "magic": self.execution_config.get("magic_number", 93030),
            "deviation": self.execution_config.get("deviation", 20),
            "comment": comment,
        }

        logger.info(json.dumps({
            "symbol": symbol,
            "order_type": decision.direction,
            "volume": self.execution_config.get("volume", 0.01),
            "price": plan.entry,
            "sl": plan.stop_loss,
            "tp": plan.take_profit,
            "comment": comment,
            "comment_len": len(comment),
            "runtime_mode": self.execution_config.get("mode", "unknown"),
        }))

        # Determine execution mode – paper orders are simulated
        if self.execution_mode == "paper":
            # Simulate a successful paper order response
            simulated_res = {
                "status": "paper_success",
                "price": order_req.get("price"),
                "symbol": order_req.get("symbol"),
                "direction": order_req.get("direction"),
                "volume": order_req.get("volume", 0.01),
                "order_id": 999999,
                "comment": order_req.get("comment", "") + " (paper)"
            }
            if self.journal:
                self.journal.write(bar_ts, {**order_req, "response": simulated_res})
            # Send notification if enabled
            if self.execution_config.get("send_notifications", False) and self.telegram:
                self.telegram.send_message(
                    f"🚀 <b>Paper Order Routed</b> [{symbol}]\nStatus: {simulated_res.get('status')} Price: {simulated_res.get('price')}"
                )
            return simulated_res
        # LIVE path – unchanged
        res = self.adapter.send_order(order_req, audit_logger=audit_logger)

        if self.journal:
            self.journal.write(bar_ts, {**order_req, "response": res})

        if self.execution_config.get("send_notifications", False) and self.telegram:
            self.telegram.send_message(f"🚀 <b>Order Routed</b> [{symbol}]\nStatus: {res.get('status')} Price: {res.get('price')}")

        return res
