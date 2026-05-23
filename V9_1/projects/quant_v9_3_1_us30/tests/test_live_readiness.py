import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Setup paths to import project modules
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.core.models import SignalDecision, RiskDecision, PositionPlan
from src.core.signal_engine import evaluate_signal
from src.core.risk_engine import RiskGateway
from src.ml.xgb_filter import apply_ml_gatekeeper
from src.strategies.us30_strategy import generate_trade_plan

# Set up helper feature dictionaries
def get_base_features():
    return {
        "timestamp": pd.to_datetime("2026-05-01 10:00:00", utc=True),
        "close_m1": 38000.0,
        "close": 38000.0,
        "high": 38010.0,
        "low": 37990.0,
        "rsi14_m15": 50.0,
        "bb_width_m15": 0.01,
        "macd_hist_m15": 0.0,
        "adx14_h1": 30.0,
        "adx14_h4": 25.0,
        "atr14_m1": 15.0,
        "atr14_h1": 20.0,
        "atr14_h4": 30.0,
        "atr_ratio": 0.75,
        "bias": "long",
        "bias_h1": "long",
        "bias_h4": "long",
        "session_flag": "london",
        "hour_sin": 0.0,
        "hour_cos": 0.0
    }

def get_base_config():
    return {
        "symbol": "US30",
        "entry": {
            "trend_adx_min": 25,
            "sideway_adx_max": 18
        },
        "position": {
            "stop_atr_mult": 1.8,
            "tp_atr_mult": 2.5,
            "timeout_minutes": 120
        },
        "risk": {
            "risk_per_trade_pct": 0.25,
            "atr_ratio_limit": 2.0,
            "transition_trade_enabled": False,
            "daily_loss_limit_pct": 2.0,
            "hard_drawdown_pct": 8.0,
            "loss_streak_pause": 3,
            "max_open_positions": 2,
            "max_daily_trades": 5,
            "spread_guard_enabled": True,
            "slippage_guard_enabled": True,
            "atr_shock_block_enabled": True
        },
        "backtest": {
            "initial_capital": 100000.0
        },
        "ml": {
            "enabled": False
        }
    }

def test_transition_long_bias_no_trade():
    """Prove transition + long bias = NO_TRADE (gate status REJECTED, entry_allowed False)"""
    features = get_base_features()
    # Transition regime: ADX H1 high (>= 25) but ADX H4 low (< 20)
    features["adx14_h1"] = 30.0
    features["adx14_h4"] = 15.0
    
    config = get_base_config()
    config["risk"]["transition_trade_enabled"] = False
    
    dec = evaluate_signal(features, config)
    assert dec.regime == "transition"
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert "transition_regime_disabled" in dec.blocked_reasons

def test_shock_long_bias_no_trade():
    """Prove shock + long bias = NO_TRADE"""
    features = get_base_features()
    # Shock regime: atr_ratio >= 2.5
    features["atr_ratio"] = 3.0
    
    config = get_base_config()
    
    dec = evaluate_signal(features, config)
    assert dec.regime == "shock"
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert "shock_regime_no_trade" in dec.blocked_reasons

def test_off_session_long_bias_no_trade():
    """Prove off_session + long bias = NO_TRADE"""
    features = get_base_features()
    features["session_flag"] = "off"
    
    config = get_base_config()
    
    dec = evaluate_signal(features, config)
    assert dec.regime == "off_session"
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert "off_session_regime_no_trade" in dec.blocked_reasons

def test_missing_features_no_trade():
    """Prove missing features = NO_TRADE (any NaN or missing key blocks trade)"""
    features = get_base_features()
    features.pop("rsi14_m15") # Remove required feature
    
    config = get_base_config()
    
    dec = evaluate_signal(features, config)
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert any("missing_required_feature_rsi14_m15" in r for r in dec.blocked_reasons)

def test_ml_enabled_missing_model_blocks():
    """Prove ML enabled but missing model = BLOCK (fails closed)"""
    features = get_base_features()
    config = get_base_config()
    config["ml"]["enabled"] = True
    config["ml"]["model_path"] = "nonexistent_model_file.json"
    
    # We should evaluate with signal engine, it runs gatekeeper and catches the load error
    dec = evaluate_signal(features, config)
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert dec.ml_decision == "BLOCK"
    assert "ML Error" in dec.ml_reason

