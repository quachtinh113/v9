import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

class MicrostructureDetector:
    def __init__(self, df: pd.DataFrame, atr_period: int = 14, lookback: int = 30):
        self.df = df.copy().sort_values("timestamp").reset_index(drop=True)
        self.atr_period = atr_period
        self.lookback = lookback
        self._prepare_indicators()

    def _prepare_indicators(self):
        # 1. Real ATR Calculation
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Wilder's smoothing for ATR
        self.df["atr"] = tr.ewm(alpha=1/self.atr_period, min_periods=self.atr_period, adjust=False).mean()
        self.df["atr"] = self.df["atr"].fillna(tr.rolling(self.atr_period).mean()).fillna(0.001)
        
        # ATR H1 (smoothed over 60 bars to simulate hourly ATR)
        self.df["atr_h1"] = self.df["atr"].rolling(60).mean().fillna(self.df["atr"])
        self.df["atr_ratio"] = (self.df["atr"] / self.df["atr_h1"].replace(0, 1e-9)).fillna(1.0)
        
        # 2. Bollinger Bands
        self.df["bb_mid"] = close.rolling(20).mean()
        self.df["bb_std"] = close.rolling(20).std()
        self.df["bb_upper"] = self.df["bb_mid"] + 2.0 * self.df["bb_std"]
        self.df["bb_lower"] = self.df["bb_mid"] - 2.0 * self.df["bb_std"]
        self.df["bb_width"] = ((self.df["bb_upper"] - self.df["bb_lower"]) / self.df["bb_mid"].replace(0, 1e-9)).fillna(0.01)
        
        # 3. Rolling extremes for liquidity levels
        self.df["roll_high"] = high.shift(1).rolling(self.lookback).max()
        self.df["roll_low"] = low.shift(1).rolling(self.lookback).min()
        
        # Parse timestamp to hour and minute
        self.df["dt"] = pd.to_datetime(self.df["timestamp"])
        self.df["hour"] = self.df["dt"].dt.hour
        self.df["minute"] = self.df["dt"].dt.minute
        self.df["time_str"] = self.df["dt"].dt.strftime("%H:%M")

    def detect_sessions(self) -> pd.Series:
        """Classify sessions: London Open, NY Open, Lunch, Pre-News, Post-News, Other."""
        sessions = pd.Series("Other", index=self.df.index)
        
        # Standard news times in UTC: 13:30 (US CPI/NFP) and 19:00 (FOMC)
        # Pre-News: 1 hour before news (12:30-13:30, 18:00-19:00 UTC)
        # Post-News: 1.5 hours after news (13:30-15:00, 19:00-20:30 UTC)
        
        for idx, row in self.df.iterrows():
            hour = row["hour"]
            minute = row["minute"]
            time_val = hour * 60 + minute
            
            # London Open: 08:00 - 10:00 UTC
            if 8 <= hour < 10:
                sessions.iloc[idx] = "London Open"
            # NY Open: 13:00 - 15:00 UTC
            elif 13 <= hour < 15:
                sessions.iloc[idx] = "NY Open"
            # Lunch Session: 11:30 - 13:00 UTC and 16:30 - 18:30 UTC
            elif (11*60 + 30 <= time_val < 13*60) or (16*60 + 30 <= time_val < 18*60 + 30):
                sessions.iloc[idx] = "Lunch Session"
                
            # Pre-News (Fixed): 12:30-13:30 and 18:00-19:00 UTC
            if (12*60 + 30 <= time_val < 13*60 + 30) or (18*60 <= time_val < 19*60):
                sessions.iloc[idx] = "Pre-News"
            # Post-News (Fixed): 13:30-15:00 and 19:00-20:30 UTC
            elif (13*60 + 30 <= time_val < 15*60) or (19*60 <= time_val < 20*60 + 30):
                sessions.iloc[idx] = "Post-News"
                
        # Dynamic News Spike detection based on Volume/Volatility
        # If Volume > 4x and range > 3x ATR, flag as dynamic News Spike.
        self.df["vol_sma"] = self.df["volume"].rolling(20).mean().fillna(1.0)
        self.df["range"] = self.df["high"] - self.df["low"]
        
        spike_cond = (self.df["volume"] > 4.0 * self.df["vol_sma"]) & (self.df["range"] > 3.0 * self.df["atr"])
        spike_indices = self.df[spike_cond].index
        
        for idx in spike_indices:
            # Pre-news: 30 bars before spike
            pre_start = max(0, idx - 30)
            sessions.iloc[pre_start:idx] = "Pre-News"
            # Post-news: 90 bars after spike
            post_end = min(len(self.df), idx + 90)
            sessions.iloc[idx:post_end] = "Post-News"
            
        return sessions

    def detect_volatility_states(self) -> pd.Series:
        """Classify volatility states: Squeeze, Expansion, Clustering, Normal."""
        states = pd.Series("Normal", index=self.df.index)
        
        # 1. Bollinger Band Squeeze
        # Bottom 20% of BB width over rolling 300 periods
        bb_width_threshold = self.df["bb_width"].rolling(300).quantile(0.20)
        squeeze_cond = self.df["bb_width"] <= bb_width_threshold
        states[squeeze_cond] = "Squeeze"
        
        # 2. Breakout Expansion
        # Range is > 2.5 * ATR and atr_ratio > 1.3
        expansion_cond = (self.df["range"] > 2.5 * self.df["atr"]) & (self.df["atr_ratio"] > 1.3)
        states[expansion_cond] = "Expansion"
        
        # 3. Volatility Clustering
        # Top 30% of rolling standard deviation of close returns
        returns = self.df["close"].pct_change()
        vol_std = returns.rolling(100).std()
        vol_std_threshold = vol_std.rolling(500).quantile(0.70)
        clustering_cond = (vol_std >= vol_std_threshold) & (~squeeze_cond) & (~expansion_cond)
        states[clustering_cond] = "Clustering"
        
        return states

    def detect_liquidity_patterns(self) -> pd.Series:
        """Classify liquidity patterns: Stop Hunt, Sweep, False Breakout, Range Raid, None."""
        patterns = pd.Series("None", index=self.df.index)
        
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        open_val = self.df["open"]
        roll_high = self.df["roll_high"]
        roll_low = self.df["roll_low"]
        atr = self.df["atr"]
        
        # 1. Sweep
        upside_sweep = (high > roll_high) & (close <= roll_high)
        downside_sweep = (low < roll_low) & (close >= roll_low)
        
        patterns[upside_sweep] = "Upside Sweep"
        patterns[downside_sweep] = "Downside Sweep"
        
        # 2. Stop Hunt
        # A sweep where the pierce is small (< 1.0 * ATR) and candle shows reversal
        # For upside: high sweeps roll_high but by <= 1.0 * ATR, and close < open (bearish) or close is near low
        upside_stophunt = upside_sweep & ((high - roll_high) <= 1.0 * atr) & (close < open_val)
        downside_stophunt = downside_sweep & ((roll_low - low) <= 1.0 * atr) & (close > open_val)
        
        patterns[upside_stophunt] = "Upside Stop Hunt"
        patterns[downside_stophunt] = "Downside Stop Hunt"
        
        # 3. False Breakout
        # Close is outside level, but within next 3 bars close crosses back inside
        for idx in range(self.lookback, len(self.df) - 3):
            # Upside false breakout
            if close.iloc[idx] > roll_high.iloc[idx]:
                # Pierced, check if it closes back below roll_high in next 3 bars
                if (close.iloc[idx+1:idx+4] < roll_high.iloc[idx]).any():
                    patterns.iloc[idx] = "Upside False Breakout"
            # Downside false breakout
            elif close.iloc[idx] < roll_low.iloc[idx]:
                if (close.iloc[idx+1:idx+4] > roll_low.iloc[idx]).any():
                    patterns.iloc[idx] = "Downside False Breakout"
                    
        # 4. Range Raid
        # Sweeps both rolling high and rolling low within a 20-bar window
        # We can calculate if there is an upside sweep/stophunt/false breakout AND downside sweep/stophunt/false breakout in the last 20 bars
        any_upside_sweep = upside_sweep | (patterns.str.contains("Upside"))
        any_downside_sweep = downside_sweep | (patterns.str.contains("Downside"))
        
        rolling_upside = any_upside_sweep.rolling(20).max().fillna(0).astype(bool)
        rolling_downside = any_downside_sweep.rolling(20).max().fillna(0).astype(bool)
        
        range_raid = rolling_upside & rolling_downside
        patterns[range_raid & (any_upside_sweep | any_downside_sweep)] = "Range Raid"
        
        return patterns

    def run_detection(self) -> pd.DataFrame:
        self.df["session_type"] = self.detect_sessions()
        self.df["volatility_state"] = self.detect_volatility_states()
        self.df["liquidity_pattern"] = self.detect_liquidity_patterns()
        return self.df

