"""Smoke test: verify all pipeline stages import and run correctly."""
import sys
sys.path.insert(0, r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd")

print("=" * 60)
print("  SMOKE TEST: Quant v9.3.1 GBPUSD Pipeline")
print("=" * 60)

# Test 1: DATA stage
print("\n[1/5] DATA: Loading CSV...")
from src.data.loaders import load_ohlcv_csv, validate_ohlcv
df = load_ohlcv_csv(r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd\data\raw\GBPUSD_M1_sample.csv")
diag = validate_ohlcv(df)
print(f"  Loaded {len(df)} rows | clean={diag['clean']} | issues={diag['issues']}")

# Test 2: FEATURE stage
print("\n[2/5] FEATURE: Building feature table...")
from src.data.mtf_builder import build_feature_table
ft = build_feature_table(df)
print(f"  Feature table: {len(ft)} rows x {len(ft.columns)} cols")
expected_cols = ["bias_h4", "macd_hist_m15", "bb_width_m15", "session_flag", "hour_sin", "hour_cos"]
for col in expected_cols:
    assert col in ft.columns, f"Missing column: {col}"
print(f"  All expected columns present: {expected_cols}")

# Test 3: REGIME + SIGNAL + AI FILTER + POSITION
print("\n[3/5] REGIME -> SIGNAL -> AI FILTER -> POSITION...")
from src.strategies.gbpusd_strategy import generate_trade_plan
from src.utils.config import load_yaml
config = load_yaml(r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd\config\symbol.yaml")
row = ft.iloc[-1].to_dict()
plan, decision = generate_trade_plan(row, config)
print(f"  Decision: dir={decision.direction} score={decision.score:.1f} regime={decision.regime}")
print(f"  ML: score={decision.ml_score:.2f} decision={decision.ml_decision}")
if plan:
    print(f"  Plan: entry={plan.entry:.5f} SL={plan.stop_loss:.5f} TP={plan.take_profit:.5f} layers={len(plan.layers)}")
else:
    print(f"  Plan: None (signal was flat)")

# Test 4: RISK gateway
print("\n[4/5] RISK: Testing RiskGateway...")
from src.core.risk_engine import RiskGateway
risk_cfg = load_yaml(r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd\config\risk.yaml")
gateway = RiskGateway(risk_cfg)
# Test ALLOW
rd = gateway.full_gate(
    {"daily_dd_pct": 0.5, "weekly_dd_pct": 1.0, "loss_streak": 1, "open_positions": 0},
    {"session_flag": "london", "spread": 1.0, "atr_ratio": 1.2},
)
print(f"  Normal conditions: action={rd.action} reasons={rd.reasons}")
assert rd.action == "ALLOW"

# Test SOFT_BLOCK
rd2 = gateway.full_gate(
    {"daily_dd_pct": 3.0, "weekly_dd_pct": 5.0, "loss_streak": 4, "open_positions": 0},
    {"session_flag": "london", "spread": 1.0, "atr_ratio": 1.2},
)
print(f"  High risk conditions: action={rd2.action} reasons={rd2.reasons}")
assert rd2.action == "SOFT_BLOCK"

# Test HARD_KILL
rd3 = gateway.full_gate(
    {"daily_dd_pct": 9.0, "weekly_dd_pct": 9.0, "loss_streak": 0, "open_positions": 0},
    {"session_flag": "london", "spread": 1.0, "atr_ratio": 1.0},
)
print(f"  Hard kill conditions: action={rd3.action} reasons={rd3.reasons}")
assert rd3.action == "HARD_KILL"

# Test 5: AUDIT
print("\n[5/5] AUDIT: Testing PipelineAuditLog...")
from src.execution.trade_journal import PipelineAuditLog
import tempfile, os
from pathlib import Path
audit_path = Path(r"d:\05_Quant\quant_v9_3_1_repos\quant_v9_3_1_gbpusd\logs\test_audit.ndjson")
audit = PipelineAuditLog(audit_path)
audit.write_tick(
    bar_ts="2025-01-01T00:00:00",
    regime="trend", regime_confidence=0.85,
    signal_direction="long", signal_score=78.0,
    ml_score=0.72, ml_decision="PASS",
    risk_action="ALLOW", risk_reasons=["all_clear"],
    execution_status="paper_only", position_size=0.02,
)
print(f"  Audit log written to {audit_path}")
# Verify file exists and has content
assert audit_path.exists()
content = audit_path.read_text()
assert "trend" in content
print(f"  Audit log verified ({len(content)} bytes)")

print("\n" + "=" * 60)
print("  ALL SMOKE TESTS PASSED ✓")
print("=" * 60)
