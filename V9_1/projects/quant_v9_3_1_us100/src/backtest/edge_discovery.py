import numpy as np
import pandas as pd
import json
import csv
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

def classify_setup(row: dict, direction: str) -> str:
    # Read indicators
    rsi = float(row.get("rsi14_m15", 50.0))
    adx = float(row.get("adx14_h1", 20.0))
    atr_ratio = float(row.get("atr_ratio", 1.0))
    
    # Parse timestamp to get hour
    hour = 12
    if "timestamp" in row:
        try:
            dt = datetime.fromisoformat(str(row["timestamp"]))
            hour = dt.hour
        except:
            pass
            
    # 1. Volatility Expansion
    if atr_ratio > 1.3:
        return "volatility expansion"
        
    # 2. RSI Recovery
    if (direction == "long" and rsi < 40) or (direction == "short" and rsi > 60):
        return "RSI recovery"
        
    # 3. Session Breakout
    if hour in (8, 9, 13, 14) and adx >= 22:
        return "session breakout"
        
    # 4. Breakout
    if adx >= 28:
        return "breakout"
        
    # 5. Trend Continuation
    if adx >= 20:
        return "trend continuation"
        
    # 6. Mean Reversion
    return "mean reversion"

def classify_session(row: dict) -> str:
    hour = 12
    if "timestamp" in row:
        try:
            dt = datetime.fromisoformat(str(row["timestamp"]))
            hour = dt.hour
        except:
            pass
    atr_ratio = float(row.get("atr_ratio", 1.0))
    
    if atr_ratio > 1.5:
        return "Post-news"
    if 0 <= hour < 8:
        return "Asia"
    if 8 <= hour < 12:
        return "London"
    if 12 <= hour < 13 or 17 <= hour < 22:
        return "Lunch"
    if 13 <= hour < 15:
        return "New York"
    if 15 <= hour < 17:
        return "Post-news"
    return "Asia"

