import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Setup path to import run_edge_validation
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
V9_1_DIR = PROJECT_DIR.parent.parent
sys.path.insert(0, str(V9_1_DIR))

from run_edge_validation import run_monte_carlo, simulate_validation_trade

def test_monte_carlo_helper():
    """Verify that Monte Carlo bootstrap helper correctly computes confidence intervals."""
    # Positive returns
    returns = np.array([0.5, 0.2, -0.1, 0.4, 0.3, -0.2, 0.1, 0.6, -0.05, 0.2] * 10) # 100 trades
    mc = run_monte_carlo(returns, num_bootstrap=100)
    
    assert "5th_pnl" in mc
    assert "mean_pnl" in mc
    assert "95th_pnl" in mc
    assert "pf_5th" in mc
    assert "sharpe_5th" in mc
    
    # Positive returns should have positive mean
    assert mc["mean_pnl"] > 0
    # 5th percentile should be less than or equal to the mean
    assert mc["5th_pnl"] <= mc["mean_pnl"]
    
def test_dynamic_trade_simulation():
    """Verify dynamic cost calculation and regime latency execution delay."""
    # Setup mock dataframe
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-05-01 08:00:00", periods=70, freq="1min"),
        "open": [100.0] * 70,
        "high": [100.1] * 70,
        "low": [99.9] * 70,
        "close": [100.0] * 70,
        "volume": [10.0] * 70,
        "atr": [1.0] * 70,
        "atr_ratio": [1.0] * 70,
        "session_flag": ["london"] * 70,
        "adx14_h1": [30.0] * 70,
        "adx14_h4": [25.0] * 70,
        "session_type": ["London Open"] * 70,
        "volatility_state": ["Normal"] * 70,
        "liquidity_pattern": ["None"] * 70,
    })
    
    # 1. Normal execution (No delay, normal costs)
    trade = simulate_validation_trade(
        df=df,
        trigger_idx=5,
        direction="long",
        base_spread=1.0,
        base_slippage=0.5,
        cost_multiplier=1.0
    )
    
    # Since prices are flat, gross return should be 0.0%
    assert trade["gross_return_pct"] == 0.0
    # Net return should be gross - total_cost_bps/100
    # Total cost is 1.0 (spread) + 0.5 (slippage) = 1.5 bps
    # Net return = 0 - 0.015% = -0.015%
    assert pytest.approx(trade["net_return_pct"]) == -0.015
    assert trade["entry_delay"] == 1 # Trend/normal default latency since trend/adx defaults to Normal/trend
    
    # 2. High Volatility / Shock Scaling
    df.loc[5, "atr_ratio"] = 2.0  # News spike volatility
    trade_news = simulate_validation_trade(
        df=df,
        trigger_idx=5,
        direction="long",
        base_spread=1.0,
        base_slippage=0.5,
        cost_multiplier=1.0
    )
    
    # Spreads scaled by 1.5x (1.5 bps), slippage scaled by 2x (1.0 bps)
    # Total cost = 2.5 bps
    assert pytest.approx(trade_news["net_return_pct"]) == -0.025
