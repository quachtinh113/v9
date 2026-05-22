import sys
from pathlib import Path
import pandas as pd
import numpy as np

V9_1_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V9_1_DIR))

from run_edge_validation import load_symbol_data, simulate_validation_trade
from src.core.microstructure import MicrostructureDetector

print("Loading data...")
df = load_symbol_data("GBPUSD")
print("Detecting microstructure patterns...")
detector = MicrostructureDetector(df)
res_df = detector.run_detection()

# Find false breakout triggers
fb_long = res_df["liquidity_pattern"] == "Downside False Breakout"
trigger_indices = res_df[fb_long].index.tolist()

print("Found Downside False Breakout triggers count:", len(trigger_indices))
for i, idx in enumerate(trigger_indices[:5]):
    t = simulate_validation_trade(res_df, idx, "long", 1.0, 0.5)
    print(f"Trade {i}: idx={idx}, entry_idx={idx + t['entry_delay']}, exit_reason={t['exit_reason']}, gross={t['gross_return_pct']:.4f}%, net={t['net_return_pct']:.4f}%, cost={t['cost_bps']:.2f} bps, regime={t['regime']}")
