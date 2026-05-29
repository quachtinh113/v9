import os
import json
from pathlib import Path
import psutil

def stop_fleet():
    pids_file = Path("c:/Quant Trade/v9/V9_1/logs/deployed_pids.json")
    if not pids_file.exists():
        print("No deployed PIDs file found.")
        return
        
    try:
        with open(pids_file, "r", encoding="utf-8") as f:
            pids = json.load(f)
            
        print("============================================================")
        print("  STOPPING INSTITUTIONAL MULTI-AGENT FLEET BACKGROUND WORKERS")
        print("============================================================\n")
        
        for sym, pid in pids.items():
            try:
                p = psutil.Process(pid)
                print(f"Terminating Agent [{sym}] (PID {pid})...")
                p.terminate()
                p.wait(timeout=3)
                print(f"  Stopped.")
            except psutil.NoSuchProcess:
                print(f"Agent [{sym}] (PID {pid}) was not running.")
            except Exception as e:
                print(f"  Error stopping [{sym}]: {e}")
                
        print("\nAll background workers stopped.")
        # Remove pids file
        try: os.remove(pids_file)
        except: pass
    except Exception as e:
        print(f"Error reading PIDs: {e}")

if __name__ == "__main__":
    stop_fleet()
