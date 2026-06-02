from __future__ import annotations
from typing import Any, Dict, List
import yaml
from pathlib import Path
from src.core.models import RiskDecision

class RiskGateway:
    def __init__(self, config: Dict[str, Any]):
        # Load from risk.yaml if it exists to keep local laptop configs in sync
        self.config = {}
        try:
            project_root = Path(__file__).resolve().parents[2]
            risk_yaml_path = project_root / "config" / "risk.yaml"
            if risk_yaml_path.exists():
                with open(risk_yaml_path, "r", encoding="utf-8") as f:
                    self.config.update(yaml.safe_load(f) or {})
        except Exception:
            pass
            
        # Merge passed config (typically from symbol.yaml in backtesting or pipeline_live)
        if config:
            self.config.update(config)
            
        self.daily_loss_limit_pct = float(self.config.get("daily_loss_limit_pct", 2.0))
        self.weekly_soft_stop_pct = float(self.config.get("weekly_soft_stop_pct", 4.0))
        self.hard_drawdown_pct = float(self.config.get("hard_drawdown_pct", 8.0))
        self.loss_streak_pause = int(self.config.get("loss_streak_pause", 3))
        self.spread_guard_enabled = bool(self.config.get("spread_guard_enabled", False))
        self.slippage_guard_enabled = bool(self.config.get("slippage_guard_enabled", False))
        self.atr_shock_block_enabled = bool(self.config.get("atr_shock_block_enabled", False))
        
        # New explicit configuration fields
        self.spread_limit_bps = float(self.config.get("spread_limit_bps", 5.0))
        self.slippage_limit_bps = float(self.config.get("slippage_limit_bps", 3.0))
        self.atr_ratio_limit = float(self.config.get("atr_ratio_limit", 2.0))
        self.max_open_positions = int(self.config.get("max_open_positions", 2))
        self.max_daily_trades = int(self.config.get("max_daily_trades", 5))
        self.max_symbol_exposure = float(self.config.get("max_symbol_exposure", 0.05))
        self.news_blackout_enabled = bool(self.config.get("news_blackout_enabled", True))
        self.transition_trade_enabled = bool(self.config.get("transition_trade_enabled", False))

        # Execution Frequency & Loss Brake configurations
        self.max_trades_per_symbol_per_hour = int(self.config.get("max_trades_per_symbol_per_hour", 3))
        self.min_seconds_between_same_symbol_trades = float(self.config.get("min_seconds_between_same_symbol_trades", 300))
        self.stop_symbol_after_n_consecutive_losses = int(self.config.get("stop_symbol_after_n_consecutive_losses", 3))
        self.fleet_loss_streak_brake = int(self.config.get("fleet_loss_streak_brake", 8))
        self.cooldown_after_loss_minutes = float(self.config.get("cooldown_after_loss_minutes", 30))
        self.max_open_trades_per_symbol = int(self.config.get("max_open_trades_per_symbol", 1))

    def full_gate(self, account: Dict[str, Any], market: Dict[str, Any]) -> RiskDecision:
        reasons = []
        action = "ALLOW"
        
        # Fail closed if market or account data is missing
        if account is None or market is None:
            return RiskDecision(action="HARD_KILL", reasons=["missing_account_or_market_data"])
            
        required_account_fields = ["daily_dd_pct", "weekly_dd_pct", "loss_streak"]
        required_market_fields = ["spread_bps", "slippage_bps", "atr_ratio", "session_flag"]
        
        for f in required_account_fields:
            if f not in account or account[f] is None:
                reasons.append(f"missing_account_field_{f}")
                action = "HARD_KILL"
        for f in required_market_fields:
            if f not in market or market[f] is None:
                reasons.append(f"missing_market_field_{f}")
                action = "HARD_KILL"
                
        if action == "HARD_KILL":
            return RiskDecision(action=action, reasons=reasons)
            
        daily_dd_pct = float(account.get("daily_dd_pct", 0.0))
        weekly_dd_pct = float(account.get("weekly_dd_pct", 0.0))
        loss_streak = int(account.get("loss_streak", 0))
        open_positions = int(account.get("open_positions", 0))
        daily_trades_count = int(account.get("daily_trades_count", 0))

        # Execution frequency guards
        trades_last_hour = int(account.get("trades_last_hour", 0))
        if trades_last_hour >= self.max_trades_per_symbol_per_hour:
            reasons.append("max_trades_per_hour_exceeded")
            action = "HARD_KILL"
            
        seconds_since_last_trade = float(account.get("seconds_since_last_trade", 999999))
        if seconds_since_last_trade < self.min_seconds_between_same_symbol_trades:
            reasons.append("too_soon_since_last_trade")
            action = "HARD_KILL"
            
        if open_positions >= self.max_open_trades_per_symbol:
            reasons.append("max_open_trades_per_symbol_exceeded")
            action = "HARD_KILL"
            
        open_directions = account.get("open_directions", [])
        pending_direction = market.get("pending_direction", None)
        if pending_direction and pending_direction in open_directions:
            reasons.append("duplicate_direction_open")
            action = "HARD_KILL"
            
        # Loss brakes
        consecutive_losses_symbol = int(account.get("consecutive_losses_symbol", 0))
        if consecutive_losses_symbol >= self.stop_symbol_after_n_consecutive_losses:
            reasons.append("symbol_consecutive_loss_limit")
            action = "HARD_KILL"
            
        fleet_loss_streak = int(account.get("fleet_loss_streak", 0))
        if fleet_loss_streak >= self.fleet_loss_streak_brake:
            reasons.append("fleet_loss_streak_limit")
            action = "HARD_KILL"
            
        seconds_since_last_loss = float(account.get("seconds_since_last_loss", 999999))
        cooldown_seconds = self.cooldown_after_loss_minutes * 60
        if seconds_since_last_loss < cooldown_seconds:
            reasons.append("loss_cooldown_active")
            action = "HARD_KILL"
        
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
                
        # Session restriction
        session_flag = market.get("session_flag")
        if session_flag == "off":
            reasons.append("off_session")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        # Transition trading restrictions
        if session_flag == "transition" or market.get("regime") == "transition":
            if not self.transition_trade_enabled:
                reasons.append("transition_trading_disabled")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"
                    
        # Max open positions limit
        if open_positions >= self.max_open_positions:
            reasons.append("max_open_positions_exceeded")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        # Max daily trades count limit
        if daily_trades_count >= self.max_daily_trades:
            reasons.append("max_daily_trades_exceeded")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        # Spread protection check
        if self.spread_guard_enabled:
            current_spread = float(market.get("spread_bps", 0.0))
            if current_spread >= self.spread_limit_bps:
                reasons.append("spread_guard_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"
                    
        # Slippage protection check
        if self.slippage_guard_enabled:
            current_slippage = float(market.get("slippage_bps", 0.0))
            if current_slippage >= self.slippage_limit_bps:
                reasons.append("slippage_guard_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"
                    
        # Volatility ATR shock protection check
        if self.atr_shock_block_enabled:
            current_atr_ratio = float(market.get("atr_ratio", 1.0))
            if current_atr_ratio >= self.atr_ratio_limit:
                reasons.append("atr_shock_trigger")
                if action != "HARD_KILL":
                    action = "SOFT_BLOCK"
                    
        # News blackout protection check
        if self.news_blackout_enabled and market.get("news_blackout", False):
            reasons.append("news_blackout_active")
            if action != "HARD_KILL":
                action = "SOFT_BLOCK"
                
        return RiskDecision(
            action=action,
            reasons=reasons,
            daily_dd_pct=daily_dd_pct,
            weekly_dd_pct=weekly_dd_pct,
            loss_streak=loss_streak,
            open_positions=open_positions
        )
