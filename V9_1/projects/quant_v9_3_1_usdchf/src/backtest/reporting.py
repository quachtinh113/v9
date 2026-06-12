from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def export_summary_json(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=4)
    return path

def export_trade_log_csv(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "trades.csv"
    path.write_text("symbol,direction,entry,exit,pnl,bars_held,exit_reason\n")
    return path

def export_report_md(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.md"
    path.write_text(f"# Backtest Report\nSymbol: {result.get('symbol')}\n")
    return path
