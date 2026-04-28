from __future__ import annotations
from typing import Dict, Any, Optional
from src.core.models import PositionPlan, PositionLayer, SignalDecision
from src.position.dca_engine import DCAEngine

def build_position(
    decision: SignalDecision,
    price: float,
    atr: float,
    tick_value: float,
    account_balance: float,
    risk_config: Dict[str, Any],
    dca_config: Dict[str, Any],
    timeout_minutes: int = 120,
    stop_atr_mult: float = 1.5,
    tp_atr_mult: float = 2.0
) -> Optional[PositionPlan]:
    
    if decision.direction == "flat": 
        return None
        
    stop_dist = atr * stop_atr_mult
    tp_dist = atr * tp_atr_mult # FIXED bug: was tp_mult
    
    sl = price - stop_dist if decision.direction == "long" else price + stop_dist
    tp = price + tp_dist if decision.direction == "long" else price - tp_dist
    
    # Dynamic Risk-Based Lot Sizing
    risk_pct = float(risk_config.get("risk_per_trade_pct", 0.15)) / 100.0
    risk_money = account_balance * risk_pct
    
    # Calculate lot size: lot = risk_money / (SL_distance_in_points * tick_value)
    # Assume price is in points for this simplified calculation, real implementation uses pip/point values
    # For robust point distance:
    dist_points = stop_dist
    if dist_points == 0 or tick_value == 0:
        base_lot = 0.01 # Fallback
    else:
        base_lot = round(risk_money / (dist_points * tick_value), 2)
        
    max_lot = float(risk_config.get("max_lot", {}).get(decision.symbol, 0.05))
    base_lot = min(max(base_lot, 0.01), max_lot) # Cap to max_lot and floor to 0.01

    layers = [PositionLayer(0, price, base_lot, "Base Layer")]
    
    dca_engine = DCAEngine({"dca": dca_config})
    if dca_engine.enabled:
        dca_layers = dca_engine.build_dca_plan(decision.symbol, price, decision.direction, atr, base_lot)
        layers.extend(dca_layers)
        
    return PositionPlan(price, sl, tp, base_lot, timeout_minutes, layers=layers)
