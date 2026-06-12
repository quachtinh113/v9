import os
import json
import glob
from pathlib import Path
from datetime import datetime, timezone

def inspect_live_flow():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    print(f"\n============================================================")
    print(f"  LIVE SIGNAL MONITORING & VERIFICATION MATRIX (DEMO FORWARD)")
    print(f"============================================================\n")
    
    total_raw = 0
    total_ml_approved = 0
    total_ml_rejected = 0
    total_risk_vetoed = 0
    total_exec_ready = 0
    total_no_signal = 0
    
    symbol_freshness = {}
    top_block_reasons = {}
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            symbol = proj.name.split("_")[-1].upper()
            no_entry_path = proj / "logs" / "no_entry_audit.jsonl"
            hb_path = proj / "logs" / "heartbeat.jsonl"
            
            # 1. Check Heartbeat
            freshness = "OFFLINE"
            if hb_path.exists():
                try:
                    with open(hb_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            last_hb = json.loads(lines[-1].strip())
                            ts_str = last_hb.get("timestamp")
                            if ts_str:
                                # Safe parsing of Z and tz offsets
                                if ts_str.endswith("Z"):
                                    ts_str = ts_str[:-1] + "+00:00"
                                ts_str = ts_str.replace("+00:00+00:00", "+00:00")
                                ts = datetime.fromisoformat(ts_str)
                                age = (datetime.now(timezone.utc) - ts).total_seconds()
                                if age < 90:
                                    freshness = f"ONLINE (age {age:.1f}s)"
                                else:
                                    freshness = f"STALE (age {age:.1f}s)"
                except Exception as e:
                    freshness = f"ERROR ({str(e)})"
            symbol_freshness[symbol] = freshness
            
            # 2. Check Audit Logs
            if no_entry_path.exists():
                try:
                    with open(no_entry_path, "r", encoding="utf-8") as f:
                        for line in f:
                            row = json.loads(line.strip())
                            decision = row.get("decision", "flat")
                            reason_code = row.get("reason_code", "")
                            reason_text = row.get("reason_text", "")
                            
                            if decision in ("long", "short") or reason_code != "strategy_flat":
                                total_raw += 1
                                if "ML_gatekeeper_block" in reason_text or reason_code == "ML_BLOCK":
                                    total_ml_rejected += 1
                                else:
                                    total_ml_approved += 1
                                    
                                if reason_code in ("SOFT_BLOCK", "HARD_KILL"):
                                    total_risk_vetoed += 1
                            else:
                                total_no_signal += 1
                                
                            if reason_text:
                                top_block_reasons[reason_text] = top_block_reasons.get(reason_text, 0) + 1
                except Exception as e:
                    pass
                    
    print(f"Asset Process Freshness Status:")
    for sym, fresh in symbol_freshness.items():
        print(f"  - {sym:<8}: {fresh}")
        
    print(f"\nLive Fleet Statistics Summary:")
    print(f"  - Total Raw Signals Generated  : {total_raw}")
    print(f"  - Total ML Filter Approvals    : {total_ml_approved}")
    print(f"  - Total ML Filter Rejections   : {total_ml_rejected}")
    print(f"  - Total Risk Engine Vetoes     : {total_risk_vetoed}")
    print(f"  - Total EXECUTION_READY Events : {total_exec_ready}")
    print(f"  - Total No-Signal States       : {total_no_signal}")
    
    if total_raw > 0:
        ml_approve_ratio = total_ml_approved / total_raw * 100
        print(f"  - ML Approval Ratio            : {ml_approve_ratio:.2f}%")
    else:
        print(f"  - ML Approval Ratio            : N/A (no signals)")
        
    print(f"\nTop Signal-Blocking Reasons:")
    sorted_reasons = sorted(top_block_reasons.items(), key=lambda x: x[1], reverse=True)
    for r, count in sorted_reasons[:5]:
        print(f"  - {r} (count: {count})")

if __name__ == "__main__":
    inspect_live_flow()
