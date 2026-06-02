import os
import yaml
from pathlib import Path

def check_fleet():
    root_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    symbols = ["gbpusd", "eurusd", "usdjpy", "audusd", "usdcad", "usdchf", "us30", "us100", "us500", "xauusd", "btcusd"]
    
    print(f"{'Bot':<10} | {'Launcher':<30} | {'Account':<20} | {'Status':<15} | {'Safe To Start':<15}")
    print("-" * 100)
    
    all_safe = True
    
    for sym in symbols:
        proj_dir = root_dir / f"quant_v9_3_1_{sym}"
        
        if not proj_dir.exists():
            print(f"{sym:<10} | {'NOT FOUND':<30} | {'N/A':<20} | {'FAIL':<15} | {'NO':<15}")
            all_safe = False
            continue
            
        if sym == "btcusd":
            launcher = proj_dir / "run_btcusd_pipeline.py"
            launcher_name = "run_btcusd_pipeline.py"
        else:
            launcher = proj_dir / "src" / "main.py"
            launcher_name = "src/main.py"
            
        if not launcher.exists():
            launcher_status = "FAIL (Missing)"
            safe = "NO"
        else:
            launcher_status = launcher_name
            safe = "YES"
            
        account_type = "UNKNOWN"
        demo_config = proj_dir / "configs" / "mt5_demo.yaml"
        if not demo_config.exists():
            demo_config = proj_dir / "config" / "mt5_demo.yaml"
            
        if demo_config.exists():
            with open(demo_config, 'r') as f:
                try:
                    cfg = yaml.safe_load(f)
                    server = cfg.get("mt5", {}).get("server", "")
                    if "trial" in server.lower() or "demo" in server.lower():
                        account_type = "DEMO"
                    else:
                        account_type = server if server else "UNKNOWN"
                except:
                    pass
        
        status = "PASS"
        if account_type.upper() == "LIVE" or "REAL" in account_type.upper():
            status = "FAIL (LIVE)"
            safe = "NO"
            
        if launcher_status.startswith("FAIL"):
            status = "FAIL (Launcher)"
            
        symbol_yaml = proj_dir / "configs" / "symbol.yaml"
        if not symbol_yaml.exists():
            symbol_yaml = proj_dir / "config" / "symbol.yaml"
            
        if symbol_yaml.exists():
            with open(symbol_yaml, 'r') as f:
                try:
                    scfg = yaml.safe_load(f)
                    mapped_sym = scfg.get("symbol", "")
                    if mapped_sym.lower() != sym.lower():
                        status = "FAIL (Symbol mismatch)"
                        safe = "NO"
                    
                    risk = scfg.get("risk", {})
                    if not risk:
                        status = "FAIL (No Risk block)"
                        safe = "NO"
                except:
                    pass
        else:
            status = "FAIL (No symbol config)"
            safe = "NO"
            
        if safe == "NO":
            all_safe = False
            
        print(f"{sym:<10} | {launcher_status:<30} | {account_type.upper():<20} | {status:<15} | {safe:<15}")

    print("\nOVERALL SAFE TO START:", "PASS" if all_safe else "FAIL")

if __name__ == "__main__":
    check_fleet()
