import json
import pandas as pd
from pathlib import Path

def build_labels(audit_path: Path, output_path: Path):
    if not audit_path.exists(): return None
    
    records = []
    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            try: records.append(json.loads(line))
            except: continue
    
    if not records: return None
    
    df = pd.DataFrame(records)
    # Target: 1 if profitable, 0 if loss (simplified based on execution_status or real PnL if available)
    # In a real institutional setup, we would join with trade results.
    # For now, we simulate labels from the audit trail for structural verification.
    df['target'] = (df['signal_score'] > 80).astype(int) # Placeholder logic
    
    # Feature names from xgb_filter.py
    from src.ml.xgb_filter import FEATURE_NAMES
    valid_ds = df.dropna(subset=FEATURE_NAMES + ['target'])
    valid_ds.to_csv(output_path, index=False)
    return len(valid_ds)

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    build_labels(root / "logs" / "live_pipeline_audit.ndjson", root / "data" / "training_labels.csv")
