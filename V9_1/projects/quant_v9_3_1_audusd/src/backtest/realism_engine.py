import numpy as np
import pandas as pd
import json
import csv
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

class RealismSimulator:
    @staticmethod
    def detect_market_condition(row: dict) -> str:
        # Determine market conditions based on volatility, adx, sessions, hour
        atr_ratio = float(row.get("atr_ratio", 1.0))
        adx = float(row.get("adx14_h1", 20.0))
        
        # Parse timestamp to get hour
        hour = 12
        if "timestamp" in row:
            try:
                dt = datetime.fromisoformat(str(row["timestamp"]))
                hour = dt.hour
            except Exception:
                pass
                
        # 1. News Volatile
        if atr_ratio > 2.0:
            return "NEWS_VOLATILE"
        # 2. Session Open (London around 8, NY around 13)
        if hour in (8, 9, 13, 14):
            return "SESSION_OPEN"
        # 3. Low Liquidity (Off-session)
        if str(row.get("session_flag", "london")) not in ("london", "new_york"):
            return "LOW_LIQUIDITY"
        # 4. Trend
        if adx > 25:
            return "TREND"
        # 5. Range
        if adx <= 18:
            return "RANGE"
        return "NORMAL"

    @staticmethod
    def calculate_cost(price: float, row: dict, base_spread_bps: float, base_slippage_bps: float) -> float:
        atr_ratio = float(row.get("atr_ratio", 1.0))
        condition = RealismSimulator.detect_market_condition(row)
        
        # Volatility-based spread expansion
        spread_multiplier = max(1.0, atr_ratio)
        if condition == "NEWS_VOLATILE":
            spread_multiplier *= 1.5
        elif condition == "LOW_LIQUIDITY":
            spread_multiplier *= 2.0
            
        effective_spread = base_spread_bps * spread_multiplier
        
        # Commission (fixed commission of 0.5 bps of trade value)
        commission = 0.5
        
        # Slippage: random components + market condition factors
        slippage = base_slippage_bps * max(1.0, atr_ratio)
        slippage += random.uniform(0.0, 1.5)
        
        # Execution delay penalty (latency slippage): 0.1 to 1.0 bps scaled by ATR
        execution_delay_bps = random.uniform(0.1, 1.0) * max(1.0, atr_ratio)
        
        total_bps = effective_spread + commission + slippage + execution_delay_bps
        cost = price * total_bps / 10000.0
        return cost

    @staticmethod
    def apply_partial_fills(pnl: float) -> float:
        # 10% probability of partial fill (fills 50% to 95% of trade size)
        if random.random() < 0.10:
            fill_rate = random.uniform(0.50, 0.95)
            return pnl * fill_rate
        return pnl

