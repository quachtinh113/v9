import os
import sys
import subprocess
from pathlib import Path
import time

def main():
    root_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    symbols = ["gbpusd", "eurusd", "usdjpy", "audusd", "usdcad", "usdchf", "us30", "us100", "us500", "xauusd", "btcusd"]
    
    print("============================================================")
    print("  LAUNCHING FLEET WITH UNBUFFERED TELEMETRY (11 AGENTS)")
    print("============================================================")
    
    runtime_mode = os.getenv("QUANT_RUNTIME_MODE", "paper").lower()
    if runtime_mode == "live":
        try:
            assert os.getenv("ALLOW_REAL_TRADING") == "true", "ALLOW_REAL_TRADING is not true"
            assert os.getenv("HUMAN_LIVE_CONFIRM") == "YES_I_ACCEPT_LIVE_RISK", "HUMAN_LIVE_CONFIRM is not YES_I_ACCEPT_LIVE_RISK"
            print("[SECURITY CHECK] Live mode authorized and verified.")
        except AssertionError as e:
            import json, sys
            from datetime import datetime, timezone
            global_log = Path("c:/Quant Trade/v9/V9_1/logs/live_pipeline_audit.ndjson")
            global_log.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": "PORTFOLIO",
                "stage": "EXECUTION",
                "reason_code": "LIVE_PERMISSION_NOT_CONFIRMED",
                "details": {"message": str(e)}
            }
            try:
                with open(global_log, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except:
                pass
            print(f"[CRITICAL] Live permission assertions failed: {e}. Execution blocked.")
            sys.exit(1)
    else:
        runtime_mode = "paper"

    # Enable Diagnostic Mode in environment
    env = os.environ.copy()
    env["DIAGNOSTIC_MODE"] = "true"
    env["PYTHONUNBUFFERED"] = "1"  # Also force via env var
    
    processes = []
    
    for sym in symbols:
        proj_dir = root_dir / f"quant_v9_3_1_{sym}"
        if not proj_dir.exists():
            print(f"Warning: Project directory {proj_dir.name} not found.")
            continue
            
        logs_dir = proj_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        stdout_file = open(logs_dir / "console_out.log", "w", encoding="utf-8")
        stderr_file = open(logs_dir / "console_err.log", "w", encoding="utf-8")
        
        print(f"Starting Agent [{sym.upper()}] background process (unbuffered, mode={runtime_mode})...")
        
        # Use literal "python" command and "-u" flag
        p = subprocess.Popen(
            ["python", "-u", "-m", "src.main", "--mode", runtime_mode],
            cwd=str(proj_dir),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        processes.append((sym.upper(), p, stdout_file, stderr_file))
        
    print("\nAll 11 agents successfully launched.")
    print("PIDs deployed:")
    for sym, p, _, _ in processes:
        print(f"  - {sym:<8}: PID {p.pid}")
        
    # Save the deployed PIDs to a file so we can clean them up later if needed
    pids_file = Path("c:/Quant Trade/v9/V9_1/logs/deployed_pids.json")
    pids_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pids_file, "w", encoding="utf-8") as f:
        import json
        json.dump({sym: p.pid for sym, p, _, _ in processes}, f, indent=4)
        
    print("\nFleet running in background. unbuffered log files active.")

if __name__ == "__main__":
    main()
