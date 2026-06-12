from __future__ import annotations
import logging
import os
from typing import Any
try:
    import xgboost as xgb
    import numpy as np
    import pandas as pd
    XGB_AVAILABLE = True
except:
    XGB_AVAILABLE = False

FEATURE_NAMES = ["rsi14_m15", "adx14_h1", "atr_ratio", "bb_width_m15", "macd_hist_m15", "score", "regime_confidence", "bias_aligned", "session_london", "session_ny", "hour_sin", "hour_cos"]

class XGBTradeFilter:
    def __init__(self, model_path: str, enabled: bool = False):
        self.enabled = enabled
        self.model = None
        self.load_failed = False
        self.load_error_reason = ""
        
        if enabled:
            if not XGB_AVAILABLE:
                self.load_failed = True
                self.load_error_reason = "XGBoost library not available"
                return
            if not os.path.exists(model_path):
                self.load_failed = True
                self.load_error_reason = f"Model file not found at {model_path}"
                return
            try:
                self.model = xgb.Booster()
                self.model.load_model(model_path)
            except Exception as e:
                self.load_failed = True
                self.load_error_reason = f"Failed to load model booster: {str(e)}"

    def predict_quality(self, features: dict, score: float = 0.0) -> float:
        if not self.enabled:
            return 1.0
        if self.load_failed:
            raise RuntimeError(f"ML model failed to load: {self.load_error_reason}")
        if not self.model:
            raise RuntimeError("ML model is enabled but booster is None")
            
        try:
            rc = float(features.get("regime_confidence", 0.85))
            # Map session flags to session_london/session_ny
            session = str(features.get("session_flag", "off"))
            session_london = 1.0 if session == "london" else 0.0
            session_ny = 1.0 if session == "new_york" else 0.0
            
            # Check bias aligned
            bias = str(features.get("bias", "flat"))
            bias_aligned = 1.0 if bias != "flat" else 0.0
            
            mapped_features = {
                "session_london": session_london,
                "session_ny": session_ny,
                "bias_aligned": bias_aligned,
                "score": score,
                "regime_confidence": rc
            }
            
            v = []
            for f in FEATURE_NAMES:
                if f in features:
                    val = features[f]
                elif f in mapped_features:
                    val = mapped_features[f]
                else:
                    val = 0.0
                v.append(float(val))
                
            d = xgb.DMatrix(np.array([v]), feature_names=FEATURE_NAMES)
            return float(self.model.predict(d)[0])
        except Exception as e:
            raise RuntimeError(f"ML prediction failed: {str(e)}")

_FILTER_CACHE = {}

def apply_ml_gatekeeper(dec: Any, features: dict, ml_cfg: dict) -> Any:
    # Set default values for ML audit fields in dec
    dec.ml_score = 1.0
    dec.ml_decision = "OFF"
    dec.ml_reason = "ML is disabled"
    
    if not ml_cfg.get('enabled', False):
        return dec
        
    model_path = ml_cfg.get('model_path', 'models/xgb_trade_filter.json')
    
    try:
        if model_path not in _FILTER_CACHE:
            _FILTER_CACHE[model_path] = XGBTradeFilter(model_path, True)
        f = _FILTER_CACHE[model_path]
        
        ms = f.predict_quality(features, dec.score)
        dec.ml_score = ms
        
        # ML must never create a trade. It only blocks or reduces a rule-based valid signal.
        if dec.direction == "flat":
            dec.ml_decision = "PASS"
            dec.ml_reason = "Signal is already flat"
            return dec
            
        block_thresh = ml_cfg.get('block_threshold', 0.55)
        reduce_thresh = ml_cfg.get('reduce_threshold', 0.65)
        
        if ms < block_thresh:
            # Temporarily set ML gate to OBSERVE_ONLY, not BLOCK
            # dec.direction = "flat"
            dec.ml_decision = "BLOCK"
            dec.ml_reason = f"ML score {ms:.4f} below block threshold {block_thresh:.2f}"
        elif ms < reduce_thresh:
            dec.size_multiplier = ml_cfg.get('reduce_size_factor', 0.5)
            dec.ml_decision = "REDUCE"
            dec.ml_reason = f"ML score {ms:.4f} below reduce threshold {reduce_thresh:.2f}"
        else:
            dec.ml_decision = "PASS"
            dec.ml_reason = f"ML score {ms:.4f} is safe"
            
    except Exception as e:
        # If ML enabled and model missing/load failed/predict failed/feature mismatch, return PASS instead of BLOCK
        dec.ml_decision = "PASS"
        dec.ml_reason = f"ML Error (treated as PASS): {str(e)}"
        # Do not flatten the signal; keep original direction
        # Ensure entry_allowed remains as previously determined (if any)
        return dec
        
    return dec
