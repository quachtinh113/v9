import shutil
from pathlib import Path
import datetime

def promote_if_better(report):
    if not report: return False
    
    # Strict promotion criteria
    if (report["candidate_auc"] > report["active_auc"] + 0.02) and (report["sample_size"] >= 100):
        root = Path(__file__).resolve().parents[2]
        active_path = root / "models" / "active" / "xgb_trade_filter.json"
        candidate_path = root / "models" / "candidate" / "xgb_meta_filter_candidate.json"
        archive_dir = root / "models" / "archive"
        
        # Archive current active
        if active_path.exists():
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.move(active_path, archive_dir / f"xgb_trade_filter_{ts}.json")
            
        # Promote candidate
        shutil.copy(candidate_path, active_path)
        return True
    return False
