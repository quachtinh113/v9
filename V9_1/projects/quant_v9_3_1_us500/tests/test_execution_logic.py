import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure the src folder of the gbpusd project is in the path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

from src.data.mtf_builder import build_feature_table
from src.core.signal_engine import evaluate_signal
from src.core.risk_engine import RiskGateway
from src.execution.order_router import OrderRouter
from src.execution.mt5_adapter import MT5Adapter
from src.core.models import SignalDecision, PositionPlan, RiskDecision
from unittest.mock import patch

def create_synthetic_data(trend: str):
    """
    Generate synthetic data for testing bias generation.
    - long: close > ema50 AND RSI >= 50 AND ADX >= 20
    - short: close < ema50 AND RSI <= 50 AND ADX >= 20
    - neutral: otherwise
    """
    dates = pd.date_range("2025-01-01", periods=1000, freq="1Min")
    df = pd.DataFrame({"timestamp": dates})
    df["open"] = 1.0
    df["high"] = 1.0
    df["low"] = 1.0
    df["volume"] = 100.0
    
    if trend == "long":
        # Price goes up, making close > EMA50, RSI > 50
        df["close"] = np.linspace(1.0, 2.0, 1000)
    elif trend == "short":
        # Price goes down, making close < EMA50, RSI < 50
        df["close"] = np.linspace(2.0, 1.0, 1000)
    else: # neutral
        # Price oscillates, close around EMA50, RSI around 50
        df["close"] = np.sin(np.linspace(0, 10*np.pi, 1000)) + 1.0

    return df

def test_mtf_builder_produces_correct_bias():
    with patch('src.data.mtf_builder.compute_rsi') as mock_rsi, \
         patch('src.data.mtf_builder.compute_adx') as mock_adx:
        
        # Long
        df_long = create_synthetic_data("long")
        mock_rsi.side_effect = lambda series, *args, **kwargs: pd.Series([60.0] * len(series), index=series.index)
        mock_adx.side_effect = lambda df, *args, **kwargs: pd.Series([25.0] * len(df), index=df.index)
        ft_long = build_feature_table(df_long)
        assert ft_long.iloc[-1]["bias"] == "long"
        
        # Short
        df_short = create_synthetic_data("short")
        mock_rsi.side_effect = lambda series, *args, **kwargs: pd.Series([40.0] * len(series), index=series.index)
        mock_adx.side_effect = lambda df, *args, **kwargs: pd.Series([25.0] * len(df), index=df.index)
        ft_short = build_feature_table(df_short)
        assert ft_short.iloc[-1]["bias"] == "short"

        # Neutral (oscillates and evaluates to binary bias)
        df_neutral = create_synthetic_data("neutral")
        mock_rsi.side_effect = lambda series, *args, **kwargs: pd.Series([50.0] * len(series), index=series.index)
        mock_adx.side_effect = lambda df, *args, **kwargs: pd.Series([10.0] * len(df), index=df.index)
        ft_neutral = build_feature_table(df_neutral)
        assert ft_neutral.iloc[-1]["bias"] in ("long", "short")

