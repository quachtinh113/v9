from __future__ import annotations
from typing import Dict, Any
from src.core.models import RegimeState

def detect_regime(features: Dict[str, Any], trend_adx_min: float = 25, sideway_adx_max: float = 18, trend_h4_adx_min: float = 20, bb_squeeze_threshold: float = 0.005, allowed_sessions: tuple = ("london", "new_york")) -> RegimeState:
    adx_h1 = float(features.get("adx14_h1", 0.0))
    adx_h4 = float(features.get("adx14_h4", 0.0))
    atr_ratio = float(features.get("atr_ratio", 1.0))
    bb_width = float(features.get("bb_width_m15", 0.0))
    session_flag = str(features.get("session_flag", "off"))
    if atr_ratio >= 2.5: return RegimeState("shock", min(atr_ratio/4.0, 1.0), adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
    if session_flag not in allowed_sessions: return RegimeState("off_session", 0.9, adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
    if adx_h1 >= trend_adx_min:
        if adx_h4 >= trend_h4_adx_min: return RegimeState("trend", min((adx_h1+adx_h4)/100.0, 1.0), adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
        return RegimeState("transition", adx_h1/60.0, adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
    if adx_h1 <= sideway_adx_max: return RegimeState("sideway", min(0.6 + (1 - adx_h1/30.0)*0.25, 1.0), adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
    return RegimeState("transition", 0.3, adx_h1, adx_h4, atr_ratio, bb_width, session_flag)