class EquityCurveEngine:
    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
        if not trades:
            return {
                "realized_pnl": 0.0,
                "max_drawdown_pct": 0.0,
                "max_consecutive_losses": 0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "equity_curve": [initial_capital]
            }
            
        equity = initial_capital
        equity_curve = [equity]
        peaks = [equity]
        drawdowns = [0.0]
        
        consecutive_losses = 0
        max_consecutive_losses = 0
        returns = []
        
        for t in trades:
            pnl = float(t.get("pnl", 0.0))
            equity += pnl
            equity_curve.append(equity)
            
            # Drawdown calculations
            peaks.append(max(peaks[-1], equity))
            dd = (peaks[-1] - equity) / peaks[-1] * 100
            drawdowns.append(dd)
            
            # Loss streak
            if pnl < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
                
            # Returns calculation
            returns.append(pnl / initial_capital)
            
        max_drawdown = float(max(drawdowns))
        realized_pnl = float(equity - initial_capital)
        
        # Sharpe and Sortino ratios (scaled by assuming ~250 trading sessions per year)
        returns = np.array(returns)
        mean_ret = np.mean(returns) if len(returns) > 0 else 0.0
        std_ret = np.std(returns) if len(returns) > 1 else 0.0
        
        neg_returns = returns[returns < 0]
        downside_std = np.std(neg_returns) if len(neg_returns) > 1 else 0.0
        
        # Scaling factor: np.sqrt(len(trades)) or dynamic based on duration.
        # Let's use a standard per-trade metrics multiplied by np.sqrt(252) for standardization
        sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        sortino = (mean_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
        
        return {
            "realized_pnl": realized_pnl,
            "max_drawdown_pct": max_drawdown,
            "max_consecutive_losses": int(max_consecutive_losses),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "equity_curve": equity_curve
        }

class MonteCarloSimulator:
    @staticmethod
    def run_simulation(trades: List[Dict[str, Any]], initial_capital: float, iterations: int = 1000) -> Dict[str, Any]:
        if not trades:
            return {"median_drawdown": 0.0, "worst_case_drawdown_95": 0.0, "ruin_probability": 0.0}
            
        max_drawdowns = []
        ruin_count = 0
        
        for _ in range(iterations):
            sim_trades = list(trades)
            random.shuffle(sim_trades)
            
            equity = initial_capital
            peak = equity
            max_dd = 0.0
            ruined = False
            
            for t in sim_trades:
                # Inject random slippage perturbation (0 to 3 bps) and execution delay penalty
                pnl = float(t.get("pnl", 0.0))
                direction = t.get("direction", "long")
                entry = float(t.get("entry", 1.0))
                
                # Slippage deduction (reducing PnL for both long and short)
                slippage_bps = random.uniform(0.0, 3.0) + random.uniform(0.0, 1.5)
                cost_deduction = entry * slippage_bps / 10000.0
                
                sim_pnl = pnl - cost_deduction
                
                # Dynamic partial fill adjustment
                sim_pnl = RealismSimulator.apply_partial_fills(sim_pnl)
                
                equity += sim_pnl
                if equity <= 0:
                    ruined = True
                    equity = 0
                    
                peak = max(peak, equity)
                if peak > 0:
                    dd = (peak - equity) / peak * 100
                    max_dd = max(max_dd, dd)
                    
            max_drawdowns.append(max_dd)
            if ruined or equity < (initial_capital * 0.5): # 50% capital drawdown considered ruin
                ruin_count += 1
                
        return {
            "median_drawdown": float(np.median(max_drawdowns)),
            "worst_case_drawdown_95": float(np.percentile(max_drawdowns, 95)),
            "ruin_probability": float(ruin_count / iterations)
        }

class RealismClassifier:
    @staticmethod
    def classify(metrics: dict, mc_metrics: dict) -> str:
        pf = float(metrics.get("profit_factor", 0.0))
        sharpe = float(metrics.get("sharpe_ratio", 0.0))
        dd = float(metrics.get("max_drawdown_pct", 0.0))
        mc_dd_95 = float(mc_metrics.get("worst_case_drawdown_95", 0.0))
        consec_losses = int(metrics.get("max_consecutive_losses", 0))
        
        if pf >= 1.5 and sharpe >= 1.8 and dd <= 8.0 and mc_dd_95 <= 12.0 and consec_losses <= 5:
            return "INSTITUTIONAL_READY"
        elif pf >= 1.2 and sharpe >= 1.2 and dd <= 15.0 and mc_dd_95 <= 20.0:
            return "LIVE_PAPER_READY"
        elif pf >= 1.0:
            return "SANDBOX_ONLY"
        else:
            return "DISABLED"

def run_realism_audit(trades: List[Dict[str, Any]], initial_capital: float, output_dir: Path, symbol: str) -> Dict[str, Any]:
    # 1. Equity metrics
    metrics = EquityCurveEngine.calculate_metrics(trades, initial_capital)
    
    # 2. Add profit factor to metrics for classification
    pnl_vals = [float(t.get("pnl", 0.0)) for t in trades]
    wins = sum(x for x in pnl_vals if x > 0)
    losses = sum(abs(x) for x in pnl_vals if x < 0)
    metrics["profit_factor"] = float(wins / losses) if losses > 0 else float('inf')
    
    # 3. Monte Carlo simulation
    mc_metrics = MonteCarloSimulator.run_simulation(trades, initial_capital, iterations=1000)
    
    # 4. Classification
    verdict = RealismClassifier.classify(metrics, mc_metrics)
    
    report = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "initial_capital": initial_capital,
        "ending_equity": float(metrics["equity_curve"][-1]),
        "realized_pnl": metrics["realized_pnl"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_pct": metrics["max_drawdown_pct"],
        "max_consecutive_losses": metrics["max_consecutive_losses"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "sortino_ratio": metrics["sortino_ratio"],
        "monte_carlo_median_dd": mc_metrics["median_drawdown"],
        "monte_carlo_95_dd": mc_metrics["worst_case_drawdown_95"],
        "ruin_probability": mc_metrics["ruin_probability"],
        "verdict": verdict
    }
    
    # Write files
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    with open(output_dir / f"{symbol}_realism.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
        
    # CSV
    with open(output_dir / f"{symbol}_realism.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=report.keys())
        writer.writeheader()
        writer.writerow(report)
        
    # HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Realism Engine Report - {symbol}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #0d1117; color: #c9d1d9; }}
        h1, h2, h3 {{ color: #58a6ff; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #161b22; padding: 25px; border-radius: 8px; border: 1px solid #30363d; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
        th, td {{ padding: 12px; border: 1px solid #30363d; text-align: left; }}
        th {{ background-color: #21262d; color: #f0f6fc; }}
        .verdict-box {{ padding: 15px; border-radius: 6px; font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
        .INSTITUTIONAL_READY {{ background-color: #1f6feb; color: #ffffff; border: 1px solid #58a6ff; }}
        .LIVE_PAPER_READY {{ background-color: #238636; color: #ffffff; border: 1px solid #2ea043; }}
        .SANDBOX_ONLY {{ background-color: #d29922; color: #0d1117; border: 1px solid #e3b341; }}
        .DISABLED {{ background-color: #da3633; color: #ffffff; border: 1px solid #f85149; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Realism Engine Audit - {symbol}</h1>
        <p>Generated at: {report['timestamp']}</p>
        
        <div class="verdict-box {verdict}">
            VERDICT: {verdict}
        </div>
        
        <h3>Simulation Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Idealized Backtest</th><th>Realistic Engine Output</th></tr>
            <tr><td>Profit Factor</td><td>-</td><td>{report['profit_factor']:.2f}</td></tr>
            <tr><td>Max Drawdown (%)</td><td>-</td><td>{report['max_drawdown_pct']:.2f}%</td></tr>
            <tr><td>Sharpe Ratio</td><td>-</td><td>{report['sharpe_ratio']:.2f}</td></tr>
            <tr><td>Sortino Ratio</td><td>-</td><td>{report['sortino_ratio']:.2f}</td></tr>
            <tr><td>Max Consecutive Losses</td><td>-</td><td>{report['max_consecutive_losses']}</td></tr>
        </table>
        
        <h3>Monte Carlo Stress Test (1,000 Iterations)</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Median Drawdown</td><td>{report['monte_carlo_median_dd']:.2f}%</td></tr>
            <tr><td>95th Percentile Drawdown (Worst-Case)</td><td>{report['monte_carlo_95_dd']:.2f}%</td></tr>
            <tr><td>Probability of Ruin / 50% Drawdown</td><td>{report['ruin_probability']:.2%}</td></tr>
        </table>
    </div>
</body>
</html>
"""
    with open(output_dir / f"{symbol}_realism.html", 'w', encoding='utf-8') as f:
        f.write(html)
        
    return report
