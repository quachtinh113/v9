from __future__ import annotations
from typing import Dict, Any
from src.core.models import SignalDecision, RegimeState
from src.core.regime_engine import detect_regime
from src.ml.xgb_filter import apply_ml_gatekeeper

def evaluate_signal(features: Dict[str, Any], config: Dict[str, Any] | None = None) -> SignalDecision:
    cfg = config or {}
    rs = detect_regime(features, trend_adx_min=20) # Lower for training signals
    bias = str(features.get("bias", "flat"))
    score = 0.0
    if rs.regime in ("trend", "sideway", "transition"): score += 50 # Base score boost for training
    if bias != "flat": score += 30
    
    threshold = cfg.get("score_threshold", 70)
    direction = bias if score >= threshold else "flat"
    
    dec = SignalDecision(cfg.get("symbol", "UKN"), direction, score, f"R={rs.regime},S={score}", rs.regime)
    return dec
