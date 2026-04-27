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

        if self.execution_config.get("send_notifications", False) and self.telegram:
            self.telegram.send_message(f"🚀 <b>Order Routed</b> [{symbol}]\nAction: {decision.action}")

        return {"status": "paper_only"}
