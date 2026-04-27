from __future__ import annotations
import logging, os
try:
    import xgboost as xgb
    import numpy as np
    XGB_AVAILABLE = True
except: XGB_AVAILABLE = False

FEATURE_NAMES = ["rsi14_m15", "adx14_h1", "atr_ratio", "bb_width_m15", "macd_hist_m15", "score", "regime_confidence", "bias_aligned", "session_london", "session_ny", "hour_sin", "hour_cos"]

class XGBTradeFilter:
    def __init__(self, model_path: str, enabled: bool = False):
        self.enabled, self.model = enabled, None
        if enabled and XGB_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = xgb.Booster()
                self.model.load_model(model_path)
            except: pass

    def predict_quality(self, features: dict, score: float = 0.0, rc: float = 0.5) -> float:
        if not self.enabled or not self.model or not XGB_AVAILABLE: return 1.0
        try:
            v = [float(features.get(f, 0)) for f in FEATURE_NAMES] # simplified for restore
            d = xgb.DMatrix(np.array([v]), feature_names=FEATURE_NAMES)
            return float(self.model.predict(d)[0])
        except: return 1.0

def apply_ml_gatekeeper(dec: Any, features: dict, ml_cfg: dict) -> Any:
    if not ml_cfg.get('enabled', False): return dec
    f = XGBTradeFilter(ml_cfg.get('model_path', 'models/xgb_filter.json'), True)
    ms = f.predict_quality(features, dec.score)
    dec.ml_score, dec.ml_decision = ms, "PASS"
    if ms < ml_cfg.get('block_threshold', 0.55):
        dec.direction, dec.ml_decision = "flat", "BLOCK"
    elif ms < ml_cfg.get('reduce_threshold', 0.65):
        dec.size_multiplier, dec.ml_decision = ml_cfg.get('reduce_size_factor', 0.5), "REDUCE"
    return dec
