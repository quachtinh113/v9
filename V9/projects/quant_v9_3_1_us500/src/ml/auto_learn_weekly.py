from pathlib import Path
from src.ml.label_builder import build_labels
from src.ml.train_xgb_from_audit import train_model
from src.ml.validate_candidate_model import validate_candidate
from src.ml.promote_model import promote_if_better

def run_auto_learn():
    print("=== [AUTO LEARN] STARTING WEEKLY REFRESH ===")
    root = Path(__file__).resolve().parents[2]
    
    print("Step 1: Building Labels from Audit Log...")
    samples = build_labels(root / "logs" / "live_pipeline_audit.ndjson", root / "data" / "training_labels.csv")
    if not samples:
        print(">> No audit data found. Skipping.")
        return

    print(f"Step 2: Training Candidate Model ({samples} samples)...")
    success = train_model()
    if not success:
        print(">> Training failed (insufficient data?). Skipping.")
        return

    print("Step 3: Validating Candidate against Active...")
    report = validate_candidate()
    if not report:
        print(">> Validation failed. Skipping.")
        return
    
    print(f">> Metrics: Candidate AUC: {report['candidate_auc']:.4f}, Active AUC: {report['active_auc']:.4f}")

    print("Step 4: Evaluating Promotion Criteria...")
    promoted = promote_if_better(report)

    if promoted:
        print("✅ SUCCESS: Candidate model promoted to ACTIVE.")
    else:
        print("❌ REJECTED: Candidate did not meet performance or safety thresholds.")

    print("=== [AUTO LEARN] DONE ===")

if __name__ == "__main__":
    run_auto_learn()
