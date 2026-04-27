from __future__ import annotations
from typing import Any, Dict, List
from src.core.models import RiskDecision

class RiskGateway:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_daily_loss_pct = float(config.get("max_daily_loss_pct", 2.0))
        self.max_loss_streak = int(config.get("max_loss_streak", 5))

    def full_gate(self, account: Dict[str, Any], market: Dict[str, Any]) -> RiskDecision:
        reasons = []
        if account.get("daily_dd_pct", 0) >= self.max_daily_loss_pct: reasons.append("daily_loss_limit")
        if account.get("loss_streak", 0) >= self.max_loss_streak: reasons.append("loss_streak_limit")
        if market.get("session_flag") == "off": reasons.append("off_session")
        
        action = "BLOCK" if reasons else "ALLOW"
        return RiskDecision(action, reasons)
