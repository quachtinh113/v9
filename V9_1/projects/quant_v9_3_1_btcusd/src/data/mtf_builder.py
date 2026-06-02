from __future__ import annotations
from typing import Dict, Any
import pandas as pd
import numpy as np
from src.indicators.rsi import compute_rsi
from src.indicators.adx import compute_adx
from src.indicators.atr import compute_atr
from src.utils.frequency import normalize_pandas_frequency

def build_feature_table(df_m1: pd.DataFrame, session_policy: str = "fx") -> pd.DataFrame:
    if df_m1.empty:
        return pd.DataFrame()
        
    df = df_m1.copy().sort_values("timestamp").reset_index(drop=True)
    df.set_index("timestamp", inplace=True)
    
    # 1. Compute M1 features (shifted by 1 to prevent look-ahead bias)
    df["atr14_m1"] = compute_atr(df, 14).shift(1)
    df["close_m1"] = df["close"]
    df["close_m5"] = df["close"]
    
    # 2. Resample to higher timeframes and compute resampled features
    # M15
    df_m15 = df.resample("15Min", closed="left", label="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    
    rsi_m15 = compute_rsi(df_m15["close"], 14).shift(1)
    
    bb_mid_m15 = df_m15["close"].rolling(20).mean()
    bb_std_m15 = df_m15["close"].rolling(20).std()
    bb_width_m15 = ((bb_mid_m15 + 2 * bb_std_m15) - (bb_mid_m15 - 2 * bb_std_m15)) / bb_mid_m15.replace(0, 1e-9)
    bb_width_m15 = bb_width_m15.shift(1)
    
    ema12_m15 = df_m15["close"].ewm(span=12, adjust=False).mean()
    ema26_m15 = df_m15["close"].ewm(span=26, adjust=False).mean()
    macd_m15 = ema12_m15 - ema26_m15
    macd_sig_m15 = macd_m15.ewm(span=9, adjust=False).mean()
    macd_hist_m15 = (macd_m15 - macd_sig_m15).shift(1)
    
    ema50_m15 = df_m15["close"].ewm(span=50, adjust=False).mean()
    bias_m15 = pd.Series(np.where(df_m15["close"] > ema50_m15, "long", "short"), index=df_m15.index).shift(1)
    
    # H1
    df_h1 = df.resample("1h", closed="left", label="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    
    adx_h1 = compute_adx(df_h1, 14).shift(1)
    atr_h1 = compute_atr(df_h1, 14).shift(1)
    
    ema50_h1 = df_h1["close"].ewm(span=50, adjust=False).mean()
    bias_h1 = pd.Series(np.where(df_h1["close"] > ema50_h1, "long", "short"), index=df_h1.index).shift(1)
    
    # H4
    df_h4 = df.resample(normalize_pandas_frequency("4H"), closed="left", label="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    
    adx_h4 = compute_adx(df_h4, 14).shift(1)
    atr_h4 = compute_atr(df_h4, 14).shift(1)
    
    # Use shorter 10-period EMA on H4 to prevent cold start / warming up NaNs when data has only 10,000 minutes
    ema10_h4 = df_h4["close"].ewm(span=10, adjust=False).mean()
    bias_h4 = pd.Series(np.where(df_h4["close"] > ema10_h4, "long", "short"), index=df_h4.index).shift(1)
    
    # 3. Reindex and forward fill resampled features back to df (M1) index
    df["rsi14_m15"] = rsi_m15.reindex(df.index, method="ffill")
    df["bb_width_m15"] = bb_width_m15.reindex(df.index, method="ffill")
    df["macd_hist_m15"] = macd_hist_m15.reindex(df.index, method="ffill")
    df["bias"] = bias_m15.reindex(df.index, method="ffill")
    
    df["adx14_h1"] = adx_h1.reindex(df.index, method="ffill")
    df["atr14_h1"] = atr_h1.reindex(df.index, method="ffill")
    df["bias_h1"] = bias_h1.reindex(df.index, method="ffill")
    
    df["adx14_h4"] = adx_h4.reindex(df.index, method="ffill")
    df["atr14_h4"] = atr_h4.reindex(df.index, method="ffill")
    df["bias_h4"] = bias_h4.reindex(df.index, method="ffill")
    
    # 4. atr_ratio
    df["atr_ratio"] = (df["atr14_m1"] / df["atr14_h1"].replace(0, 1e-9)).fillna(1.0)
    
    # 5. session_flag from time (UTC)
    df["hour"] = df.index.hour
    df["minute"] = df.index.minute
    
    def calc_session(hour):
        if session_policy == "always_on":
            return "crypto_24_7"
        if 8 <= hour < 13:
            return "london"
        elif 13 <= hour < 21:
            return "new_york"
        else:
            return "off"
            
    df["session_flag"] = df["hour"].apply(calc_session)
    
    # Time sinusoidal encodings
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    
    # Dropna to drop the initial warming-up rows with NaNs
    df.reset_index(inplace=True)
    return df.dropna()