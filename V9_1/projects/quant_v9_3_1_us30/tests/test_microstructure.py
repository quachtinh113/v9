import pytest
import pandas as pd
import numpy as np
from src.core.microstructure import MicrostructureDetector, simulate_expectancy

def test_detector_basic():
    # Create mock M1 data: 100 rows
    dates = pd.date_range(start="2025-01-01 00:00:00", periods=200, freq="1min")
    np.random.seed(42)
    close = np.linspace(100.0, 105.0, 200) + np.random.normal(0, 0.1, 200)
    high = close + 0.2
    low = close - 0.2
    open_val = close - np.random.normal(0, 0.05, 200)
    volume = np.random.randint(100, 1000, 200)
    
    # Inject a news spike
    volume[100] = 5000
    high[100] = close[100] + 2.0
    low[100] = close[100] - 2.0
    
    df = pd.DataFrame({
        "timestamp": dates.astype(str),
        "open": open_val,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })
    
    detector = MicrostructureDetector(df, atr_period=14, lookback=10)
    res = detector.run_detection()
    
    assert "atr" in res.columns
    assert "session_type" in res.columns
    assert "volatility_state" in res.columns
    assert "liquidity_pattern" in res.columns
    
    # Verify that dynamic news spike triggered Pre-News and Post-News around index 100
    assert "Post-News" in res["session_type"].values
    assert "Pre-News" in res["session_type"].values

def test_expectancy_simulation():
    # Simple df with flat prices
    dates = pd.date_range(start="2025-01-01 00:00:00", periods=10, freq="1min")
    df = pd.DataFrame({
        "timestamp": dates.astype(str),
        "open": [100.0] * 10,
        "high": [101.0] * 10,
        "low": [99.0] * 10,
        "close": [100.0] * 10,
        "volume": [500] * 10,
        "atr": [1.0] * 10
    })
    
    # At index 2: Buy
    # SL = 100 - 1.0 * 1.0 = 99.0. If low goes to 99.0, it should exit with SL.
    # TP = 100 + 1.5 * 1.0 = 101.5. High is 101.0, so TP is not hit.
    pnl, reason = simulate_expectancy(df, entry_index=2, direction="long", tp_mult=1.5, sl_mult=1.0, max_bars=3)
    assert reason == "SL"
    assert pnl == -1.0
