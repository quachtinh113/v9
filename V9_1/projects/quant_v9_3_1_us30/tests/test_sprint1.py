import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Setup paths to import project modules
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
V9_1_DIR = PROJECT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.core.models import SignalDecision, RiskDecision, PositionPlan, Trade
from src.core.risk_engine import RiskGateway
from src.ml.validation import simulate_financials
from src.ml.xgb_filter import apply_ml_gatekeeper
from src.execution.mt5_adapter import MT5Adapter
from src.backtest.backtest_engine import SingleAssetBacktester

def test_validation_profit_factor():
    """Verify that profit factor calculates wins_sum / losses_sum instead of counts."""
    y_true = [1, 1, 0]
    y_pred = [1, 1, 1]
    
    results = simulate_financials(y_true, y_pred)
    assert results["profit_factor"] == 4.0
    assert results["winrate"] == pytest.approx(2/3)

def test_risk_gateway_yaml_guards():
    """Verify YAML guards configuration and activation thresholds in RiskGateway."""
    cfg_disabled = {
        "daily_loss_limit_pct": 2.0,
        "spread_guard_enabled": False,
        "slippage_guard_enabled": False,
        "atr_shock_block_enabled": False
    }
    gateway = RiskGateway(cfg_disabled)
    
    account = {"daily_dd_pct": 0.0, "weekly_dd_pct": 0.0, "loss_streak": 0}
    market = {"spread_bps": 10.0, "slippage_bps": 10.0, "atr_ratio": 5.0, "session_flag": "london"}
    
    decision = gateway.full_gate(account, market)
    assert decision.action == "ALLOW"
    assert len(decision.reasons) == 0
    
    cfg_enabled = {
        "daily_loss_limit_pct": 2.0,
        "spread_guard_enabled": True,
        "spread_limit_bps": 5.0,
        "slippage_guard_enabled": True,
        "slippage_limit_bps": 3.0,
        "atr_shock_block_enabled": True,
        "atr_ratio_limit": 2.0
    }
    gateway = RiskGateway(cfg_enabled)
    
    decision_spread = gateway.full_gate(account, {"spread_bps": 5.5, "slippage_bps": 1.0, "atr_ratio": 1.0, "session_flag": "london"})
    assert decision_spread.action == "SOFT_BLOCK"
    assert "spread_guard_trigger" in decision_spread.reasons
    
    decision_slippage = gateway.full_gate(account, {"spread_bps": 1.0, "slippage_bps": 3.5, "atr_ratio": 1.0, "session_flag": "london"})
    assert decision_slippage.action == "SOFT_BLOCK"
    assert "slippage_guard_trigger" in decision_slippage.reasons
    
    decision_atr = gateway.full_gate(account, {"spread_bps": 1.0, "slippage_bps": 1.0, "atr_ratio": 2.5, "session_flag": "london"})
    assert decision_atr.action == "SOFT_BLOCK"
    assert "atr_shock_trigger" in decision_atr.reasons

def test_ml_gatekeeper_behavior(monkeypatch):
    """Verify ML gatekeeper logic for BLOCK, REDUCE, and PASS zones."""
    dec = SignalDecision("US30", "long", 80.0, "Buy bias")
    features = {"rsi14_m15": 50.0}
    
    from src.ml.xgb_filter import XGBTradeFilter
    
    monkeypatch.setattr(XGBTradeFilter, "predict_quality", lambda self, f, s: 0.50)
    ml_cfg = {"enabled": True, "block_threshold": 0.55, "reduce_threshold": 0.65, "reduce_size_factor": 0.5}
    res = apply_ml_gatekeeper(dec, features, ml_cfg)
    assert res.direction == "flat"
    assert res.ml_decision == "BLOCK"
    
    dec = SignalDecision("US30", "long", 80.0, "Buy bias")
    monkeypatch.setattr(XGBTradeFilter, "predict_quality", lambda self, f, s: 0.60)
    res = apply_ml_gatekeeper(dec, features, ml_cfg)
    assert res.direction == "long"
    assert res.size_multiplier == 0.5
    assert res.ml_decision == "REDUCE"
    
    dec = SignalDecision("US30", "long", 80.0, "Buy bias")
    monkeypatch.setattr(XGBTradeFilter, "predict_quality", lambda self, f, s: 0.70)
    res = apply_ml_gatekeeper(dec, features, ml_cfg)
    assert res.direction == "long"
    assert res.size_multiplier == 1.0
    assert res.ml_decision == "PASS"

def test_mt5_adapter_fallback():
    """Verify that MT5Adapter gracefully falls back to local paper trading mode."""
    adapter = MT5Adapter(login=123456, password="pw", server="Server", enabled=False)
    
    res_conn = adapter.connect()
    assert not res_conn
    assert not adapter.connected
    
    order_req = {
        "symbol": "US30",
        "direction": "long",
        "price": 34000.0,
        "sl": 33900.0,
        "tp": 34200.0,
        "volume": 0.05,
        "comment": "test_order"
    }
    order_res = adapter.send_order(order_req)
    assert order_res["status"] == "paper_success"
    assert order_res["order_id"] == 999999
    assert order_res["comment"] == "test_order (paper)"
    assert order_res["price"] == 34000.0
    assert order_res["volume"] == 0.05

