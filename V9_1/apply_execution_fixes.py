import os
import glob
import re

def update_risk_engine(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add config defaults in __init__
    if 'self.max_trades_per_symbol_per_hour' not in content:
        init_injection = """
        # Execution Frequency & Loss Brake configurations
        self.max_trades_per_symbol_per_hour = int(self.config.get("max_trades_per_symbol_per_hour", 3))
        self.min_seconds_between_same_symbol_trades = float(self.config.get("min_seconds_between_same_symbol_trades", 300))
        self.stop_symbol_after_n_consecutive_losses = int(self.config.get("stop_symbol_after_n_consecutive_losses", 3))
        self.fleet_loss_streak_brake = int(self.config.get("fleet_loss_streak_brake", 8))
        self.cooldown_after_loss_minutes = float(self.config.get("cooldown_after_loss_minutes", 30))
        self.max_open_trades_per_symbol = int(self.config.get("max_open_trades_per_symbol", 1))
"""
        content = re.sub(r'(self\.transition_trade_enabled = .*?\n)', r'\1' + init_injection, content, count=1)

    # Add gate checks in full_gate
    if 'max_trades_per_hour_exceeded' not in content:
        gate_injection = """
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
"""
        content = re.sub(r'(daily_trades_count = int\(account\.get\("daily_trades_count", 0\)\)\n)', r'\1' + gate_injection, content, count=1)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def update_pipeline_live(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Inject variables for account_data and market_data
    if '"trades_last_hour":' not in content:
        account_data_injection = """
                "trades_last_hour": getattr(self, "trades_last_hour", 0),
                "seconds_since_last_trade": getattr(self, "seconds_since_last_trade", 999999),
                "open_directions": getattr(self, "open_directions", []),
                "consecutive_losses_symbol": getattr(self, "consecutive_losses_symbol", 0),
                "fleet_loss_streak": getattr(self, "fleet_loss_streak", 0),
                "seconds_since_last_loss": getattr(self, "seconds_since_last_loss", 999999),
"""
        content = re.sub(r'("loss_streak": self\.loss_streak,\n)', r'\1' + account_data_injection, content, count=1)
        
        market_data_injection = """
                "pending_direction": decision.direction,
"""
        content = re.sub(r'("session_flag": row\.get\("session_flag", "london"\),\n)', r'\1' + market_data_injection, content, count=1)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def update_trade_journal(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '"trades_last_hour":' not in content:
        # We need to add the requested fields to write_loop_audit
        # The prompt asks for: symbol, direction, signal_score, regime, adx, rsi, ml_score, risk_decision, veto_reason, cooldown_status, trades_last_hour, consecutive_losses_symbol, consecutive_losses_fleet
        # Some are already there. Let's patch write_loop_audit arguments and the dict.
        
        # In write_loop_audit arguments, add new ones if not present
        if 'trades_last_hour=None' not in content:
            content = re.sub(
                r'(def write_loop_audit\(self, symbol, tick_ok, broker_symbol, data_stale, regime_result, signal_result, ml_mode, ml_score, risk_decision, execution_mode, order_send_called, ml_gate_mode=None, ml_block_applied=None, ml_reason=None, model_provenance_valid=None, model_id=None, model_status=None, allowed_to_block=None, details=None, rsi14_m15=None, adx14_h1=None, atr14_m1=None, spread_bps=None, effective_spread=None, regime=None, session_state=None, signal_score=None)',
                r'\1, trades_last_hour=None, consecutive_losses_symbol=None, consecutive_losses_fleet=None, cooldown_status=None, veto_reason=None',
                content
            )

        # In the entry dict
        audit_fields_injection = """
            "trades_last_hour": trades_last_hour,
            "consecutive_losses_symbol": consecutive_losses_symbol,
            "consecutive_losses_fleet": consecutive_losses_fleet,
            "cooldown_status": cooldown_status,
            "veto_reason": veto_reason,
            "adx": adx14_h1,
            "rsi": rsi14_m15,
            "direction": signal_result,
"""
        content = re.sub(r'("details": details or \{\}\n\s+\})', audit_fields_injection + r'\1', content, count=1)
        
        # Second write_loop_audit block in the file (there seems to be duplicate in trade_journal)
        content = re.sub(r'(def write_loop_audit\(self.*?details=None\).*?:.*?)(entry = \{.*?"details": details or \{\}\n\s+\})', r'\1\2', content, flags=re.DOTALL) # Need to be careful here

    # To be safer with trade_journal.py, let's just do a direct string replace for the entry dictionary
    # Actually, it's easier to just replace the whole write_loop_audit if needed, or append to `details` if it's dynamic.
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

projects_dir = r"c:\Quant Trade\v9\V9_1\projects"
for proj in os.listdir(projects_dir):
    proj_path = os.path.join(projects_dir, proj)
    if os.path.isdir(proj_path):
        re_path = os.path.join(proj_path, "src", "core", "risk_engine.py")
        pl_path = os.path.join(proj_path, "src", "pipeline_live.py")
        tj_path = os.path.join(proj_path, "src", "execution", "trade_journal.py")
        
        if os.path.exists(re_path):
            update_risk_engine(re_path)
        if os.path.exists(pl_path):
            update_pipeline_live(pl_path)
        if os.path.exists(tj_path):
            update_trade_journal(tj_path)

print("Patching complete.")
