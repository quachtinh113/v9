import os
import json
import csv
from pathlib import Path

def main():
    proj_dir = Path("c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_gbpusd")
    reports_dir = proj_dir / "reports"
    
    # 1. Inspect training_audit/GBPUSD_audit.json
    audit_json = reports_dir / "training_audit" / "GBPUSD_audit.json"
    if audit_json.exists():
        print(f"\n--- training_audit/GBPUSD_audit.json ---")
        try:
            with open(audit_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Top-level keys: {list(data.keys())}")
                if "training_metrics" in data:
                    print(f"training_metrics keys: {list(data['training_metrics'].keys())}")
                # Print some other interesting keys
                for k, v in data.items():
                    if not isinstance(v, (dict, list)):
                        print(f"  {k}: {v}")
                    else:
                        print(f"  {k} (length/keys): {len(v) if isinstance(v, list) else list(v.keys())}")
        except Exception as e:
            print(f"Error: {e}")
            
    # 2. Inspect latest/summary.json
    latest_sum = reports_dir / "latest" / "summary.json"
    if latest_sum.exists():
        print(f"\n--- latest/summary.json ---")
        try:
            with open(latest_sum, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error: {e}")
            
    # 3. Inspect latest/trade_log.csv
    trade_csv = reports_dir / "latest" / "trade_log.csv"
    if trade_csv.exists():
        print(f"\n--- latest/trade_log.csv ---")
        try:
            with open(trade_csv, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                print(f"Headers: {headers}")
                # Print first 3 rows
                for i in range(3):
                    try:
                        row = next(reader)
                        print(f"Row {i+1}: {row}")
                    except StopIteration:
                        break
        except Exception as e:
            print(f"Error: {e}")
            
    # 4. Inspect edge_discovery/GBPUSD_edge_discovery.json
    edge_json = reports_dir / "edge_discovery" / "GBPUSD_edge_discovery.json"
    if edge_json.exists():
        print(f"\n--- edge_discovery/GBPUSD_edge_discovery.json ---")
        try:
            with open(edge_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Top-level keys: {list(data.keys())}")
                if "setup_stats" in data:
                    print(f"setup_stats length: {len(data['setup_stats'])}")
                if "session_stats" in data:
                    print(f"session_stats length: {len(data['session_stats'])}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
