import pandas as pd
import numpy as np

def compute_atr(df: pd.DataFrame, p: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder's MA for ATR
    atr = tr.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    return atr.fillna(tr.rolling(p).mean()).fillna(0.001)
