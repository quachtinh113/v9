import os
from pathlib import Path

def patch_pipeline_live(proj_dir):
    pipe_path = proj_dir / "src" / "pipeline_live.py"
    if not pipe_path.exists():
        print(f"File not found: {pipe_path}")
        return False
        
    with open(pipe_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # We find the diagnostic block to replace
    target_str = '''        # ------------------ DIAGNOSTIC MODE SUMMARY ------------------
        import os
        if os.getenv("DIAGNOSTIC_MODE", "false").lower() == "true":
            risk_act = risk_decision.action if risk_decision else "N/A"
            risk_reasons = risk_decision.reasons if risk_decision else []
            final_act = "ORDER_SENT" if res else ("BLOCKED_BY_RISK" if (risk_act != "ALLOW" and risk_act != "N/A") else f"BLOCKED_BY_SIGNAL")
            all_blocks = decision.blocked_reasons + risk_reasons
            
            ts_val = row.get("timestamp", "N/A")
            raw_sig = getattr(decision, "raw_signal", decision.direction)
            ml_thresh = self.config.get("ml", {}).get("block_threshold", 0.50)
            
            print(f"[DIAGNOSTIC] symbol={self.symbol} | timestamp={ts_val} | regime={decision.regime} | raw_signal={raw_sig} | signal_score={decision.score:.0f} | ml_score={decision.ml_score:.4f} | ml_threshold={ml_thresh:.2f} | ml_decision={decision.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={all_blocks}")'''

    replacement_str = '''        # ------------------ DIAGNOSTIC MODE SUMMARY ------------------
        import os
        if os.getenv("DIAGNOSTIC_MODE", "false").lower() == "true":
            risk_act = risk_decision.action if risk_decision else "N/A"
            risk_reasons = risk_decision.reasons if risk_decision else []
            final_act = "ORDER_SENT" if res else ("BLOCKED_BY_RISK" if (risk_act != "ALLOW" and risk_act != "N/A") else f"BLOCKED_BY_SIGNAL")
            all_blocks = decision.blocked_reasons + risk_reasons
            
            ts_val = row.get("timestamp", "N/A")
            raw_sig = getattr(decision, "raw_signal", decision.direction)
            ml_thresh = self.config.get("ml", {}).get("block_threshold", 0.50)
            
            # Extract indicators safely
            rsi_m15 = row.get("rsi14_m15", 0.0)
            adx_val = row.get("adx14_h1", 0.0)
            atr_val = row.get("atr14_m1", 0.001)
            
            print(f"[DIAGNOSTIC] symbol={self.symbol} | timestamp={ts_val} | regime={decision.regime} | rsi_m15={rsi_m15:.2f} | rsi_h1=N/A | rsi_h4=N/A | adx={adx_val:.2f} | atr={atr_val:.6f} | raw_signal={raw_sig} | signal_score={decision.score:.0f} | ml_score={decision.ml_score:.4f} | ml_threshold={ml_thresh:.2f} | ml_decision={decision.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={all_blocks}")'''

    if target_str not in content:
        # Check if already patched
        if "rsi_m15=" in content:
            print(f"Already expanded diagnostics in {proj_dir.name}")
            return True
        print(f"Could not find target diagnostic block in {proj_dir.name}/src/pipeline_live.py")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(pipe_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched src/pipeline_live.py in {proj_dir.name} successfully.")
    return True

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    patched_count = 0
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            if patch_pipeline_live(proj):
                patched_count += 1
                
    print(f"\nExpanded Telemetry Patched: {patched_count} pipelines updated.")

if __name__ == "__main__":
    main()