def test_signal_engine_directions():
    # Long Trend Features
    features_long = {
        "rsi14_m15": 55.0,
        "bb_width_m15": 0.02,
        "macd_hist_m15": 0.001,
        "adx14_h1": 30.0,
        "adx14_h4": 28.0,
        "atr14_m1": 0.002,
        "atr14_h1": 0.005,
        "atr14_h4": 0.010,
        "atr_ratio": 1.0,
        "bias": "long",
        "bias_h1": "long",
        "bias_h4": "long",
        "session_flag": "london"
    }
    dec_long = evaluate_signal(features_long, {"score_threshold": 70})
    assert dec_long.direction == "long"

    # Short Trend Features
    features_short = {
        "rsi14_m15": 45.0,
        "bb_width_m15": 0.02,
        "macd_hist_m15": -0.001,
        "adx14_h1": 30.0,
        "adx14_h4": 28.0,
        "atr14_m1": 0.002,
        "atr14_h1": 0.005,
        "atr14_h4": 0.010,
        "atr_ratio": 1.0,
        "bias": "short",
        "bias_h1": "short",
        "bias_h4": "short",
        "session_flag": "london"
    }
    dec_short = evaluate_signal(features_short, {"score_threshold": 70})
    assert dec_short.direction == "short"
    
    # Neutral/Flat Bias
    features_neutral = {
        "rsi14_m15": 50.0,
        "bb_width_m15": 0.02,
        "macd_hist_m15": 0.0,
        "adx14_h1": 15.0,
        "adx14_h4": 15.0,
        "atr14_m1": 0.002,
        "atr14_h1": 0.005,
        "atr14_h4": 0.010,
        "atr_ratio": 1.0,
        "bias": "neutral",
        "bias_h1": "neutral",
        "bias_h4": "neutral",
        "session_flag": "london"
    }
    dec_neutral = evaluate_signal(features_neutral, {"score_threshold": 70})
    assert dec_neutral.direction == "flat"

def test_order_router_mapping():
    router = OrderRouter(MT5Adapter(), {"mode": "paper", "volume": 0.02})
    plan = PositionPlan(1.0, 0.9, 1.1, 0.1, 120)
    risk_allow = RiskDecision("ALLOW", [])
    
    # long mapping
    res = router.route_order(plan, SignalDecision("GBPUSD", "long", 80, ""), risk_allow)
    assert res.get("direction") == "long"
    assert res.get("status") == "paper_success"
    assert res.get("volume") == 0.02
    
    # short mapping
    res = router.route_order(plan, SignalDecision("GBPUSD", "short", 80, ""), risk_allow)
    assert res.get("direction") == "short"
    assert res.get("status") == "paper_success"
    
    # Blocked by risk should return blocked status
    risk_block = RiskDecision("SOFT_BLOCK", ["daily_loss_limit"])
    res = router.route_order(plan, SignalDecision("GBPUSD", "long", 80, ""), risk_block)
    assert res.get("status") == "blocked_soft_block"

def test_risk_engine_vetoes():
    gateway = RiskGateway({
        "hard_drawdown_pct": 8.0,
        "daily_loss_limit_pct": 2.0,
        "loss_streak_pause": 3
    })
    
    # Allow Normal
    account_ok = {"daily_dd_pct": 0.5, "weekly_dd_pct": 1.0, "loss_streak": 0, "open_positions": 0, "daily_trades_count": 1}
    market_ok = {"spread_bps": 2.0, "slippage_bps": 1.0, "atr_ratio": 1.0, "session_flag": "london"}
    rd = gateway.full_gate(account_ok, market_ok)
    assert rd.action == "ALLOW"
    
    # Drawdown limit daily_loss_limit soft block
    account_dd_limit = {"daily_dd_pct": 2.5, "weekly_dd_pct": 1.0, "loss_streak": 0, "open_positions": 0, "daily_trades_count": 1}
    rd = gateway.full_gate(account_dd_limit, market_ok)
    assert rd.action == "SOFT_BLOCK"
    assert "daily_loss_limit" in rd.reasons
    
    # Hard Drawdown hard kill
    account_hard_dd = {"daily_dd_pct": 9.0, "weekly_dd_pct": 1.0, "loss_streak": 0, "open_positions": 0, "daily_trades_count": 1}
    rd = gateway.full_gate(account_hard_dd, market_ok)
    assert rd.action == "HARD_KILL"
    assert "daily_hard_drawdown" in rd.reasons
    
    # Missing market fields should hard kill
    market_missing = {"session_flag": "london"}
    rd = gateway.full_gate(account_ok, market_missing)
    assert rd.action == "HARD_KILL"
    assert any("missing_market_field_" in r for r in rd.reasons)
