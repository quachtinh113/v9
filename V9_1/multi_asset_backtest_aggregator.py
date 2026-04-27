import os
import sys
import subprocess
import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(r"d:\V9\projects")
SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD"]

def run_backtest(symbol):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = REPO_ROOT / repo_name
    print(f"Running backtest for {symbol}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(target_path)
    
    cmd = [sys.executable, "-m", "src.main", "--mode", "backtest"]
    result = subprocess.run(cmd, cwd=target_path, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        # In our simplified main.py, it prints a summary. 
        # But we also have summary.json in reports/latest/
        summary_path = target_path / "reports" / "latest" / "summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                return json.load(f)
        else:
            # Fallback parsing from stdout if summary.json missing
            print(f"Warning: summary.json not found for {symbol}")
            return None
    else:
        print(f"Backtest FAILED for {symbol}")
        print(result.stderr)
        return None

if __name__ == "__main__":
    results = []
    for sym in SYMBOLS:
        res = run_backtest(sym)
        if res:
            results.append(res)
    
    if not results:
        print("No results to report.")
        sys.exit(1)
        
    df = pd.DataFrame(results)
    
    print("\n" + "="*80)
    print("  MULTI-ASSET BACKTEST REPORT (INSTITUTIONAL PIPELINE V9.3.1)")
    print("="*80)
    
    report_cols = ["symbol", "trades", "win_rate", "net_pnl", "profit_factor", "ending_equity"]
    # Filter only columns that exist
    report_cols = [c for c in report_cols if c in df.columns]
    
    summary_table = df[report_cols].copy()
    summary_table["win_rate"] = summary_table["win_rate"].apply(lambda x: f"{x:.2%}")
    summary_table["net_pnl"] = summary_table["net_pnl"].apply(lambda x: f"{x:,.2f}")
    summary_table["ending_equity"] = summary_table["ending_equity"].apply(lambda x: f"{x:,.2f}")
    
    print(summary_table.to_string(index=False))
    print("="*80)
    
    total_pnl = df["net_pnl"].sum()
    avg_win_rate = df["win_rate"].mean()
    total_trades = df["trades"].sum()
    
    print(f"TOTAL TRADES: {total_trades}")
    print(f"TOTAL NET PNL: {total_pnl:,.2f}")
    print(f"AVG WIN RATE: {avg_win_rate:.2%}")
    print("="*80)
