from __future__ import annotations
from typing import Any, Dict, List
from src.core.models import RiskDecision

class RiskGateway:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("risk_engine", {})
        self.enabled = self.config.get("enabled", True)
        self.max_daily_loss_pct = float(self.config.get("max_daily_loss_pct", 2.0))
        self.max_basket_risk_pct = float(self.config.get("max_basket_risk_pct", 0.75))
        self.max_total_open_risk_pct = float(self.config.get("max_total_open_risk_pct", 1.5))
        self.max_open_positions_total = int(self.config.get("max_open_positions_total", 10))
        self.max_open_positions_per_symbol = int(self.config.get("max_open_positions_per_symbol", 2))
        self.max_pending_orders_per_symbol = int(self.config.get("max_pending_orders_per_symbol", 3))
        self.max_same_direction_assets = int(self.config.get("max_same_direction_assets", 3))
        self.block_trade_if_spread_high = self.config.get("block_trade_if_spread_high", True)

    def full_gate(self, account: Dict[str, Any], market: Dict[str, Any], symbol_state: Dict[str, Any] = None) -> RiskDecision:
        if not self.enabled:
            return RiskDecision("ALLOW", [])
            
        symbol_state = symbol_state or {}
        reasons = []
        
        if account.get("daily_dd_pct", 0) >= self.max_daily_loss_pct: 
            reasons.append("daily_loss_limit")
            
        if account.get("total_open_risk_pct", 0) >= self.max_total_open_risk_pct:
            reasons.append("total_open_risk_limit")
            
        if account.get("open_positions_total", 0) >= self.max_open_positions_total:
            reasons.append("max_open_positions_total")
            
        if symbol_state.get("open_positions", 0) >= self.max_open_positions_per_symbol:
            reasons.append("max_open_positions_symbol")
            
        if symbol_state.get("pending_orders", 0) >= self.max_pending_orders_per_symbol:
            reasons.append("max_pending_orders_symbol")
            
        if symbol_state.get("basket_risk_pct", 0) >= self.max_basket_risk_pct:
            reasons.append("basket_risk_limit")

        if market.get("session_flag") == "off": 
            reasons.append("off_session")
            
        if self.block_trade_if_spread_high and market.get("spread_high", False):
            reasons.append("spread_high")
        
        # NOTE: Correlation guards require cross-asset state, normally checked by OrderRouter or a higher level Aggregator, 
        # but we can assume 'account' dict passes this info down if needed.
        if account.get("same_direction_count", 0) >= self.max_same_direction_assets:
            reasons.append("max_same_direction_assets")
            
        action = "BLOCK" if reasons else "ALLOW"
        return RiskDecision(action, reasons)
