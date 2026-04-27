import pandas as pd
import xgboost as xgb
from pathlib import Path
from src.ml.xgb_filter import FEATURE_NAMES

def train_model():
    root = Path(__file__).resolve().parents[2]
    data_path = root / "data" / "training_labels.csv"
    if not data_path.exists(): return False
    
    df = pd.read_csv(data_path)
    if len(df) < 100: return False # Minimum sample check
    
    X = df[FEATURE_NAMES]
    y = df['target']
    
    dtrain = xgb.DMatrix(X, label=y)
    bst = xgb.train({"objective": "binary:logistic", "eval_metric": "auc"}, dtrain, 50)
    
    candidate_path = root / "models" / "candidate" / "xgb_meta_filter_candidate.json"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    bst.save_model(str(candidate_path))
    return True

if __name__ == "__main__":
    train_model()
