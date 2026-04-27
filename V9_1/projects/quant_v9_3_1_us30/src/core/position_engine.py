from __future__ import annotations
from typing import Dict, Any, Optional
from src.core.models import PositionPlan, PositionLayer, SignalDecision

def build_position(decision: SignalDecision, price: float, atr: float, risk_pct: float = 0.25, timeout_minutes: int = 120, stop_atr_mult: float = 1.5, tp_atr_mult: float = 2.0, max_layers: int = 1, dca_spacing_atr_mult: float = 1.0) -> Optional[PositionPlan]:
    if decision.direction == "flat": return None
    stop_dist = atr * stop_atr_mult
    tp_dist = atr * tp_mult
    sl = price - stop_dist if decision.direction == "long" else price + stop_dist
    tp = price + tp_dist if decision.direction == "long" else price - tp_dist
    return PositionPlan(price, sl, tp, risk_pct, timeout_minutes, layers=[PositionLayer(1, price, risk_pct)])
