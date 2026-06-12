import os
from pathlib import Path

def patch_signal_engine(proj_dir):
    engine_path = proj_dir / "src" / "core" / "signal_engine.py"
    if not engine_path.exists():
        print(f"File not found: {engine_path}")
        return False
        
    with open(engine_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    target_str = '''    elif regime == "sideway":
        # Mean reversion: trade opposite to direction or buy/sell based on RSI
        if rsi is not None:
            if rsi <= 35:
                direction = "long"
                direction_alignment_pass = True
            elif rsi >= 65:
                direction = "short"
                direction_alignment_pass = True
            else:
                blocked_reasons.append("rsi_neutral_in_sideway")
        else:
            blocked_reasons.append("missing_rsi_in_sideway")
    else:
        blocked_reasons.append(f"no_trade_in_regime_{regime}")'''
        
    replacement_str = '''    elif regime == "sideway":
        # Mean reversion: trade opposite to direction or buy/sell based on RSI
        if rsi is not None:
            if rsi <= 35:
                direction = "long"
                direction_alignment_pass = True
            elif rsi >= 65:
                direction = "short"
                direction_alignment_pass = True
            else:
                blocked_reasons.append("rsi_neutral_in_sideway")
        else:
            blocked_reasons.append("missing_rsi_in_sideway")
    elif regime == "transition":
        # Transition: trade emerging trend when enabled (align M15 and H1 bias)
        transition_allowed = cfg.get("risk", {}).get("transition_trade_enabled", False)
        if transition_allowed:
            if bias == bias_h1 and bias in ("long", "short"):
                direction = bias
                direction_alignment_pass = True
            else:
                blocked_reasons.append(f"transition_biases_mismatch_m15={bias}_h1={bias_h1}")
        else:
            blocked_reasons.append(f"no_trade_in_regime_{regime}")
    else:
        blocked_reasons.append(f"no_trade_in_regime_{regime}")'''

    if target_str not in content:
        # Check if already patched or slightly different spacing
        if "elif regime == \"transition\":" in content:
            print(f"Already patched in {proj_dir.name}")
            return True
        print(f"Could not find target string in {proj_dir.name}")
        return False
        
    new_content = content.replace(target_str, replacement_str)
    
    with open(engine_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched {proj_dir.name} successfully.")
    return True

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    patched_count = 0
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            if patch_signal_engine(proj):
                patched_count += 1
                
    print(f"Total patched: {patched_count} projects with transition trading logic.")

if __name__ == "__main__":
    main()
