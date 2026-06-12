from src.core.models import PositionPlan, SignalDecision
from src.core.signal_engine import evaluate_signal

def generate_trade_plan(features, config=None):
    decision = evaluate_signal(features, config)
    if decision.direction == "flat": 
        return None, decision
        
    cfg = config or {}
    entry = float(features["close_m1"])
    atr = float(features.get("atr14_m1", 0.001))
    
    # ATR multipliers for dynamic stop loss and take profit
    stop_atr_mult = float(cfg.get("position", {}).get("stop_atr_mult", 1.8))
    tp_atr_mult = float(cfg.get("position", {}).get("tp_atr_mult", 2.5))
    
    if decision.direction == "long":
        sl = entry - stop_atr_mult * atr
        tp = entry + tp_atr_mult * atr
    else: # short
        sl = entry + stop_atr_mult * atr
        tp = entry - tp_atr_mult * atr
        
    # Position Sizing: Risk-based sizing
    capital = float(cfg.get("backtest", {}).get("initial_capital", 10000.0))
    risk_pct = float(cfg.get("risk", {}).get("risk_per_trade_pct", 0.25))
    risk_amount = capital * (risk_pct / 100.0)
    
    sl_distance = abs(entry - sl)
    
    # Apply ML gatekeeper size multiplier
    size_mult = float(decision.size_multiplier)
    
    # Check if fixed lot size is configured and explicitly enabled
    fixed_lot = cfg.get("risk", {}).get("fixed_lot_size")
    if fixed_lot is not None:
        size = float(fixed_lot) * size_mult
    else:
        if sl_distance > 0:
            size = (risk_amount / sl_distance) * size_mult
        else:
            size = 0.0
            
    # Round lot size to 2 decimal places (standard broker constraint)
    size = round(max(size, 0.01), 2)
    
    plan = PositionPlan(
        entry=entry,
        stop_loss=sl,
        take_profit=tp,
        size=size,
        timeout_minutes=int(cfg.get("position", {}).get("timeout_minutes", 120))
    )
    
    # SL/TP validation
    plan_valid = False
    if decision.direction == "long":
        if sl < entry < tp:
            plan_valid = True
    elif decision.direction == "short":
        if tp < entry < sl:
            plan_valid = True
            
    decision.position_plan_valid = plan_valid
    if not plan_valid:
        decision.entry_allowed = False
        decision.blocked_reasons.append("invalid_position_plan_bounds")
        return None, decision
        
    return plan, decision
