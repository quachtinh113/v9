from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED_COLS = {"timestamp", "open", "high", "low", "close", "volume"}

def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists(): raise FileNotFoundError(f"Missing {path}")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df

def generate_sample_ohlcv(symbol: str, periods: int = 10000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2025-01-01", periods=periods, freq="min", tz="UTC")
    start = 100.0
    if "US30" in symbol: start = 38000.0
    elif "XAU" in symbol: start = 2000.0
    rets = rng.normal(0.00001, 0.001, periods)
    close = start * np.exp(np.cumsum(rets))
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": close * 0.9999, "high": close * 1.001, "low": close * 0.999, "close": close, "volume": 500
    })
    return df

def resolve_csv_source(repo_root, symbol, csv_path=None):
    if csv_path: return Path(csv_path)
    target = Path(repo_root) / "data" / "raw" / f"{symbol}_M1_sample.csv"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        df = generate_sample_ohlcv(symbol)
        df.to_csv(target, index=False)
        print(f"Generated sample data for {symbol}")
    return target
