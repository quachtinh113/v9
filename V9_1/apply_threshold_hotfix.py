import os
from pathlib import Path

def patch_symbol_config(proj_dir):
    cfg_path = proj_dir / "config" / "symbol.yaml"
    if not cfg_path.exists():
        print(f"File not found: {cfg_path}")
        return False
        
    with open(cfg_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Standard replacement for block_threshold
    target_str = "  block_threshold: 0.55"
    replacement_str = "  block_threshold: 0.50"
    
    if target_str not in content:
        # Check if already patched
        if "  block_threshold: 0.50" in content:
            print(f"Already hotfixed block_threshold in {proj_dir.name}")
            return True
        print(f"Could not find block_threshold: 0.55 in {proj_dir.name}/config/symbol.yaml")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched config/symbol.yaml in {proj_dir.name} successfully.")
    return True

def patch_signal_engine(proj_dir):
    engine_path = proj_dir / "src" / "core" / "signal_engine.py"
    if not engine_path.exists():
        print(f"File not found: {engine_path}")
        return False
        
    with open(engine_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    target_str = '''    # Enforce ML Gatekeeper
    ml_cfg = dict(cfg.get("ml", {}))'''
    
    replacement_str = '''    # Store raw strategy direction before ML Gatekeeper overwrites it
    dec.raw_signal = dec.direction
    
    # Enforce ML Gatekeeper
    ml_cfg = dict(cfg.get("ml", {}))'''
    
    if target_str not in content:
        if "dec.raw_signal = dec.direction" in content:
            print(f"Already hotfixed raw_signal in {proj_dir.name}")
            return True
        print(f"Could not find target block in {proj_dir.name}/src/core/signal_engine.py")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(engine_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched src/core/signal_engine.py in {proj_dir.name} successfully.")
    return True

def patch_pipeline_live(proj_dir):
    pipe_path = proj_dir / "src" / "pipeline_live.py"
    if not pipe_path.exists():
        print(f"File not found: {pipe_path}")
        return False
        
    with open(pipe_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    target_str = '''        # ------------------ DIAGNOSTIC MODE SUMMARY ------------------
        import os
        if os.getenv("DIAGNOSTIC_MODE", "false").lower() == "true":
            risk_act = risk_decision.action if risk_decision else "N/A"
            risk_reasons = risk_decision.reasons if risk_decision else []
            final_act = "ORDER_SENT" if res else ("BLOCKED_BY_RISK" if (risk_act != "ALLOW" and risk_act != "N/A") else f"BLOCKED_BY_SIGNAL")
            all_blocks = decision.blocked_reasons + risk_reasons
            
            tf = self.config.get("profile", {}).get("trigger_timeframe", "M5")
            rsi_val = row.get("rsi14_m15", 0.0)
            adx_val = row.get("adx14_h1", 0.0)
            atr_val = row.get("atr14_m1", 0.001)
            bias_val = row.get("bias", "flat")
            
            print(f"[DIAGNOSTIC] symbol={self.symbol} | timeframe={tf} | rsi_fast={rsi_val:.2f} | rsi_slow=N/A | adx={adx_val:.2f} | atr={atr_val:.6f} | regime={decision.regime} | trend_bias={bias_val} | raw_signal={decision.direction} | signal_score={decision.score:.0f} | ml_score={decision.ml_score:.4f} | ml_decision={decision.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={all_blocks}")'''
            
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
            
            print(f"[DIAGNOSTIC] symbol={self.symbol} | timestamp={ts_val} | regime={decision.regime} | raw_signal={raw_sig} | signal_score={decision.score:.0f} | ml_score={decision.ml_score:.4f} | ml_threshold={ml_thresh:.2f} | ml_decision={decision.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={all_blocks}")'''

    if target_str not in content:
        # Check if already patched
        if "ml_threshold=" in content:
            print(f"Already hotfixed pipeline_live.py diagnostics in {proj_dir.name}")
            return True
        print(f"Could not find diagnostic block in {proj_dir.name}/src/pipeline_live.py")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(pipe_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched src/pipeline_live.py in {proj_dir.name} successfully.")
    return True

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    patched_cfg = 0
    patched_eng = 0
    patched_pipe = 0
    
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            if patch_symbol_config(proj):
                patched_cfg += 1
            if patch_signal_engine(proj):
                patched_eng += 1
            if patch_pipeline_live(proj):
                patched_pipe += 1
                
    print(f"\nHotfix Succeeded: {patched_cfg} configs, {patched_eng} engines, {patched_pipe} pipelines patched.")

if __name__ == "__main__":
    main()
