from typing import Any, Dict, Optional
from src.core.models import PositionPlan, SignalDecision, RiskDecision
from src.execution.mt5_adapter import MT5Adapter
from src.execution.trade_journal import TradeJournal
from src.utils.telegram_bot import TelegramBot


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
        self.journal = journal
        self.telegram = telegram
        self.last_fingerprint: str | None = None

    def route_order(
        self,
        plan: PositionPlan,
        decision: SignalDecision,
        risk_decision: RiskDecision,
        bar_ts: str = "",
    ) -> Dict[str, Any]:
        symbol = decision.symbol

        if risk_decision.action != "ALLOW":
            if risk_decision.action == "HARD_KILL" and self.telegram:
                self.telegram.send_message(f"⚠️ <b>HARD KILL</b> [{symbol}]\nReason: {risk_decision.reasons}")
            return {"status": f"blocked_{risk_decision.action.lower()}"}

        # Build order payload with sanitized comment
        comment_prefix = self.execution_config.get('comment_prefix', 'quant')
        sanitized_ts = bar_ts.replace(':', '_').replace(' ', '_')
        comment = f"{comment_prefix}_{sanitized_ts}"[:30]
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

        res = self.adapter.send_order(order_req)

        if self.journal:
            self.journal.write(bar_ts, {**order_req, "response": res})

        if self.execution_config.get("send_notifications", False) and self.telegram:
            self.telegram.send_message(
                f"🚀 <b>Order Routed</b> [{symbol}]\nStatus: {res.get('status')} Price: {res.get('price')}"
            )

        return res