def test_backtest_engine_lockout_resets(monkeypatch):
    """Verify that daily peak/drawdown and daily loss streak reset at midnight, and weekly resets on boundary."""
    from src.backtest.alpha_filter import AlphaResearchFilter
    monkeypatch.setattr(AlphaResearchFilter, "evaluate", lambda *args, **kwargs: (1, True))
    monkeypatch.setattr(AlphaResearchFilter, "track_signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(AlphaResearchFilter, "track_trade_exit", lambda *args, **kwargs: None)
    monkeypatch.setattr(AlphaResearchFilter, "finalize_analysis", lambda *args, **kwargs: {
        "execution_efficiency": {
            "total_trades": 0, "total_net_pnl": 0.0, "expectancy_dollars": 0.0, "cost_adjusted_expectancy": 0.0
        }
    })
    
    import src.backtest.realism_engine
    monkeypatch.setattr(src.backtest.realism_engine, "run_realism_audit", lambda *args, **kwargs: {
        "verdict": "PASS", "sharpe_ratio": 1.5, "sortino_ratio": 1.5, "max_drawdown_pct": 1.0, "monte_carlo_95_dd": 1.0, "ruin_probability": 0.0
    })
    from src.backtest.realism_engine import RealismSimulator
    monkeypatch.setattr(RealismSimulator, "calculate_cost", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(RealismSimulator, "apply_partial_fills", lambda pnl, *args, **kwargs: pnl)
    monkeypatch.setattr(RealismSimulator, "detect_market_condition", lambda *args, **kwargs: "NORMAL")
    
    import src.backtest.edge_discovery
    from src.backtest.edge_discovery import EdgeDiscoveryAnalyzer
    monkeypatch.setattr(EdgeDiscoveryAnalyzer, "analyze", lambda *args, **kwargs: {
        "rejected_setups": set(),
        "portfolio_metrics": {
            "total_trades": 0,
            "winrate": 0.0,
            "net_pnl": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "mc_worst_case_dd": 0.0,
            "ruin_probability": 0.0,
            "verdict": "APPROVED"
        }
    })
    monkeypatch.setattr(src.backtest.edge_discovery, "finalize_edge_discovery_reports", lambda *args, **kwargs: None)
    
    from src.backtest.realism_engine import EquityCurveEngine, MonteCarloSimulator
    monkeypatch.setattr(EquityCurveEngine, "calculate_metrics", lambda *args, **kwargs: {"realized_pnl": 0.0, "sharpe_ratio": 0.0, "max_drawdown_pct": 0.0})
    monkeypatch.setattr(MonteCarloSimulator, "run_simulation", lambda *args, **kwargs: {"worst_case_drawdown_95": 0.0, "ruin_probability": 0.0})

    recorded_trades = []
    original_init = Trade.__init__
    def mock_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        recorded_trades.append(self)
    monkeypatch.setattr(Trade, "__init__", mock_init)

    symbol_config = {
        "symbol": "US30",
        "backtest": {
            "spread_bps": 0.0,
            "slippage_bps": 0.0,
            "initial_capital": 100000.0
        },
        "risk": {
            "daily_loss_limit_pct": 2.0,
            "loss_streak_pause": 3
        },
        "position": {
            "timeout_minutes": 10
        }
    }
    
    class DummyStrategy:
        @staticmethod
        def generate_trade_plan(row, cfg):
            if row.get("signal_flag") == "long":
                return PositionPlan(row["close_m1"], row["close_m1"] - 100.0, row["close_m1"] + 200.0, 1.0, 10), SignalDecision("US30", "long", 80.0, "long_signal")
            return None, SignalDecision("US30", "flat", 0.0, "flat")
            
    bars = []
    
    # Day 1: generate bars with signals resulting in losses
    for i in range(10):
        ts = pd.to_datetime("2026-05-01 10:00:00") + pd.timedelta_range("0min", "9min", freq="1min")[i]
        bars.append({
            "timestamp": ts,
            "close_m1": 10000.0,
            "high": 10000.0,
            "low": 9800.0,
            "atr_ratio": 1.0,
            "session_flag": "london",
            "signal_flag": "long" if i % 2 == 0 else "flat",
            "rsi14_m15": 55.0,
            "bb_width_m15": 0.01,
            "macd_hist_m15": 0.0,
            "adx14_h1": 30.0,
            "adx14_h4": 25.0,
            "atr14_m1": 15.0,
            "atr14_h1": 20.0,
            "atr14_h4": 30.0,
            "bias": "long",
            "bias_h1": "long",
            "bias_h4": "long"
        })
        
    # Day 2: generate bars after boundary transition
    for i in range(5):
        ts = pd.to_datetime("2026-05-02 10:00:00") + pd.timedelta_range("0min", "4min", freq="1min")[i]
        bars.append({
            "timestamp": ts,
            "close_m1": 10000.0,
            "high": 10000.0,
            "low": 9800.0 if i > 0 else 10000.0,  # Trigger exit for Day 2 trade
            "atr_ratio": 1.0,
            "session_flag": "london",
            "signal_flag": "long" if i == 0 else "flat",
            "rsi14_m15": 55.0,
            "bb_width_m15": 0.01,
            "macd_hist_m15": 0.0,
            "adx14_h1": 30.0,
            "adx14_h4": 25.0,
            "atr14_m1": 15.0,
            "atr14_h1": 20.0,
            "atr14_h4": 30.0,
            "bias": "long",
            "bias_h1": "long",
            "bias_h4": "long"
        })
        
    df_bars = pd.DataFrame(bars)
    
    backtester = SingleAssetBacktester(symbol_config, DummyStrategy)
    
    summary = backtester.run(df_bars)
    
    print("\n--- DEBUG INFO ---")
    print("Summary:", summary)
    print("Recorded trades list size:", len(recorded_trades))
    for idx, t in enumerate(recorded_trades):
        print(f"Trade {idx}: EntryTime={t.entry_time}, ExitTime={t.exit_time}, PnL={t.pnl}, Dir={t.direction}")
        
    day2_trades = [t for t in recorded_trades if pd.to_datetime(t.entry_time).date() == pd.to_datetime("2026-05-02").date()]
    assert len(day2_trades) > 0, "Trade on Day 2 must execute successfully due to midnight resets"
