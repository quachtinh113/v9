import os
import json
from pathlib import Path
import numpy as np

def analyze_symbol_alpha(json_path):
    print(f"\nParsing alpha data: {json_path.name}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    ranking = data.get("ranking_distribution", {})
    print(f"Ranking distribution: {ranking}")
    
    edge_analysis = data.get("edge_analysis", [])
    print("Edge analysis setups:")
    for edge in edge_analysis:
        print(f"  Regime: {edge.get('regime')} | Dir: {edge.get('direction')} | Total Signals: {edge.get('total_signals')} | Executed: {edge.get('executed')} | Net PnL: {edge.get('net_pnl')}")

def analyze_raw_signals_log(proj_dir):
    alpha_json_path = proj_dir / "reports" / "alpha_research" / f"{proj_dir.name.split('_')[-1].upper()}_alpha.json"
    if not alpha_json_path.exists():
        print(f"No alpha report found at {alpha_json_path}")
        return
        
    with open(alpha_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"\n--- Detailed Logs Analysis for {proj_dir.name} ---")
    
    # Wait, does the JSON contain a detailed signals_log?
    # Let's check keys in the JSON
    print(f"Top level keys in {alpha_json_path.name}: {list(data.keys())}")
    
    # Wait! If the JSON report doesn't save the full raw list, let's see if there is another source, 
    # or let's read the logs to see if there is a signals_log or similar file in the folder.
    # Ah, in AlphaResearchFilter.finalize_analysis in alpha_filter.py:
    # it saves the `report` but does it save the raw signals list? 
    # Yes, it says: "report = { ...ranking_distribution, edge_analysis }" 
    # Let's check if the raw signals logs were saved or if they can be gathered from the backtest run.
    # Let's search if there's any file named like '*signals*.json' or '*trades*.json' in logs/ or reports/
    logs_dir = proj_dir / "logs"
    reports_dir = proj_dir / "reports"
    print(f"Scanning reports/ directory:")
    for f in reports_dir.rglob("*"):
        if f.is_file():
            print(f"  - {f.relative_to(reports_dir)} ({f.stat().st_size} bytes)")
            
def main():
    proj_dir = Path("c:/Quant Trade/v9/V9_1/projects/quant_v9_3_1_gbpusd")
    analyze_symbol_alpha(proj_dir / "reports" / "alpha_research" / "GBPUSD_alpha.json")
    analyze_raw_signals_log(proj_dir)

if __name__ == "__main__":
    main()
