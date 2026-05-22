from __future__ import annotations
from typing import Any, Dict, List
from src.core.models import RiskDecision

class RiskGateway:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.daily_loss_limit_pct = float(self.config.get("daily_loss_limit_pct", 2.0))
        self.weekly_soft_stop_pct = float(self.config.get("weekly_soft_stop_pct", 4.0))
        self.hard_drawdown_pct = float(self.config.get("hard_drawdown_pct", 8.0))
        self.loss_streak_pause = int(self.config.get("loss_streak_pause", 3))
        self.spread_guard_enabled = bool(self.config.get("spread_guard_enabled", False))
        self.slippage_guard_enabled = bool(self.config.get("slippage_guard_enabled", False))
        self.atr_shock_block_enabled = bool(self.config.get("atr_shock_block_enabled", False))

    def full_gate(self, account: Dict[str, Any], market: Dict[str, Any]) -> RiskDecision:
        reasons = []
        action = "ALLOW"
        
        daily_dd_pct = float(account.get("daily_dd_pct", 0.0))
        weekly_dd_pct = float(account.get("weekly_dd_pct", 0.0))
        loss_streak = int(account.get("loss_streak", 0))
        open_positions = int(account.get("open_positions", 0))
        
        # Hard kill checks
        if daily_dd_pct >= self.hard_drawdown_pct:
            reasons.append("daily_hard_drawdown")
            action = "HARD_KILL"
        if weekly_dd_pct >= self.hard_drawdown_pct:
            reasons.append("weekly_hard_drawdown")
            action = "HARD_KILL"
            
        # Soft block checks
        if daily_dd_pct >= self.daily_loss_limit_pct:
            reasons.append("daily_loss_limit")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        if weekly_dd_pct >= self.weekly_soft_stop_pct:
            reasons.append("weekly_soft_stop")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        if loss_streak >= self.loss_streak_pause:
            reasons.append("loss_streak_limit")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        if market.get("session_flag") == "off":
            reasons.append("off_session")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        # Spread protection
        if self.spread_guard_enabled:
            spread_limit = float(self.config.get("spread_limit_bps", 5.0))
            current_spread = float(market.get("spread_bps", market.get("spread", 0.0)))
            if current_spread >= spread_limit:
                reasons.append("spread_guard_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"

        # Slippage protection
        if self.slippage_guard_enabled:
            slippage_limit = float(self.config.get("slippage_limit_bps", 3.0))
            current_slippage = float(market.get("slippage_bps", market.get("slippage", 0.0)))
            if current_slippage >= slippage_limit:
                reasons.append("slippage_guard_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"

        # Volatility ATR shock protection
        if self.atr_shock_block_enabled:
            atr_ratio_limit = float(self.config.get("atr_ratio_limit", 2.0))
            current_atr_ratio = float(market.get("atr_ratio", 1.0))
            if current_atr_ratio >= atr_ratio_limit:
                reasons.append("atr_shock_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"
                
        return RiskDecision(
            action=action,
            reasons=reasons,
            daily_dd_pct=daily_dd_pct,
            weekly_dd_pct=weekly_dd_pct,
            loss_streak=loss_streak,
            open_positions=open_positions,
        )

