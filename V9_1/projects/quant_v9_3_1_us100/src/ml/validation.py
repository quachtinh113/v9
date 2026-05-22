import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
try:
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
    from sklearn.model_selection import TimeSeriesSplit
except ImportError:
    # Fallback if scikit-learn is missing
    pass
try:
    import xgboost as xgb
except ImportError:
    xgb = None

def simulate_financials(y_true, y_pred) -> Dict[str, Any]:
    initial_capital = 100000.0
    pnl = []
    # Win = +0.5% of capital ($500), Loss = -0.25% of capital (-$250)
    for t, p in zip(y_true, y_pred):
        if p == 1:
            if t == 1:
                pnl.append(0.005 * initial_capital)
            else:
                pnl.append(-0.0025 * initial_capital)
        else:
            pnl.append(0.0)
            
    equity = initial_capital + np.cumsum(pnl)
    peaks = np.maximum.accumulate(equity)
    drawdowns = (peaks - equity) / peaks * 100
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
    
    wins = sum(1 for x in pnl if x > 0)
    wins_sum = sum(x for x in pnl if x > 0)
    losses_sum = sum(abs(x) for x in pnl if x < 0)
    
    profit_factor = wins_sum / losses_sum if losses_sum > 0 else float('inf')
    total_trades = sum(1 for x in pnl if x != 0)
    winrate = wins / total_trades if total_trades > 0 else 0
    
    return {
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "winrate": winrate,
        "avg_trade_duration": "4h (Simulated)"
    }

def walk_forward_validation(df: pd.DataFrame, feature_names: list, n_splits: int = 3) -> Dict[str, Any]:
    if xgb is None:
        return {}
        
    tscv = TimeSeriesSplit(n_splits=n_splits)
    X = df[feature_names].values
    y = df['label'].values
    
    val_metrics = []
    train_metrics_list = []
    global_regime_stats = {}
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
        
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_names)
        dtest = xgb.DMatrix(X_test, feature_names=feature_names)
        
        bst = xgb.train({"objective": "binary:logistic"}, dtrain, 20)
        
        # Predict on validation
        preds_prob = bst.predict(dtest)
        preds = (preds_prob > 0.5).astype(int)
        
        # Predict on train
        preds_train_prob = bst.predict(dtrain)
        preds_train = (preds_train_prob > 0.5).astype(int)
        
        # Collect regimes for this split
        if 'regime' in df.columns:
            test_regimes = df.iloc[test_index]['regime'].values
            for reg, t, p in zip(test_regimes, y_test, preds):
                if reg not in global_regime_stats:
                    global_regime_stats[reg] = {"wins": 0, "total": 0}
                if p == 1:
                    global_regime_stats[reg]["total"] += 1
                    if t == 1:
                        global_regime_stats[reg]["wins"] += 1
        
        try:
            val_f1 = f1_score(y_test, preds)
            train_f1 = f1_score(y_train, preds_train)
            
            val_metrics.append({
                "precision": precision_score(y_test, preds, zero_division=0),
                "recall": recall_score(y_test, preds, zero_division=0),
                "f1_score": val_f1,
                "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
                "financials": simulate_financials(y_test, preds)
            })
            train_metrics_list.append(train_f1)
        except NameError:
            # sklearn not available
            val_metrics.append({
                "precision": 0, "recall": 0, "f1_score": 0, "confusion_matrix": [],
                "financials": simulate_financials(y_test, preds)
            })
            train_metrics_list.append(0)

    # Average the metrics from the last split for simplicity, or overall average
    latest_val = val_metrics[-1]
    latest_train_f1 = train_metrics_list[-1]
    
    overfitting_delta = latest_train_f1 - latest_val.get("f1_score", 0)
    overfitting_detected = overfitting_delta > 0.15
    
    regimes = df['regime'].value_counts().to_dict() if 'regime' in df.columns else {"N/A": len(df)}
    
    best_regime = "N/A"
    worst_regime = "N/A"
    best_wr = -1.0
    worst_wr = 2.0
    
    for reg, stats in global_regime_stats.items():
        if stats["total"] > 0:
            wr = stats["wins"] / stats["total"]
            if wr > best_wr:
                best_wr = wr
                best_regime = reg
            if wr < worst_wr:
                worst_wr = wr
                worst_regime = reg
                
    f1s = [m.get("f1_score", 0) for m in val_metrics]
    stability = 1.0 - float(np.std(f1s)) if len(f1s) > 1 else 1.0
    stability = max(0.0, min(1.0, stability))
    
    return {
        "overfitting_detected": bool(overfitting_detected),
        "train_f1_score": latest_train_f1,
        "stability_score": stability,
        "best_regime": best_regime,
        "worst_regime": worst_regime,
        "validation_metrics": {
            "winrate": latest_val["financials"]["winrate"],
            "precision": latest_val["precision"],
            "recall": latest_val["recall"],
            "f1_score": latest_val["f1_score"],
            "confusion_matrix": latest_val["confusion_matrix"]
        },
        "financial_metrics": {
            "max_drawdown": latest_val["financials"]["max_drawdown"],
            "profit_factor": latest_val["financials"]["profit_factor"],
            "avg_trade_duration": latest_val["financials"]["avg_trade_duration"]
        },
        "regime_distribution": regimes
    }
