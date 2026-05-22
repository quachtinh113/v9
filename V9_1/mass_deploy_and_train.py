import os
import shutil
import sys
from pathlib import Path
import yaml
import subprocess

PROJECTS_DIR = Path(__file__).resolve().parent / "projects"
SOURCE_REPO = PROJECTS_DIR / "quant_v9_3_1_us30"

SYMBOLS = {
    "GBPUSD": {"type": "forex", "mt5_symbol": "GBPUSDm"},
    "EURUSD": {"type": "forex", "mt5_symbol": "EURUSDm"},
    "USDJPY": {"type": "forex", "mt5_symbol": "USDJPYm"},
    "AUDUSD": {"type": "forex", "mt5_symbol": "AUDUSDm"},
    "USDCAD": {"type": "forex", "mt5_symbol": "USDCADm"},
    "USDCHF": {"type": "forex", "mt5_symbol": "USDCHFm"},
    "US30":   {"type": "index", "mt5_symbol": "US30m"},
    "US100":  {"type": "index", "mt5_symbol": "USTEC"},
    "US500":  {"type": "index", "mt5_symbol": "US500m"},
    "XAUUSD": {"type": "gold",  "mt5_symbol": "XAUUSDm"},
}

def setup_repo(symbol, data):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = PROJECTS_DIR / repo_name
    print(f"\n--- Setting up {symbol} at {target_path} ---")
    
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory {target_path}")

    # Sync source code (src, config)
    if target_path != SOURCE_REPO:
        for folder in ["src", "config"]:
            src_folder = SOURCE_REPO / folder
            dst_folder = target_path / folder
            if dst_folder.exists():
                shutil.rmtree(dst_folder)
            shutil.copytree(src_folder, dst_folder)
    
    (target_path / "models").mkdir(exist_ok=True)
    (target_path / "logs").mkdir(exist_ok=True)
    (target_path / "reports").mkdir(exist_ok=True)
    (target_path / "data" / "raw").mkdir(parents=True, exist_ok=True)

    # Update symbol.yaml
    config_path = target_path / "config" / "symbol.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['symbol'] = symbol
        if data['type'] == 'index':
            config['entry']['trend_adx_min'] = 25
            config['position']['stop_atr_mult'] = 1.8
            config['position']['tp_atr_mult'] = 2.5
        elif data['type'] == 'gold':
            config['entry']['trend_adx_min'] = 28
            config['position']['stop_atr_mult'] = 2.0
            config['position']['tp_atr_mult'] = 3.0
        else: # forex
            config['entry']['trend_adx_min'] = 22
            config['position']['stop_atr_mult'] = 1.4
            config['position']['tp_atr_mult'] = 2.2
            
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

    # Rename strategy
    strategy_dir = target_path / "src" / "strategies"
    for file in strategy_dir.glob("*_strategy.py"):
        if file.name != f"{symbol.lower()}_strategy.py":
            content = file.read_text()
            content = content.replace('"US30"', f'"{symbol}"')
            content = content.replace('us30_strategy', f'{symbol.lower()}_strategy')
            (strategy_dir / f"{symbol.lower()}_strategy.py").write_text(content)
            file.unlink()

    print(f"Setup complete for {symbol}")

