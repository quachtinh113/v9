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
    dates = pd.date_range("2025-01-01", periods=100, freq="1Min")
    df = pd.DataFrame({"timestamp": dates})
    df["open"] = 1.0
    df["high"] = 1.0
    df["low"] = 1.0
    
    if trend == "long":
        # Price goes up, making close > EMA50, RSI > 50
        df["close"] = np.linspace(1.0, 2.0, 100)
    elif trend == "short":
        # Price goes down, making close < EMA50, RSI < 50
        df["close"] = np.linspace(2.0, 1.0, 100)
    else: # neutral
        # Price oscillates, close around EMA50, RSI around 50
        df["close"] = np.sin(np.linspace(0, 10*np.pi, 100)) + 1.0

    return df

def test_mtf_builder_produces_correct_bias():
    with patch('src.data.mtf_builder.compute_rsi') as mock_rsi, \
         patch('src.data.mtf_builder.compute_adx') as mock_adx:
        
        # Long
        df_long = create_synthetic_data("long")
        mock_rsi.return_value = pd.Series([60] * len(df_long))
        mock_adx.return_value = pd.Series([25] * len(df_long))
        ft_long = build_feature_table(df_long)
        assert ft_long.iloc[-1]["bias"] == "long"
        
        # Short
        df_short = create_synthetic_data("short")
        mock_rsi.return_value = pd.Series([40] * len(df_short))
        mock_adx.return_value = pd.Series([25] * len(df_short))
        ft_short = build_feature_table(df_short)
        assert ft_short.iloc[-1]["bias"] == "short"

        # Neutral (fails RSI/ADX condition)
        df_neutral = create_synthetic_data("neutral")
        mock_rsi.return_value = pd.Series([50] * len(df_neutral))
        mock_adx.return_value = pd.Series([10] * len(df_neutral))
        ft_neutral = build_feature_table(df_neutral)
        assert ft_neutral.iloc[-1]["bias"] == "neutral"

def test_signal_engine_directions():
    # Test BUY
    features = {"bias": "long"}
    dec = evaluate_signal(features, {"score_threshold": 70})
    # evaluate_signal adds 30 for bias != NO_TRADE and 50 if regime is trend/sideway (total 80)
    # mock detect_regime output is "trend" -> 50, +30 -> 80
    assert dec.direction == "BUY"

    # Test SELL
    features = {"bias": "short"}
    dec = evaluate_signal(features, {"score_threshold": 70})
    assert dec.direction == "SELL"
    
    # Test NO_TRADE
    features = {"bias": "neutral"}
    dec = evaluate_signal(features, {"score_threshold": 70})
    assert dec.direction == "NO_TRADE"

def test_order_router_mapping():
    router = OrderRouter(MT5Adapter(), {})
    plan = PositionPlan(1.0, 0.9, 1.1, 0.1, 120)
    risk_allow = RiskDecision("ALLOW", [])
    
    # BUY mapping
    res = router.route_order(plan, SignalDecision("GBPUSD", "BUY", 80, ""), risk_allow)
    assert res.get("order_type") == "ORDER_TYPE_BUY"
    
    # SELL mapping
    res = router.route_order(plan, SignalDecision("GBPUSD", "SELL", 80, ""), risk_allow)
    assert res.get("order_type") == "ORDER_TYPE_SELL"
    
    # NO_TRADE should not send an order
    res = router.route_order(plan, SignalDecision("GBPUSD", "NO_TRADE", 80, ""), risk_allow)
    assert res.get("status") == "no_order"

def test_risk_engine_vetoes():
    gateway = RiskGateway({})
    account = {"daily_dd_pct": 0, "loss_streak": 0}
    
    # Veto BUY in bear trend
    rd = gateway.full_gate(account, {"session_flag": "london", "bias_h4": "short"}, "BUY")
    assert rd.action == "BLOCK"
    assert "veto_buy_in_bear_trend" in rd.reasons
    
    # Veto SELL in bull trend
    rd = gateway.full_gate(account, {"session_flag": "london", "bias_h4": "long"}, "SELL")
    assert rd.action == "BLOCK"
    assert "veto_sell_in_bull_trend" in rd.reasons
    
    # Allow matched trends
    rd = gateway.full_gate(account, {"session_flag": "london", "bias_h4": "long"}, "BUY")
    assert rd.action == "ALLOW"
    
    # Block NO_TRADE
    rd = gateway.full_gate(account, {"session_flag": "london", "bias_h4": "long"}, "NO_TRADE")
    assert rd.action == "BLOCK"
    assert "veto_neutral_signal" in rd.reasons