class EdgeDiscoveryAnalyzer:
    def __init__(self, symbol: str, initial_capital: float = 10000.0):
        self.symbol = symbol
        self.initial_capital = initial_capital
        
    def analyze(self, signals_log: List[dict]) -> Dict[str, Any]:
        executed_signals = [s for s in signals_log if s.get("executed", False)]
        
        # 1. Setup Stats
        setups = ["trend continuation", "breakout", "mean reversion", "session breakout", "RSI recovery", "volatility expansion"]
        setup_stats = {}
        rejected_setups = set()
        
        for setup in setups:
            setup_signals = [s for s in executed_signals if s.get("setup") == setup]
            trade_count = len(setup_signals)
            
            if trade_count == 0:
                setup_stats[setup] = {
                    "trade_count": 0, "winrate": 0.0, "profit_factor": 0.0, "sharpe": 0.0,
                    "avg_holding_time": 0.0, "expectancy": 0.0, "mc_worst_case_dd": 0.0,
                    "mc_ruin_probability": 0.0, "verdict": "REJECTED", "reason": "No trades"
                }
                rejected_setups.add(setup)
                continue
                
            pnls = [s["net_pnl"] for s in setup_signals]
            wins = sum(1 for p in pnls if p > 0)
            winrate = float(wins / trade_count)
            
            pos_pnls = [p for p in pnls if p > 0]
            neg_pnls = [p for p in pnls if p < 0]
            pf = float(sum(pos_pnls) / abs(sum(neg_pnls))) if neg_pnls else float('inf')
            
            mean_pnl = np.mean(pnls)
            std_pnl = np.std(pnls) if len(pnls) > 1 else 0.0
            
            # Simple Sharpe
            sharpe = float((mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0)
            avg_holding = float(np.mean([s.get("duration_bars", 0) for s in setup_signals]))
            expectancy = float(mean_pnl)
            
            # Monte Carlo
            mc = self.run_monte_carlo(pnls)
            mc_worst_dd = mc["worst_case_drawdown_95"]
            mc_ruin = mc["ruin_probability"]
            
            # Verdict Logic
            rejection_reasons = []
            if expectancy < 0:
                rejection_reasons.append("Negative Expectancy")
            if trade_count < 3:
                rejection_reasons.append("Insufficient Sample (<3)")
            if mc_worst_dd > 10.0:
                rejection_reasons.append(f"Unstable MC DD ({mc_worst_dd:.1f}%)")
            if mc_ruin > 0.01:
                rejection_reasons.append(f"High Ruin Prob ({mc_ruin:.1%})")
                
            verdict = "APPROVED" if not rejection_reasons else "REJECTED"
            reason_str = ", ".join(rejection_reasons) if rejection_reasons else "Passed all criteria"
            
            if verdict == "REJECTED":
                rejected_setups.add(setup)
                
            setup_stats[setup] = {
                "trade_count": trade_count,
                "winrate": winrate,
                "profit_factor": pf,
                "sharpe": sharpe,
                "avg_holding_time": avg_holding,
                "expectancy": expectancy,
                "mc_worst_case_dd": mc_worst_dd,
                "mc_ruin_probability": mc_ruin,
                "verdict": verdict,
                "reason": reason_str
            }
            
        # 2. Session Stats
        sessions = ["Asia", "London", "New York", "Lunch", "Post-news"]
        session_stats = {}
        for sess in sessions:
            sess_signals = [s for s in executed_signals if s.get("session_type") == sess]
            trade_count = len(sess_signals)
            
            if trade_count == 0:
                session_stats[sess] = {"trade_count": 0, "winrate": 0.0, "net_pnl": 0.0, "expectancy": 0.0}
                continue
                
            pnls = [s["net_pnl"] for s in sess_signals]
            wins = sum(1 for p in pnls if p > 0)
            winrate = float(wins / trade_count)
            net_pnl = float(sum(pnls))
            expectancy = float(net_pnl / trade_count)
            
            session_stats[sess] = {
                "trade_count": trade_count,
                "winrate": winrate,
                "net_pnl": net_pnl,
                "expectancy": expectancy
            }
            
        # 3. Asset-specific Alpha Profile
        approved_setups = [k for k, v in setup_stats.items() if v["verdict"] == "APPROVED"]
        all_traded_setups = [k for k, v in setup_stats.items() if v["trade_count"] > 0]
        
        # Best/Worst setup
        if approved_setups:
            best_setup = max(approved_setups, key=lambda k: setup_stats[k]["expectancy"])
        elif all_traded_setups:
            best_setup = max(all_traded_setups, key=lambda k: setup_stats[k]["expectancy"])
        else:
            best_setup = "N/A"
            
        if all_traded_setups:
            worst_setup = min(all_traded_setups, key=lambda k: setup_stats[k]["expectancy"])
        else:
            worst_setup = "N/A"
            
        # Best/Worst session
        active_sessions = [k for k, v in session_stats.items() if v["trade_count"] > 0]
        best_session = max(active_sessions, key=lambda k: session_stats[k]["net_pnl"]) if active_sessions else "N/A"
        worst_session = min(active_sessions, key=lambda k: session_stats[k]["net_pnl"]) if active_sessions else "N/A"
        
        # Volatility preference
        winning_signals = [s for s in executed_signals if s.get("net_pnl", 0.0) > 0]
        if winning_signals:
            avg_winning_atr = np.mean([s.get("atr_ratio", 1.0) for s in winning_signals])
            vol_preference = "HIGH_VOLATILITY" if avg_winning_atr > 1.0 else "LOW_VOLATILITY"
        else:
            vol_preference = "LOW_VOLATILITY"
            
        alpha_profile = {
            "best_setup": best_setup,
            "worst_setup": worst_setup,
            "best_session": best_session,
            "worst_session": worst_session,
            "volatility_preference": vol_preference
        }
        
        return {
            "symbol": self.symbol,
            "setup_statistics": setup_stats,
            "session_statistics": session_stats,
            "alpha_profile": alpha_profile,
            "rejected_setups": list(rejected_setups)
        }
        
    def run_monte_carlo(self, pnls: List[float], iterations: int = 1000) -> Dict[str, float]:
        if not pnls:
            return {"worst_case_drawdown_95": 0.0, "ruin_probability": 0.0}
            
        max_drawdowns = []
        ruin_count = 0
        
        for _ in range(iterations):
            sim_pnls = list(pnls)
            random.shuffle(sim_pnls)
            
            equity = self.initial_capital
            peak = equity
            max_dd = 0.0
            ruined = False
            
            for p in sim_pnls:
                equity += p
                if equity <= 0:
                    ruined = True
                    equity = 0
                    
                peak = max(peak, equity)
                if peak > 0:
                    dd = (peak - equity) / peak * 100
                    max_dd = max(max_dd, dd)
                    
            max_drawdowns.append(max_dd)
            if ruined or equity < (self.initial_capital * 0.8): # Tight 80% capital ruin threshold
                ruin_count += 1
                
        return {
            "worst_case_drawdown_95": float(np.percentile(max_drawdowns, 95)),
            "ruin_probability": float(ruin_count / iterations)
        }

def finalize_edge_discovery_reports(output_dir: Path, result: Dict[str, Any]):
    output_dir.mkdir(parents=True, exist_ok=True)
    symbol = result["symbol"]
    
    # Save JSON report
    with open(output_dir / f"{symbol}_edge_discovery.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
        
    # Export CSV for setup stats
    with open(output_dir / f"{symbol}_setup_stats.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["setup", "trade_count", "winrate", "profit_factor", "sharpe", "avg_holding_time", "expectancy", "mc_worst_case_dd", "mc_ruin_probability", "verdict", "reason"])
        for k, v in result["setup_statistics"].items():
            writer.writerow([k, v["trade_count"], v["winrate"], v["profit_factor"], v["sharpe"], v["avg_holding_time"], v["expectancy"], v["mc_worst_case_dd"], v["mc_ruin_probability"], v["verdict"], v["reason"]])
            
    # Export CSV for session stats
    with open(output_dir / f"{symbol}_session_stats.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["session", "trade_count", "winrate", "net_pnl", "expectancy"])
        for k, v in result["session_statistics"].items():
            writer.writerow([k, v["trade_count"], v["winrate"], v["net_pnl"], v["expectancy"]])
            
    # Export HTML Report
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Edge Discovery Report - {symbol}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #0d1117; color: #c9d1d9; }}
        h1, h2, h3 {{ color: #58a6ff; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: #161b22; padding: 25px; border-radius: 8px; border: 1px solid #30363d; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
        th, td {{ padding: 12px; border: 1px solid #30363d; text-align: left; }}
        th {{ background-color: #21262d; color: #f0f6fc; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .APPROVED {{ background-color: #238636; color: #ffffff; }}
        .REJECTED {{ background-color: #da3633; color: #ffffff; }}
        .card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .card {{ background-color: #21262d; padding: 15px; border-radius: 6px; border: 1px solid #30363d; text-align: center; }}
        .card-value {{ font-size: 18px; font-weight: bold; color: #58a6ff; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Edge Discovery Research - {symbol}</h1>
        <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <h2>Asset-Specific Alpha Profile</h2>
        <div class="card-grid">
            <div class="card"><div>Best Setup</div><div class="card-value">{result['alpha_profile']['best_setup']}</div></div>
            <div class="card"><div>Worst Setup</div><div class="card-value">{result['alpha_profile']['worst_setup']}</div></div>
            <div class="card"><div>Best Session</div><div class="card-value">{result['alpha_profile']['best_session']}</div></div>
            <div class="card"><div>Worst Session</div><div class="card-value">{result['alpha_profile']['worst_session']}</div></div>
            <div class="card"><div>Volatility Pref</div><div class="card-value">{result['alpha_profile']['volatility_preference']}</div></div>
        </div>
        
        <h2>Setup-Level Performance (Realistic Costs)</h2>
        <table>
            <thead>
                <tr>
                    <th>Setup</th>
                    <th>Trades</th>
                    <th>Winrate</th>
                    <th>PF</th>
                    <th>Sharpe</th>
                    <th>Avg Bars Held</th>
                    <th>Expectancy</th>
                    <th>MC 95% DD</th>
                    <th>MC Ruin</th>
                    <th>Verdict</th>
                </tr>
            </thead>
            <tbody>
    """
    for k, v in result["setup_statistics"].items():
        html += f"""
                <tr>
                    <td><b>{k}</b></td>
                    <td>{v['trade_count']}</td>
                    <td>{v['winrate']:.1%}</td>
                    <td>{v['profit_factor']:.2f}</td>
                    <td>{v['sharpe']:.2f}</td>
                    <td>{v['avg_holding_time']:.1f}</td>
                    <td>${v['expectancy']:.2f}</td>
                    <td>{v['mc_worst_case_dd']:.1f}%</td>
                    <td>{v['mc_ruin_probability']:.1%}</td>
                    <td><span class="badge {v['verdict']}">{v['verdict']}</span></td>
                </tr>
        """
    html += """
            </tbody>
        </table>
        
        <h2>Session-Level Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Session</th>
                    <th>Trades</th>
                    <th>Winrate</th>
                    <th>Net PnL</th>
                    <th>Expectancy</th>
                </tr>
            </thead>
            <tbody>
    """
    for k, v in result["session_statistics"].items():
        html += f"""
                <tr>
                    <td><b>{k}</b></td>
                    <td>{v['trade_count']}</td>
                    <td>{v['winrate']:.1%}</td>
                    <td>${v['net_pnl']:.2f}</td>
                    <td>${v['expectancy']:.2f}</td>
                </tr>
        """
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>
    """
    with open(output_dir / f"{symbol}_edge_discovery.html", 'w', encoding='utf-8') as f:
        f.write(html)