def simulate_expectancy(df: pd.DataFrame, entry_index: int, direction: str, tp_mult: float = 1.5, sl_mult: float = 1.0, max_bars: int = 60) -> Tuple[float, str]:
    """
    Simulate a position entry at entry_index.
    Returns:
        (pnl_ratio_atr, exit_reason)
        pnl_ratio_atr is PnL divided by entry ATR (e.g. +1.5 if TP hit, -1.0 if SL hit).
    """
    if entry_index >= len(df) - 1:
        return 0.0, "End of Data"
        
    entry_price = df.loc[entry_index, "close"]
    atr = df.loc[entry_index, "atr"]
    if atr <= 0:
        atr = 0.001
        
    if direction == "long":
        tp = entry_price + tp_mult * atr
        sl = entry_price - sl_mult * atr
    else: # short
        tp = entry_price - tp_mult * atr
        sl = entry_price + sl_mult * atr
        
    for offset in range(1, max_bars + 1):
        idx = entry_index + offset
        if idx >= len(df):
            # End of data, exit at close
            exit_price = df.loc[len(df)-1, "close"]
            pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            return pnl / atr, "Timeout"
            
        high = df.loc[idx, "high"]
        low = df.loc[idx, "low"]
        close = df.loc[idx, "close"]
        
        if direction == "long":
            # Check SL first (conservative)
            if low <= sl:
                return -sl_mult, "SL"
            if high >= tp:
                return tp_mult, "TP"
        else: # short
            if high >= sl:
                return -sl_mult, "SL"
            if low <= tp:
                return tp_mult, "TP"
                
    # Timeout
    exit_price = df.loc[entry_index + max_bars, "close"]
    pnl = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
    return pnl / atr, "Timeout"
