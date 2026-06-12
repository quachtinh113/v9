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
    # Disable ML filter during dataset building so we evaluate raw signal candidates
    cfg_copy = dict(config)
    if "ml" in cfg_copy:
        cfg_copy["ml"] = dict(cfg_copy["ml"])
        cfg_copy["ml"]["enabled"] = False
        
    symbol = config.get("symbol", "US30")
    strategy_name = symbol.lower() + "_strategy"
    try:
        strategy_module = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
    except ImportError:
        strategy_module = None
        
    records = []
    rows = ft.to_dict("records")
    n = len(rows)
    for i, row in enumerate(rows):
        if strategy_module is not None:
            plan, dec = strategy_module.generate_trade_plan(row, cfg_copy)
        else:
            from src.core.signal_engine import evaluate_signal
            dec = evaluate_signal(row, cfg_copy)
            from src.core.models import PositionPlan
            plan = PositionPlan(row["close_m1"], row["close_m1"]*0.99, row["close_m1"]*1.02, 0.25, 120) if dec.direction != "flat" else None
            
        if plan is None or dec.direction == "flat":
            continue
            
        direction = dec.direction
        sl = plan.stop_loss
        tp = plan.take_profit
        timeout = plan.timeout_minutes
        
        label = 0
        # Look forward up to timeout bars
        for j in range(i + 1, min(i + 1 + timeout, n)):
            f_row = rows[j]
            f_high = float(f_row.get("high", f_row["close_m1"]))
            f_low = float(f_row.get("low", f_row["close_m1"]))
            
            if direction == "long":
                if f_low <= sl:
                    label = 0
                    break
                elif f_high >= tp:
                    label = 1
                    break
            elif direction == "short":
                if f_high >= sl:
                    label = 0
                    break
                elif f_low <= tp:
                    label = 1
                    break
                    
        records.append({**{f: row.get(f, 0) for f in FEATURE_NAMES}, "label": label, "regime": dec.regime})
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
    from src.ml.validation import walk_forward_validation
    from src.ml.audit_reporter import generate_all_reports
    
    config = load_yaml(root / "config" / "symbol.yaml")
    csv = resolve_csv_source(root, config["symbol"])
    df = load_ohlcv_csv(csv)
    ft = build_feature_table(df)
    ds = _build_dataset(ft, config)
    
    if len(ds) >= 50:
        path = root / config.get("ml", {}).get("model_path", "models/xgb_trade_filter.json")
        path.parent.mkdir(exist_ok=True)
        
        # 1. Train final model on full dataset
        train_model(ds, path)
        print(f"XGB Trained for {config['symbol']}: {len(ds)} signals")
        
        # 2. Walk-forward validation and Audit Reporting
        print(f"Running walk-forward validation for {config['symbol']}...")
        metrics = walk_forward_validation(ds, FEATURE_NAMES, n_splits=3)
        
        if metrics:
            audit_dir = root / "reports" / "training_audit"
            generate_all_reports(metrics, audit_dir, config["symbol"])
            print(f"Audit reports generated at {audit_dir}")
            
            if metrics.get("overfitting_detected"):
                print(f"WARNING: Overfitting detected for {config['symbol']}! Delta > 0.15")
    else:
        print(f"Not enough signals for {config['symbol']}: {len(ds)}")

if __name__ == "__main__": main()
