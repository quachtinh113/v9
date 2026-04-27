def compute_rsi(s, p=14): return s.pct_change().fillna(0) # placeholder
def compute_adx(df, p=14): return df["close"].pct_change().fillna(0) # placeholder
def compute_atr(df, p=14): return df["close"].pct_change().fillna(0) # placeholder
