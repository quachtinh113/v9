from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from src.core.models import SignalDecision
from src.core.regime_engine import detect_regime
from src.ml.xgb_filter import apply_ml_gatekeeper

def evaluate_signal(features: Dict[str, Any], config: Dict[str, Any] | None = None) -> SignalDecision:
    cfg = config or {}
    symbol = cfg.get("symbol", "UKN")
    
    # 1. Detect market regime
    trend_adx_min = float(cfg.get("entry", {}).get("trend_adx_min", 25))
    sideway_adx_max = float(cfg.get("entry", {}).get("sideway_adx_max", 18))
    rs = detect_regime(features, trend_adx_min=trend_adx_min, sideway_adx_max=sideway_adx_max)
    
    regime = rs.regime
    blocked_reasons = []
    
    # Gate checks initialization
    regime_pass = False
    session_pass = False
    rsi_pass = False
    adx_pass = False
    atr_pass = False
    direction_alignment_pass = False
    
    # --- 1. Regime PASS check ---
    if regime == "shock":
        blocked_reasons.append("shock_regime_no_trade")
    elif regime == "off_session":
        blocked_reasons.append("off_session_regime_no_trade")
    elif regime == "transition":
        transition_allowed = cfg.get("risk", {}).get("transition_trade_enabled", False)
        if not transition_allowed:
            blocked_reasons.append("transition_regime_disabled")
        else:
            regime_pass = True
    elif regime in ("trend", "sideway"):
        regime_pass = True
        
    # --- 2. Session PASS check ---
    session = str(features.get("session_flag", "off"))
    allowed_sessions = ("london", "new_york", "crypto_24_7")
    if session in allowed_sessions:
        session_pass = True
    else:
        blocked_reasons.append(f"invalid_session_{session}")
        
    # --- 3. MTF RSI PASS check ---
    rsi = features.get("rsi14_m15")
    if rsi is None or pd.isna(rsi):
        blocked_reasons.append("missing_rsi14_m15")
    else:
        rsi = float(rsi)
        if regime == "trend":
            # Trend following: BUY bias must match. Long bias confirmation: [40, 75]. Short bias confirmation: [25, 60].
            bias = str(features.get("bias", "flat"))
            if bias == "long":
                if 40 <= rsi <= 75:
                    rsi_pass = True
                else:
                    blocked_reasons.append(f"rsi_out_of_trend_bounds_long_{rsi:.1f}")
            elif bias == "short":
                if 25 <= rsi <= 60:
                    rsi_pass = True
                else:
                    blocked_reasons.append(f"rsi_out_of_trend_bounds_short_{rsi:.1f}")
            else:
                blocked_reasons.append("flat_bias_in_trend")
        elif regime == "sideway":
            # Mean reversion: BUY on oversold, SELL on overbought
            if rsi <= 35:
                rsi_pass = True
            elif rsi >= 65:
                rsi_pass = True
            else:
                blocked_reasons.append(f"rsi_not_in_mean_reversion_bounds_{rsi:.1f}")
        else:
            # Transition safe range check
            if 30 <= rsi <= 70:
                rsi_pass = True
            else:
                blocked_reasons.append(f"rsi_unsafe_for_transition_{rsi:.1f}")
                
    # --- 4. ADX PASS check ---
    adx_h1 = features.get("adx14_h1")
    if adx_h1 is None or pd.isna(adx_h1):
        blocked_reasons.append("missing_adx14_h1")
    else:
        adx_h1 = float(adx_h1)
        if regime == "trend":
            if adx_h1 >= trend_adx_min:
                adx_pass = True
            else:
                blocked_reasons.append(f"trend_adx_too_low_{adx_h1:.1f}")
        elif regime == "sideway":
            if adx_h1 <= sideway_adx_max:
                adx_pass = True
            else:
                blocked_reasons.append(f"sideway_adx_too_high_{adx_h1:.1f}")
        else:
            adx_pass = True
            
    # --- 5. ATR PASS check ---
    atr_ratio = features.get("atr_ratio")
    if atr_ratio is None or pd.isna(atr_ratio):
        blocked_reasons.append("missing_atr_ratio")
    else:
        atr_ratio = float(atr_ratio)
        atr_ratio_limit = float(cfg.get("risk", {}).get("atr_ratio_limit", 2.0))
        if atr_ratio <= atr_ratio_limit:
            atr_pass = True
        else:
            blocked_reasons.append(f"atr_ratio_exceeds_limit_{atr_ratio:.2f}")
            
    # --- 6. Direction Alignment PASS check ---
    bias = str(features.get("bias", "flat"))
    bias_h1 = str(features.get("bias_h1", "flat"))
    bias_h4 = str(features.get("bias_h4", "flat"))
    
    # Missing feature validation check
    for f in ["rsi14_m15", "bb_width_m15", "macd_hist_m15", "adx14_h1", "adx14_h4", "atr14_m1", "atr14_h1", "atr14_h4", "bias", "bias_h1", "bias_h4", "session_flag"]:
        if f not in features or features[f] is None or pd.isna(features[f]):
            blocked_reasons.append(f"missing_required_feature_{f}")
            
    # Determine rule-based signal direction
    direction = "flat"
    pullback_detected = False
    
    if regime == "trend":
        # Check Trend Pullback Entry conditions
        is_pullback = False
        adx_val = features.get("adx14_h1")
        if adx_val is not None and not pd.isna(adx_val) and float(adx_val) >= 25:
            if bias_h1 == bias_h4 and bias_h1 in ("long", "short"):
                if (bias_h1 == "long" and bias == "short") or (bias_h1 == "short" and bias == "long"):
                    is_pullback = True
                    
        if is_pullback:
            direction = bias_h1
            direction_alignment_pass = True
            pullback_detected = True
        elif bias == bias_h1 == bias_h4 and bias in ("long", "short"):
            direction = bias
            direction_alignment_pass = True
        else:
            blocked_reasons.append(f"trend_biases_mismatch_m15={bias}_h1={bias_h1}_h4={bias_h4}")
    elif regime == "sideway":
        # Mean reversion: trade opposite to direction or buy/sell based on RSI
        if rsi is not None:
            if rsi <= 35:
                direction = "long"
                direction_alignment_pass = True
            elif rsi >= 65:
                direction = "short"
                direction_alignment_pass = True
            else:
                blocked_reasons.append("rsi_neutral_in_sideway")
        else:
            blocked_reasons.append("missing_rsi_in_sideway")
    elif regime == "transition":
        # Transition: trade emerging trend when enabled (align M15 and H1 bias)
        transition_allowed = cfg.get("risk", {}).get("transition_trade_enabled", False)
        if transition_allowed:
            if bias == bias_h1 and bias in ("long", "short"):
                direction = bias
                direction_alignment_pass = True
            else:
                blocked_reasons.append(f"transition_biases_mismatch_m15={bias}_h1={bias_h1}")
        else:
            blocked_reasons.append(f"no_trade_in_regime_{regime}")
    else:
        blocked_reasons.append(f"no_trade_in_regime_{regime}")
        
    # Enforce scoring logic
    score = 0.0
    if regime_pass: score += 20
    if session_pass: score += 10
    if rsi_pass: score += 10
    if adx_pass: score += 10
    if atr_pass: score += 10
    if direction_alignment_pass: score += 20
    
    score_before_pullback = score
    score_after_pullback = score
    
    if pullback_detected:
        score += 10
        score = min(100.0, score)
        score_after_pullback = score
        
    threshold = cfg.get("score_threshold", 70)
    
    # Hard entry gate: if any check fails, direction is flat
    gate_passed = (regime_pass and session_pass and rsi_pass and adx_pass and atr_pass and direction_alignment_pass and score >= threshold and len(blocked_reasons) == 0)
    
    if not gate_passed:
        direction = "flat"
        gate_status = "REJECTED"
        if score < threshold:
            blocked_reasons.append(f"score_below_threshold_{score:.0f}_vs_{threshold}")
    else:
        gate_status = "PASSED"
        
    entry_allowed = gate_passed
    
    # Add audit reasons to entry_reasons post-gate passed so they don't block
    entry_reasons = []
    if pullback_detected and gate_passed:
        entry_reasons.append("trend_pullback_entry_enabled")
        entry_reasons.append("pullback_m15_against_h1_h4")
        entry_reasons.append("final_direction_from_h1_h4")
        
    dec = SignalDecision(
        symbol=symbol,
        direction=direction,
        score=score,
        reason=f"Regime={regime}, Gate={gate_status}",
        regime=regime,
        entry_allowed=entry_allowed,
        gate_status=gate_status,
        blocked_reasons=blocked_reasons,
        entry_reasons=entry_reasons,
        rsi_mtf_pass=rsi_pass,
        adx_pass=adx_pass,
        atr_pass=atr_pass,
        session_pass=session_pass,
        direction_alignment_pass=direction_alignment_pass,
        position_plan_valid=False
    )
    dec.pullback_detected = pullback_detected
    dec.score_before_pullback = score_before_pullback
    dec.score_after_pullback = score_after_pullback
    
    # Store raw strategy direction before ML Gatekeeper overwrites it
    dec.raw_signal = dec.direction
    
    # Enforce ML Gatekeeper
    ml_cfg = dict(cfg.get("ml", {}))
    tg_cfg = cfg.get("telegram", {})
    for key in ["reduce_threshold", "reduce_size_factor"]:
        if key in tg_cfg and key not in ml_cfg:
            ml_cfg[key] = tg_cfg[key]
            
    dec = apply_ml_gatekeeper(dec, features, ml_cfg)
    
    # Update entry_allowed based on ML gatekeeper decision
    if dec.ml_decision == "BLOCK":
        # Temporarily set ML gate to OBSERVE_ONLY, not BLOCK
        # dec.direction = "flat"
        # dec.entry_allowed = False
        dec.blocked_reasons.append("ML_gatekeeper_block (OBSERVE_ONLY)")
        
    return dec
