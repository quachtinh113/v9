import os
import sys
import subprocess
import json
import csv
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECTS_DIR = Path(__file__).resolve().parent / "projects"
SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]

def run_backtest(symbol):
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    target_path = PROJECTS_DIR / repo_name
    print(f"Running backtest for {symbol}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(target_path)
    
    cmd = [sys.executable, "-m", "src.main", "--mode", "backtest"]
    result = subprocess.run(cmd, cwd=target_path, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        realism_path = target_path / "reports" / "realism_engine" / f"{symbol}_realism.json"
        alpha_path = target_path / "reports" / "alpha_research" / f"{symbol}_alpha.json"
        edge_path = target_path / "reports" / "edge_discovery" / f"{symbol}_edge_discovery.json"
        
        data = {}
        if realism_path.exists():
            with open(realism_path, 'r', encoding='utf-8') as f:
                data["realism"] = json.load(f)
        if alpha_path.exists():
            with open(alpha_path, 'r', encoding='utf-8') as f:
                data["alpha"] = json.load(f)
        if edge_path.exists():
            with open(edge_path, 'r', encoding='utf-8') as f:
                data["edge"] = json.load(f)
        return data if data else None
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
        
    # Extract Realism Results
    realism_results = [r["realism"] for r in results if "realism" in r]
    if realism_results:
        df_real = pd.DataFrame(realism_results)
        df_real.sort_values(by="sharpe_ratio", ascending=False, inplace=True)
        
        print("\n" + "="*95)
        print("  LAYER 1: MULTI-ASSET REALISM ENGINE AUDIT REPORT (INSTITUTIONAL PIPELINE V9.3.1)")
        print("="*95)
        
        report_cols = ["symbol", "verdict", "profit_factor", "max_drawdown_pct", "sharpe_ratio", "monte_carlo_95_dd", "ruin_probability"]
        summary_table = df_real[report_cols].copy()
        summary_table["max_drawdown_pct"] = summary_table["max_drawdown_pct"].apply(lambda x: f"{x:.2f}%")
        summary_table["monte_carlo_95_dd"] = summary_table["monte_carlo_95_dd"].apply(lambda x: f"{x:.2f}%")
        summary_table["ruin_probability"] = summary_table["ruin_probability"].apply(lambda x: f"{x:.2%}")
        summary_table["profit_factor"] = summary_table["profit_factor"].apply(lambda x: f"{x:.2f}")
        summary_table["sharpe_ratio"] = summary_table["sharpe_ratio"].apply(lambda x: f"{x:.2f}")
        
        print(summary_table.to_string(index=False))
        print("="*95)
        
        # Save Realism Summary
        realism_export_dir = Path(__file__).resolve().parent / "reports" / "realism_engine"
        realism_export_dir.mkdir(parents=True, exist_ok=True)
        with open(realism_export_dir / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(realism_results, f, indent=4)
        df_real.to_csv(realism_export_dir / "summary.csv", index=False, encoding='utf-8')
        
    # Extract Alpha Research Results
    alpha_results = [r["alpha"] for r in results if "alpha" in r]
    if alpha_results:
        alpha_flat = []
        for r in alpha_results:
            ee = r["execution_efficiency"]
            rd = r["ranking_distribution"]
            alpha_flat.append({
                "symbol": r["symbol"],
                "total_trades": ee["total_trades"],
                "total_net_pnl": ee["total_net_pnl"],
                "expectancy": ee["expectancy_dollars"],
                "cost_adj_expectancy": ee["cost_adjusted_expectancy"],
                "rank_A_plus": rd.get("A+", 0),
                "rank_A": rd.get("A", 0),
                "rank_B": rd.get("B", 0),
                "rank_C": rd.get("C", 0),
                "rank_REJECT": rd.get("REJECT", 0)
            })
            
        df_alpha = pd.DataFrame(alpha_flat)
        df_alpha.sort_values(by="total_net_pnl", ascending=False, inplace=True)
        
        print("\n" + "="*95)
        print("  LAYER 2: MULTI-ASSET ALPHA RESEARCH SELECTIVE EXECUTION (INSTITUTIONAL PIPELINE V9.3.1)")
        print("="*95)
        
        alpha_cols = ["symbol", "total_trades", "total_net_pnl", "expectancy", "cost_adj_expectancy", "rank_A_plus", "rank_A", "rank_REJECT"]
        summary_alpha = df_alpha[alpha_cols].copy()
        summary_alpha["total_net_pnl"] = summary_alpha["total_net_pnl"].apply(lambda x: f"${x:,.2f}")
        summary_alpha["expectancy"] = summary_alpha["expectancy"].apply(lambda x: f"${x:,.2f}")
        summary_alpha["cost_adj_expectancy"] = summary_alpha["cost_adj_expectancy"].apply(lambda x: f"${x:,.2f}")
        
        print(summary_alpha.to_string(index=False))
        print("="*95)
        
        # Save Alpha Summary
        alpha_export_dir = Path(__file__).resolve().parent / "reports" / "alpha_research"
        alpha_export_dir.mkdir(parents=True, exist_ok=True)
        with open(alpha_export_dir / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(alpha_results, f, indent=4)
        df_alpha.to_csv(alpha_export_dir / "summary.csv", index=False, encoding='utf-8')
        
        # Generate Alpha Consolidated HTML Summary
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Consolidated Alpha Research Audit - Quant V9</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #0d1117; color: #c9d1d9; }}
        h1, h2 {{ color: #58a6ff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
        th, td {{ border: 1px solid #30363d; padding: 12px; text-align: left; }}
        th {{ background-color: #161b22; color: #f0f6fc; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #161b22; }}
    </style>
</head>
<body>
    <h1>Consolidated Alpha Research Report</h1>
    <h2>Quant V9 Institutional Selective Execution Layer</h2>
    <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Total Executed Trades</th>
                <th>Net PnL</th>
                <th>Expectancy</th>
                <th>Cost-Adjusted Expectancy</th>
                <th>A+ Count</th>
                <th>A Count</th>
                <th>B Count</th>
                <th>C Count</th>
                <th>REJECT Count</th>
            </tr>
        </thead>
        <tbody>
    """
        for _, row in df_alpha.iterrows():
            html += f"""
                <tr>
                    <td><b>{row['symbol']}</b></td>
                    <td>{row['total_trades']}</td>
                    <td>${row['total_net_pnl']:,.2f}</td>
                    <td>${row['expectancy']:,.2f}</td>
                    <td>${row['cost_adj_expectancy']:,.2f}</td>
                    <td>{row['rank_A_plus']}</td>
                    <td>{row['rank_A']}</td>
                    <td>{row['rank_B']}</td>
                    <td>{row['rank_C']}</td>
                    <td>{row['rank_REJECT']}</td>
                </tr>
            """
        html += """
        </tbody>
    </table>
</body>
</html>
        """
        with open(alpha_export_dir / "summary.html", 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"\nConsolidated Alpha Research Generated:")
        print(f" -> {alpha_export_dir / 'summary.json'}")
        print(f" -> {alpha_export_dir / 'summary.csv'}")
        print(f" -> {alpha_export_dir / 'summary.html'}")
        
    # Extract Edge Discovery Results
    edge_results = [r["edge"] for r in results if "edge" in r]
    if edge_results:
        edge_flat = []
        for r in edge_results:
            pm = r["portfolio_metrics"]
            ap = r["alpha_profile"]
            edge_flat.append({
                "symbol": r["symbol"],
                "verdict": pm["verdict"],
                "total_trades": pm["total_trades"],
                "net_pnl": pm["net_pnl"],
                "profit_factor": pm["profit_factor"],
                "sharpe_ratio": pm["sharpe_ratio"],
                "max_drawdown_pct": pm["max_drawdown_pct"],
                "monte_carlo_95_dd": pm["mc_worst_case_dd"],
                "ruin_probability": pm["ruin_probability"],
                "best_setup": ap.get("best_setup", "N/A"),
                "best_session": ap.get("best_session", "N/A"),
                "volatility_pref": ap.get("volatility_preference", "N/A")
            })
            
        df_edge = pd.DataFrame(edge_flat)
        df_edge.sort_values(by="net_pnl", ascending=False, inplace=True)
        
        print("\n" + "="*115)
        print("  LAYER 3: MULTI-ASSET EDGE DISCOVERY PORTFOLIO SUMMARY (INSTITUTIONAL PIPELINE V9.3.1)")
        print("="*115)
        
        edge_cols = ["symbol", "verdict", "total_trades", "net_pnl", "profit_factor", "sharpe_ratio", "monte_carlo_95_dd", "best_setup", "best_session"]
        summary_edge = df_edge[edge_cols].copy()
        summary_edge["net_pnl"] = summary_edge["net_pnl"].apply(lambda x: f"${x:,.2f}")
        summary_edge["monte_carlo_95_dd"] = summary_edge["monte_carlo_95_dd"].apply(lambda x: f"{x:.2f}%")
        summary_edge["profit_factor"] = summary_edge["profit_factor"].apply(lambda x: f"{x:.2f}")
        summary_edge["sharpe_ratio"] = summary_edge["sharpe_ratio"].apply(lambda x: f"{x:.2f}")
        
        print(summary_edge.to_string(index=False))
        print("="*115)
        
        # Save Edge Summary
        edge_export_dir = Path(__file__).resolve().parent / "reports" / "edge_discovery"
        edge_export_dir.mkdir(parents=True, exist_ok=True)
        with open(edge_export_dir / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(edge_results, f, indent=4)
        df_edge.to_csv(edge_export_dir / "summary.csv", index=False, encoding='utf-8')
        
        # Generate HTML visual summary for Edge Discovery
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Consolidated Edge Discovery Audit - Quant V9</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #0d1117; color: #c9d1d9; }}
        h1, h2 {{ color: #58a6ff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
        th, td {{ border: 1px solid #30363d; padding: 12px; text-align: left; }}
        th {{ background-color: #161b22; color: #f0f6fc; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #161b22; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .APPROVED {{ background-color: #238636; color: #ffffff; }}
        .DISABLED {{ background-color: #da3633; color: #ffffff; }}
    </style>
</head>
<body>
    <h1>Consolidated Edge Discovery Audit Report</h1>
    <h2>Quant V9 Layer 3 Edge Filtering Performance</h2>
    <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Verdict</th>
                <th>Trades</th>
                <th>Net PnL</th>
                <th>Profit Factor</th>
                <th>Sharpe Ratio</th>
                <th>Max DD</th>
                <th>MC 95% DD</th>
                <th>Ruin Prob</th>
                <th>Best Setup</th>
                <th>Best Session</th>
                <th>Volatility Pref</th>
            </tr>
        </thead>
        <tbody>
    """
        for _, row in df_edge.iterrows():
            html += f"""
                <tr>
                    <td><b>{row['symbol']}</b></td>
                    <td><span class="badge {row['verdict']}">{row['verdict']}</span></td>
                    <td>{row['total_trades']}</td>
                    <td>${row['net_pnl']:,.2f}</td>
                    <td>{row['profit_factor']:.2f}</td>
                    <td>{row['sharpe_ratio']:.2f}</td>
                    <td>{row['max_drawdown_pct']:.2f}%</td>
                    <td>{row['monte_carlo_95_dd']:.2f}%</td>
                    <td>{row['ruin_probability']:.2%}</td>
                    <td>{row['best_setup']}</td>
                    <td>{row['best_session']}</td>
                    <td>{row['volatility_pref']}</td>
                </tr>
            """
        html += """
        </tbody>
    </table>
</body>
</html>
        """
        with open(edge_export_dir / "summary.html", 'w', encoding='utf-8') as f:
            f.write(html)
            
        print(f"\nConsolidated Edge Discovery Generated:")
        print(f" -> {edge_export_dir / 'summary.json'}")
        print(f" -> {edge_export_dir / 'summary.csv'}")
        print(f" -> {edge_export_dir / 'summary.html'}")
