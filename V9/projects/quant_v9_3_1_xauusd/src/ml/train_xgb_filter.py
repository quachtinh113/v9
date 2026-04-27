from __future__ import annotations
import argparse, json, logging, os, sys
from pathlib import Path
import numpy as np, pandas as pd
try: import xgboost as xgb
except: xgb = None
from src.data.loaders import resolve_csv_source, load_ohlcv_csv
from src.data.mtf_builder import build_feature_table
from src.ml.xgb_filter import FEATURE_NAMES

def _build_dataset(ft, config):
    from src.core.signal_engine import evaluate_signal
    records = []
    for row in ft.to_dict("records"):
        dec = evaluate_signal(row, config)
        if dec.direction == "flat": continue
        # Label 1 for profit, 0 for loss (simplified random for mock)
        label = 1 if np.random.random() > 0.45 else 0
        records.append({**{f: row.get(f, 0) for f in FEATURE_NAMES}, "label": label}) 
    return pd.DataFrame(records)

def train_model(ds, path):
    if xgb is None: return
    X, y = ds[FEATURE_NAMES].values, ds["label"].values
    d = xgb.DMatrix(X, label=y, feature_names=FEATURE_NAMES)
    bst = xgb.train({"objective": "binary:logistic"}, d, 20)
    bst.save_model(str(path))

def main():
    root = Path(__file__).resolve().parents[2]
    from src.utils.config import load_yaml
    config = load_yaml(root / "config" / "symbol.yaml")
    csv = resolve_csv_source(root, config["symbol"])
    df = load_ohlcv_csv(csv)
    ft = build_feature_table(df)
    ds = _build_dataset(ft, config)
    if len(ds) >= 50:
        path = root / config.get("ml", {}).get("model_path", "models/xgb_trade_filter.json")
        path.parent.mkdir(exist_ok=True)
        train_model(ds, path)
        print(f"XGB Trained for {config['symbol']}: {len(ds)} signals")
    else:
        print(f"Not enough signals for {config['symbol']}: {len(ds)}")

if __name__ == "__main__": main()
