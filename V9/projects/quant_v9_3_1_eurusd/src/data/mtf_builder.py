from __future__ import annotations
from typing import Dict, Any
import pandas as pd
from src.indicators.rsi import compute_rsi
from src.indicators.adx import compute_adx
from src.indicators.atr import compute_atr

def build_feature_table(df_m1: pd.DataFrame) -> pd.DataFrame:
    df = df_m1.copy().sort_values("timestamp").reset_index(drop=True)
    # Full indicator set
    df["rsi14_m15"] = compute_rsi(df["close"], 14)
    df["adx14_h1"] = compute_adx(df, 14)
    df["adx14_h4"] = compute_adx(df, 14) # simplified mtf for training
    df["atr14_m1"] = compute_atr(df, 14)
    df["atr14_h1"] = compute_atr(df, 14)
    df["atr_ratio"] = (df["atr14_m1"] / df["atr14_h1"].replace(0, 1)).fillna(1.0)
    df["bb_width_m15"] = 0.01 # placeholder
    df["macd_hist_m15"] = 0.001 # placeholder
    df["session_flag"] = "london"
    df["bias"] = "long" # Assume long trend for mock data
    df["bias_h1"] = "long"
    df["bias_h4"] = "long"
    df["hour_sin"] = 0.0
    df["hour_cos"] = 0.0
    df["close_m1"] = df["close"]
    return df.dropna()
