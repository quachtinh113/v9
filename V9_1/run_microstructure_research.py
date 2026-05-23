import os
import sys
import json
import csv
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Setup project import paths
V9_1_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = V9_1_DIR / "projects"
sys.path.insert(0, str(PROJECTS_DIR / "quant_v9_3_1_us30"))

from src.core.microstructure import MicrostructureDetector, simulate_expectancy

SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "US30", "US100", "US500", "XAUUSD", "BTCUSD"]

def load_symbol_data(symbol: str) -> pd.DataFrame:
    """Find and load the M1 CSV for a given symbol."""
    proj_dir = PROJECTS_DIR / f"quant_v9_3_1_{symbol.lower()}"
    raw_dir = proj_dir / "data" / "raw"
    
    if not raw_dir.exists():
        print(f"Directory not found: {raw_dir}")
        return None
        
    csv_files = list(raw_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV data found in {raw_dir}")
        return None
        
    # Load the first CSV file found
    csv_path = csv_files[0]
    print(f"Loading data for {symbol} from {csv_path.name}...")
    
    # Load and clean
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def classify_time_window(row) -> str:
    """Classify specific institutional timing windows."""
    hour = row["hour"]
    minute = row["minute"]
    time_val = hour * 60 + minute
    
    # 19h20/20h20 (19:20 - 20:20 UTC)
    if (19*60 + 20 <= time_val <= 20*60 + 20):
        return "19h20-20h20"
    # 21h30/22h30 (21:30 - 22:30 UTC)
    elif (21*60 + 30 <= time_val <= 22*60 + 30):
        return "21h30-22h30"
    # 23h30/24h30 (23:30 - 00:30 UTC)
    elif (23*60 + 30 <= time_val) or (time_val <= 30):
        return "23h30-00h30"
        
    return "Other"

def run_analysis_for_symbol(symbol: str) -> dict:
    df = load_symbol_data(symbol)
    if df is None or len(df) < 500:
        print(f"Skipping {symbol} due to insufficient data.")
        return None
        
    print(f"Running Microstructure Detection for {symbol} ({len(df)} bars)...")
    detector = MicrostructureDetector(df)
    res_df = detector.run_detection()
    
    # Apply specific timing window classification
    res_df["time_window"] = res_df.apply(classify_time_window, axis=1)
    
    print(f"Simulating standardized trade outcomes for {symbol}...")
    # Pre-calculate simulation results to avoid slow loops
    long_pnls = []
    short_pnls = []
    
    # Sampling for performance if data is massive, but for 10k bars we can do all of them
    for idx in range(len(res_df)):
        lp, _ = simulate_expectancy(res_df, idx, "long")
        sp, _ = simulate_expectancy(res_df, idx, "short")
        long_pnls.append(lp)
        short_pnls.append(sp)
        
    res_df["long_pnl_atr"] = long_pnls
    res_df["short_pnl_atr"] = short_pnls
    
    # Aggregate results
    stats = {
        "symbol": symbol,
        "total_bars": len(res_df),
        "sessions": {},
        "volatility_states": {},
        "liquidity_patterns": {},
        "time_windows": {}
    }
    
    # Helper to calculate stats
    def get_group_stats(df_group):
        if len(df_group) == 0:
            return {"count": 0, "long_expectancy": 0.0, "short_expectancy": 0.0, "long_winrate": 0.0, "short_winrate": 0.0}
        l_pnls = df_group["long_pnl_atr"].values
        s_pnls = df_group["short_pnl_atr"].values
        
        return {
            "count": int(len(df_group)),
            "long_expectancy": float(np.mean(l_pnls)),
            "short_expectancy": float(np.mean(s_pnls)),
            "long_winrate": float(np.mean(l_pnls > 0)),
            "short_winrate": float(np.mean(s_pnls > 0))
        }
        
    # Grouping by Session
    for name, group in res_df.groupby("session_type"):
        stats["sessions"][name] = get_group_stats(group)
        
    # Grouping by Volatility State
    for name, group in res_df.groupby("volatility_state"):
        stats["volatility_states"][name] = get_group_stats(group)
        
    # Grouping by Liquidity Pattern
    for name, group in res_df.groupby("liquidity_pattern"):
        stats["liquidity_patterns"][name] = get_group_stats(group)
        
    # Grouping by Time Window
    for name, group in res_df.groupby("time_window"):
        stats["time_windows"][name] = get_group_stats(group)
        
    # Add a top-level summary of the best timing and liquidity edges
    all_edges = []
    
    # Extract liquidity patterns
    for pat, pat_stats in stats["liquidity_patterns"].items():
        if pat == "None" or pat_stats["count"] < 3: continue
        all_edges.append(("liquidity", pat, "long", pat_stats["long_expectancy"], pat_stats["long_winrate"], pat_stats["count"]))
        all_edges.append(("liquidity", pat, "short", pat_stats["short_expectancy"], pat_stats["short_winrate"], pat_stats["count"]))
        
    # Extract time windows
    for tw, tw_stats in stats["time_windows"].items():
        if tw == "Other" or tw_stats["count"] < 3: continue
        all_edges.append(("time_window", tw, "long", tw_stats["long_expectancy"], tw_stats["long_winrate"], tw_stats["count"]))
        all_edges.append(("time_window", tw, "short", tw_stats["short_expectancy"], tw_stats["short_winrate"], tw_stats["count"]))
        
    # Rank edges by absolute expectancy
    all_edges.sort(key=lambda x: abs(x[3]), reverse=True)
    stats["top_edges"] = [
        {
            "category": edge[0],
            "trigger": edge[1],
            "direction": edge[2],
            "expectancy_atr": edge[3],
            "winrate": edge[4],
            "sample_size": edge[5]
        } for edge in all_edges[:5]
    ]
    
    # Save per-symbol data
    out_dir = V9_1_DIR / "reports" / "microstructure_research" / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / f"{symbol}_microstructure.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)
        
    # Save a small sample CSV of classified bars (last 1000 bars for size limit / detail view)
    res_df.tail(1000).to_csv(out_dir / f"{symbol}_microstructure_sample.csv", index=False)
    
    # Generate HTML report for this symbol
    generate_symbol_html_report(symbol, stats, out_dir / f"{symbol}_microstructure_report.html")
    
    return stats

def generate_symbol_html_report(symbol: str, stats: dict, file_path: Path):
    """Generate a premium visual HTML dashboard for a single asset's microstructure."""
    top_edges_html = ""
    for edge in stats.get("top_edges", []):
        dir_class = "APPROVED" if edge["expectancy_atr"] > 0 else "DISABLED"
        val_sign = "+" if edge["expectancy_atr"] > 0 else ""
        top_edges_html += f"""
        <div class="edge-card">
            <div class="edge-header">
                <span class="edge-cat">{edge['category'].upper()}</span>
                <span class="badge {dir_class}">{edge['direction'].upper()}</span>
            </div>
            <div class="edge-trigger">{edge['trigger']}</div>
            <div class="edge-metrics">
                <div>Expectancy: <b style="color: #38bdf8;">{val_sign}{edge['expectancy_atr']:.2f} ATR</b></div>
                <div>Win Rate: <b>{edge['winrate']:.1%}</b></div>
                <div>Samples: <b>{edge['sample_size']}</b></div>
            </div>
        </div>
        """
        
    sessions_rows = ""
    for k, v in stats["sessions"].items():
        sessions_rows += f"""
        <tr>
            <td><b>{k}</b></td>
            <td>{v['count']}</td>
            <td style="color: { '#10b981' if v['long_expectancy'] > 0 else '#ef4444' };">{v['long_expectancy']:.3f}</td>
            <td>{v['long_winrate']:.1%}</td>
            <td style="color: { '#10b981' if v['short_expectancy'] > 0 else '#ef4444' };">{v['short_expectancy']:.3f}</td>
            <td>{v['short_winrate']:.1%}</td>
        </tr>
        """
        
    vol_rows = ""
    for k, v in stats["volatility_states"].items():
        vol_rows += f"""
        <tr>
            <td><b>{k}</b></td>
            <td>{v['count']}</td>
            <td style="color: { '#10b981' if v['long_expectancy'] > 0 else '#ef4444' };">{v['long_expectancy']:.3f}</td>
            <td>{v['long_winrate']:.1%}</td>
            <td style="color: { '#10b981' if v['short_expectancy'] > 0 else '#ef4444' };">{v['short_expectancy']:.3f}</td>
            <td>{v['short_winrate']:.1%}</td>
        </tr>
        """
        
    liq_rows = ""
    for k, v in stats["liquidity_patterns"].items():
        liq_rows += f"""
        <tr>
            <td><b>{k}</b></td>
            <td>{v['count']}</td>
            <td style="color: { '#10b981' if v['long_expectancy'] > 0 else '#ef4444' };">{v['long_expectancy']:.3f}</td>
            <td>{v['long_winrate']:.1%}</td>
            <td style="color: { '#10b981' if v['short_expectancy'] > 0 else '#ef4444' };">{v['short_expectancy']:.3f}</td>
            <td>{v['short_winrate']:.1%}</td>
        </tr>
        """
        
    tw_rows = ""
    for k, v in stats["time_windows"].items():
        tw_rows += f"""
        <tr>
            <td><b>{k}</b></td>
            <td>{v['count']}</td>
            <td style="color: { '#10b981' if v['long_expectancy'] > 0 else '#ef4444' };">{v['long_expectancy']:.3f}</td>
            <td>{v['long_winrate']:.1%}</td>
            <td style="color: { '#10b981' if v['short_expectancy'] > 0 else '#ef4444' };">{v['short_expectancy']:.3f}</td>
            <td>{v['short_winrate']:.1%}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Microstructure Research - {symbol}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 30px;
        }}
        h1, h2, h3 {{
            color: #38bdf8;
            margin-top: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .edge-card {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }}
        .edge-card:hover {{
            transform: translateY(-5px);
        }}
        .edge-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .edge-cat {{
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            color: #94a3b8;
        }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }}
        .APPROVED {{ background-color: #065f46; color: #34d399; }}
        .DISABLED {{ background-color: #7f1d1d; color: #f87171; }}
        .edge-trigger {{
            font-size: 18px;
            font-weight: bold;
            color: #f8fafc;
            margin-bottom: 12px;
        }}
        .edge-metrics {{
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.6;
        }}
        .panel {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 35px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 14px;
            border-bottom: 1px solid #334155;
            text-align: left;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #0f172a;
        }}
        .chart-container {{
            position: relative;
            height: 350px;
            width: 100%;
            margin-top: 15px;
        }}
        .grid-2col {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Microstructure Timing & Liquidity Edge</h1>
                <h2 style="color: #94a3b8; font-weight: 400; font-size: 16px;">Asset Profile: {symbol}</h2>
            </div>
            <div>
                <span style="font-size: 13px; color: #64748b;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</span>
            </div>
        </div>
        
        <h2>Top Discovered Institutional Edges</h2>
        <div class="card-grid">
            {top_edges_html}
        </div>
        
        <div class="grid-2col">
            <div class="panel">
                <h2>Session Expectancy Profile</h2>
                <div class="chart-container">
                    <canvas id="sessionChart"></canvas>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Session</th>
                            <th>Count</th>
                            <th>Buy Exp (ATR)</th>
                            <th>Buy WR</th>
                            <th>Sell Exp (ATR)</th>
                            <th>Sell WR</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sessions_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="panel">
                <h2>Volatility State Expectancy</h2>
                <div class="chart-container">
                    <canvas id="volChart"></canvas>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Volatility State</th>
                            <th>Count</th>
                            <th>Buy Exp (ATR)</th>
                            <th>Buy WR</th>
                            <th>Sell Exp (ATR)</th>
                            <th>Sell WR</th>
                        </tr>
                    </thead>
                    <tbody>
                        {vol_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="grid-2col">
            <div class="panel">
                <h2>Liquidity Pattern Expectancy</h2>
                <div class="chart-container">
                    <canvas id="liqChart"></canvas>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Liquidity Pattern</th>
                            <th>Count</th>
                            <th>Buy Exp (ATR)</th>
                            <th>Buy WR</th>
                            <th>Sell Exp (ATR)</th>
                            <th>Sell WR</th>
                        </tr>
                    </thead>
                    <tbody>
                        {liq_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="panel">
                <h2>Specific Hour Windows Expectancy</h2>
                <div class="chart-container">
                    <canvas id="twChart"></canvas>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Time Window</th>
                            <th>Count</th>
                            <th>Buy Exp (ATR)</th>
                            <th>Buy WR</th>
                            <th>Sell Exp (ATR)</th>
                            <th>Sell WR</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tw_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        const rawData = {json.dumps(stats)};
        
        function renderBarChart(ctxId, title, labels, buyData, sellData) {{
            const ctx = document.getElementById(ctxId).getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Buy Expectancy (ATR)',
                            data: buyData,
                            backgroundColor: 'rgba(16, 185, 129, 0.65)',
                            borderColor: 'rgba(16, 185, 129, 1)',
                            borderWidth: 1
                        }},
                        {{
                            label: 'Sell Expectancy (ATR)',
                            data: sellData,
                            backgroundColor: 'rgba(239, 68, 68, 0.65)',
                            borderColor: 'rgba(239, 68, 68, 1)',
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{ color: '#334155' }},
                            ticks: {{ color: '#94a3b8' }}
                        }},
                        x: {{
                            grid: {{ display: false }},
                            ticks: {{ color: '#94a3b8' }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ labels: {{ color: '#f1f5f9' }} }}
                    }}
                }}
            }});
        }}
        
        // 1. Session Chart
        const sessKeys = Object.keys(rawData.sessions);
        renderBarChart(
            'sessionChart',
            'Session Expectancy',
            sessKeys,
            sessKeys.map(k => rawData.sessions[k].long_expectancy),
            sessKeys.map(k => rawData.sessions[k].short_expectancy)
        );
        
        // 2. Volatility Chart
        const volKeys = Object.keys(rawData.volatility_states);
        renderBarChart(
            'volChart',
            'Volatility Expectancy',
            volKeys,
            volKeys.map(k => rawData.volatility_states[k].long_expectancy),
            volKeys.map(k => rawData.volatility_states[k].short_expectancy)
        );
        
        // 3. Liquidity Chart
        const liqKeys = Object.keys(rawData.liquidity_patterns);
        renderBarChart(
            'liqChart',
            'Liquidity Expectancy',
            liqKeys,
            liqKeys.map(k => rawData.liquidity_patterns[k].long_expectancy),
            liqKeys.map(k => rawData.liquidity_patterns[k].short_expectancy)
        );
        
        // 4. Time Window Chart
        const twKeys = Object.keys(rawData.time_windows);
        renderBarChart(
            'twChart',
            'Time Window Expectancy',
            twKeys,
            twKeys.map(k => rawData.time_windows[k].long_expectancy),
            twKeys.map(k => rawData.time_windows[k].short_expectancy)
        );
    </script>
</body>
</html>
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_global_html_report(global_results: dict, summary_dir: Path):
    """Generate a beautiful global dashboard ranking assets and displaying institutional edges."""
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    rows = ""
    for sym in SYMBOLS:
        sym_stats = global_results.get(sym)
        if not sym_stats: continue
        
        best_edge_str = "None"
        best_edge_val = 0.0
        best_edge_dir = "Buy"
        for edge in sym_stats.get("top_edges", []):
            if abs(edge["expectancy_atr"]) > abs(best_edge_val):
                best_edge_val = edge["expectancy_atr"]
                best_edge_str = f"{edge['trigger']} ({edge['category']})"
                best_edge_dir = "Buy" if edge["direction"] == "long" else "Sell"
                
        # Calculate some summary stats for display
        ny_open_buy = sym_stats["sessions"].get("NY Open", {}).get("long_expectancy", 0.0)
        ldn_open_buy = sym_stats["sessions"].get("London Open", {}).get("long_expectancy", 0.0)
        
        val_sign = "+" if best_edge_val > 0 else ""
        color_code = "#10b981" if best_edge_val > 0 else "#ef4444"
        
        rows += f"""
        <tr>
            <td><b><a href="{sym}/{sym}_microstructure_report.html" style="color: #38bdf8; text-decoration: none;">{sym}</a></b></td>
            <td>{sym_stats['total_bars']}</td>
            <td>{best_edge_str}</td>
            <td><span class="badge APPROVED" style="background-color: { '#065f46' if best_edge_dir == 'Buy' else '#7f1d1d' }; color: { '#34d399' if best_edge_dir == 'Buy' else '#f87171' };">{best_edge_dir.upper()}</span></td>
            <td style="color: {color_code}; font-weight: bold;">{val_sign}{best_edge_val:.3f} ATR</td>
            <td style="color: { '#10b981' if ldn_open_buy > 0 else '#ef4444' };">{ldn_open_buy:.3f}</td>
            <td style="color: { '#10b981' if ny_open_buy > 0 else '#ef4444' };">{ny_open_buy:.3f}</td>
        </tr>
        """
        
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Global Microstructure Research Summary - Quant V9</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 30px;
        }}
        h1, h2, h3 {{
            color: #38bdf8;
            margin-top: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .panel {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 35px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 14px;
            border-bottom: 1px solid #334155;
            text-align: left;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #0f172a;
        }}
        .badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }}
        .APPROVED {{ background-color: #065f46; color: #34d399; }}
        .DISABLED {{ background-color: #7f1d1d; color: #f87171; }}
        .glass-hero {{
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(15, 23, 42, 0.6) 100%);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .intro-text {{
            font-size: 15px;
            color: #cbd5e1;
            line-height: 1.6;
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Global Microstructure Research Summary</h1>
                <h2 style="color: #94a3b8; font-weight: 400; font-size: 16px;">Quant V9 Institutional Intelligence Layer</h2>
            </div>
            <div>
                <span style="font-size: 13px; color: #64748b;">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</span>
            </div>
        </div>
        
        <div class="glass-hero">
            <h3>Institutional Timing & Liquidity Edge Report</h3>
            <p class="intro-text">
                This dashboard presents the consolidated statistical edge analysis of market microstructure states across all 10 assets. 
                Expectancy values are measured in ATR units derived from M1 bar standardized trading simulations.
                Click on the symbol names to explore interactive asset-level reports.
            </p>
        </div>
        
        <div class="panel">
            <h2>Multi-Asset Microstructure Edge Leaderboard</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Total Bars Analyzed</th>
                        <th>Strongest Edge Pattern</th>
                        <th>Edge Direction</th>
                        <th>Expectancy (ATR)</th>
                        <th>London Open Buy Exp</th>
                        <th>NY Open Buy Exp</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    with open(summary_dir / "summary.html", 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    global_results = {}
    
    print("\n============================================================")
    print(" STARTING MULTI-ASSET MARKET MICROSTRUCTURE RESEARCH")
    print("============================================================\n")
    
    for sym in SYMBOLS:
        try:
            stats = run_analysis_for_symbol(sym)
            if stats:
                global_results[sym] = stats
        except Exception as e:
            print(f"Error analyzing symbol {sym}: {e}")
            import traceback
            traceback.print_exc()
            
    # Save global results summary
    summary_dir = V9_1_DIR / "reports" / "microstructure_research"
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    with open(summary_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(global_results, f, indent=4)
        
    # Generate global summary HTML dashboard
    generate_global_html_report(global_results, summary_dir)
    
    print("\n============================================================")
    print(" MARKET MICROSTRUCTURE RESEARCH COMPLETED SUCCESSFULLY")
    print(f" Global Summary Dashboard: {summary_dir / 'summary.html'}")
    print("============================================================\n")

if __name__ == "__main__":
    main()