def train_repo(symbol):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = PROJECTS_DIR / repo_name
    print(f"\n--- Training {symbol} ---")
    
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(target_path)
        
        cmd = [sys.executable, "-m", "src.main", "--mode", "train"]
        result = subprocess.run(cmd, cwd=target_path, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Training SUCCESS for {symbol}")
            lines = result.stdout.splitlines()
            if lines: print(lines[-1])
        else:
            print(f"Training FAILED for {symbol}")
            print(result.stderr)
            print(result.stdout)
    except Exception as e:
        print(f"Error training {symbol}: {e}")

def generate_consolidated_summary():
    import json
    import csv
    from datetime import datetime
    
    summary_dir = Path(__file__).resolve().parent / "reports" / "final_quant_v9_summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    summary_data = []
    
    for sym in SYMBOLS.keys():
        repo_name = f"quant_v9_3_1_{sym.lower()}"
        audit_file = PROJECTS_DIR / repo_name / "reports" / "training_audit" / f"{sym}_audit.json"
        
        if audit_file.exists():
            try:
                with open(audit_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                val_met = data.get("validation_metrics", {})
                fin_met = data.get("financial_metrics", {})
                
                pf = fin_met.get("profit_factor", 0.0)
                wr = val_met.get("winrate", 0.0)
                dd = fin_met.get("max_drawdown", 0.0)
                stability = data.get("stability_score", 1.0)
                overfitting = data.get("overfitting_detected", False)
                
                # Calculate risk-adjusted score: (PF * WR) / (DD + 0.1)
                risk_adj = (pf * wr) / (dd + 0.1)
                
                # Classification
                if pf >= 1.6 and wr >= 0.55 and dd <= 2.0 and not overfitting:
                    verdict = "PRODUCTION_READY"
                elif pf >= 1.2 and wr >= 0.45 and dd <= 5.0 and not overfitting:
                    verdict = "PAPER_TRADE_ONLY"
                elif pf >= 1.0 or overfitting:
                    verdict = "RESEARCH_ONLY"
                else:
                    verdict = "DISABLED"
                    
                summary_data.append({
                    "symbol": sym,
                    "PF": pf,
                    "WR": wr,
                    "DD": dd,
                    "stability": stability,
                    "risk_adjusted_score": risk_adj,
                    "best_regime": data.get("best_regime", "N/A"),
                    "worst_regime": data.get("worst_regime", "N/A"),
                    "overfitting_warning": "YES" if overfitting else "NO",
                    "verdict": verdict
                })
            except Exception as e:
                print(f"Error parsing audit for {sym}: {e}")
        else:
            print(f"Audit file not found for {sym}: {audit_file}")
            
    if not summary_data:
        print("No audit data found. Cannot generate consolidated summary.")
        return
        
    # Rank symbols by risk adjusted score desc
    summary_data.sort(key=lambda x: x["risk_adjusted_score"], reverse=True)
    
    # Export JSON
    with open(summary_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=4)
        
    # Export CSV
    with open(summary_dir / "summary.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=summary_data[0].keys())
        writer.writeheader()
        writer.writerows(summary_data)
        
    # Export HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Consolidated Multi-Asset Audit Summary - Quant V9</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background-color: #f9f9f9; color: #333; }}
        h1, h2 {{ color: #111; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); background-color: #fff; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #fafafa; }}
        .verdict {{ font-weight: bold; padding: 4px 8px; border-radius: 4px; text-align: center; display: inline-block; }}
        .PRODUCTION_READY {{ background-color: #d4edda; color: #155724; }}
        .PAPER_TRADE_ONLY {{ background-color: #fff3cd; color: #856404; }}
        .RESEARCH_ONLY {{ background-color: #d1ecf1; color: #0c5460; }}
        .DISABLED {{ background-color: #f8d7da; color: #721c24; }}
        .warning {{ color: #721c24; background-color: #f8d7da; padding: 2px 5px; border-radius: 3px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Consolidated Multi-Asset Audit Summary</h1>
    <h2>Quant V9 Institutional Intelligence Layer</h2>
    <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>PF</th>
                <th>WR</th>
                <th>DD</th>
                <th>Stability</th>
                <th>Risk-Adj Score</th>
                <th>Best Regime</th>
                <th>Worst Regime</th>
                <th>Overfitting</th>
                <th>Verdict</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for row in summary_data:
        overfitting_class = ' class="warning"' if row['overfitting_warning'] == 'YES' else ''
        html += f"""
            <tr>
                <td><b>{row['symbol']}</b></td>
                <td>{row['PF']:.2f}</td>
                <td>{row['WR']:.2%}</td>
                <td>{row['DD']:.2f}</td>
                <td>{row['stability']:.2f}</td>
                <td>{row['risk_adjusted_score']:.2f}</td>
                <td>{row['best_regime']}</td>
                <td>{row['worst_regime']}</td>
                <td{overfitting_class}>{row['overfitting_warning']}</td>
                <td><span class="verdict {row['verdict']}">{row['verdict']}</span></td>
            </tr>
        """
        
    html += """
        </tbody>
    </table>
</body>
</html>
    """
    
    with open(summary_dir / "summary.html", 'w', encoding='utf-8') as f:
        f.write(html)
        
    print(f"\n============================================================")
    print(f" CONSOLIDATED MULTI-ASSET AUDIT REPORT GENERATED SUCCESS")
    print(f" Location: {summary_dir}")
    print(f"============================================================")

if __name__ == "__main__":
    for sym, data in SYMBOLS.items():
        setup_repo(sym, data)
    
    print("\n" + "="*60)
    print("  MASS SETUP COMPLETE. STARTING MASS TRAINING...")
    print("="*60)
    
    for sym in SYMBOLS.keys():
        train_repo(sym)
        
    generate_consolidated_summary()
