import pandas as pd
import numpy as np

def compute_adx(df: pd.DataFrame, p: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # TR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    
    up = high.diff()
    down = -low.diff()
    
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    smooth_plus_dm = pd.Series(plus_dm, index=df.index).ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    smooth_minus_dm = pd.Series(minus_dm, index=df.index).ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    
    plus_di = 100 * (smooth_plus_dm / atr.replace(0, 1e-9))
    minus_di = 100 * (smooth_minus_dm / atr.replace(0, 1e-9))
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-9)
    adx = dx.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    
    return adx.fillna(25.0)
