from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def export_summary_json(result, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(result, f, indent=4)

def export_trade_log_csv(result, out_dir):
    pass # placeholder for now

def export_report_md(result, out_dir):
    pass # placeholder for now