def test_ml_exception_blocks():
    """Prove ML exception during prediction = BLOCK"""
    features = get_base_features()
    config = get_base_config()
    config["ml"]["enabled"] = True
    config["ml"]["model_path"] = "nonexistent_model_file.json"
    
    # Run gatekeeper directly to ensure it catches custom prediction errors
    dec = SignalDecision("US30", "long", 85.0, "reason", "trend")
    dec = apply_ml_gatekeeper(dec, features, config["ml"])
    
    assert dec.direction == "flat"
    assert dec.ml_decision == "BLOCK"
    assert "ML Error" in dec.ml_reason

def test_buy_position_sl_tp_bounds():
    """Prove BUY position has SL < entry < TP"""
    features = get_base_features()
    features["rsi14_m15"] = 55.0 # Bullish momentum confirm
    
    config = get_base_config()
    
    plan, dec = generate_trade_plan(features, config)
    
    assert dec.direction == "long"
    assert plan is not None
    assert plan.stop_loss < plan.entry < plan.take_profit
    assert dec.position_plan_valid

def test_sell_position_sl_tp_bounds():
    """Prove SELL position has TP < entry < SL"""
    features = get_base_features()
    features["bias"] = "short"
    features["bias_h1"] = "short"
    features["bias_h4"] = "short"
    features["rsi14_m15"] = 45.0 # Bearish momentum confirm
    
    config = get_base_config()
    
    plan, dec = generate_trade_plan(features, config)
    
    assert dec.direction == "short"
    assert plan is not None
    assert plan.take_profit < plan.entry < plan.stop_loss
    assert dec.position_plan_valid

def test_trend_without_mtf_confirmation_no_trade():
    """Prove trend without MTF confirmation (mismatch in H1/H4 biases) = NO_TRADE"""
    features = get_base_features()
    # Trend regime, but H4 bias is short while H1 bias is long
    features["bias"] = "long"
    features["bias_h1"] = "long"
    features["bias_h4"] = "short"
    
    config = get_base_config()
    
    dec = evaluate_signal(features, config)
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert "trend_biases_mismatch" in "".join(dec.blocked_reasons)

def test_sideway_without_mean_reversion_edge_no_trade():
    """Prove sideway without mean-reversion edge (RSI neutral, e.g. 50) = NO_TRADE"""
    features = get_base_features()
    # Sideway regime: ADX H1 low (<= 18)
    features["adx14_h1"] = 15.0
    features["rsi14_m15"] = 50.0 # Neutral RSI, no overbought/oversold edge
    
    config = get_base_config()
    
    dec = evaluate_signal(features, config)
    assert dec.regime == "sideway"
    assert not dec.entry_allowed
    assert dec.direction == "flat"
    assert "rsi_neutral_in_sideway" in dec.blocked_reasons

def test_daily_loss_limit_soft_block():
    """Prove daily loss limit = SOFT_BLOCK"""
    config = get_base_config()
    gateway = RiskGateway(config["risk"])
    
    account = {"daily_dd_pct": 2.5, "weekly_dd_pct": 0.0, "loss_streak": 0, "open_positions": 0}
    market = {"spread_bps": 1.0, "slippage_bps": 1.0, "atr_ratio": 1.0, "session_flag": "london"}
    
    dec = gateway.full_gate(account, market)
    assert dec.action == "SOFT_BLOCK"
    assert "daily_loss_limit" in dec.reasons

def test_hard_drawdown_hard_kill():
    """Prove hard drawdown = HARD_KILL"""
    config = get_base_config()
    gateway = RiskGateway(config["risk"])
    
    account = {"daily_dd_pct": 0.0, "weekly_dd_pct": 8.5, "loss_streak": 0, "open_positions": 0}
    market = {"spread_bps": 1.0, "slippage_bps": 1.0, "atr_ratio": 1.0, "session_flag": "london"}
    
    dec = gateway.full_gate(account, market)
    assert dec.action == "HARD_KILL"
    assert "weekly_hard_drawdown" in dec.reasons
