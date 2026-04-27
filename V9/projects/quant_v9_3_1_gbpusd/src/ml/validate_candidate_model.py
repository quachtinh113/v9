import pandas as pd
import xgboost as xgb
from pathlib import Path
from src.ml.xgb_filter import FEATURE_NAMES
from sklearn.metrics import roc_auc_score

def validate_candidate():
    root = Path(__file__).resolve().parents[2]
    data_path = root / "data" / "training_labels.csv"
    active_path = root / "models" / "active" / "xgb_trade_filter.json"
    candidate_path = root / "models" / "candidate" / "xgb_meta_filter_candidate.json"
    
    if not candidate_path.exists() or not data_path.exists(): return None
    
    df = pd.read_csv(data_path)
    X = df[FEATURE_NAMES]
    y = df['target']
    deval = xgb.DMatrix(X)
    
    # Candidate Score
    bst_cand = xgb.Booster()
    bst_cand.load_model(str(candidate_path))
    y_cand = bst_cand.predict(deval)
    auc_cand = roc_auc_score(y, y_cand)
    
    # Active Score
    auc_active = 0.5
    if active_path.exists():
        bst_act = xgb.Booster()
        bst_act.load_model(str(active_path))
        y_act = bst_act.predict(deval)
        auc_active = roc_auc_score(y, y_act)
    
    report = {
        "candidate_auc": auc_cand,
        "active_auc": auc_active,
        "improvement": auc_cand - auc_active,
        "sample_size": len(df)
    }
    return report
