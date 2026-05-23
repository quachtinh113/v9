import numpy as np
import pandas as pd
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

class AlphaResearchFilter:
    def __init__(self, symbol: str, base_spread_bps: float, base_slippage_bps: float):
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.base_slippage_bps = base_slippage_bps
        
        # State tracking
        self.bars_since_last_trade = 999
        self.last_trade_was_loss = False
        self.current_session = None
        self.session_trade_count = 0
        
        # Logs
        self.signals_log = []
        self.trades_log = []
        
    def on_bar(self, row: dict):
        self.bars_since_last_trade += 1
        session = row.get("session_flag", "london")
        if session != self.current_session:
            self.current_session = session
            self.session_trade_count = 0

    def evaluate(self, row: dict, plan: Any, decision: Any) -> tuple[str, bool]:
        from src.core.regime_engine import detect_regime
        
        # Detect regime dynamically to get confidence and regime name
        rs = detect_regime(row, trend_adx_min=20)
        regime_confidence = rs.confidence
        regime = rs.regime
        
        adx = float(row.get("adx14_h1", 20.0))
        atr_ratio = float(row.get("atr_ratio", 1.0))
        
        bias = str(row.get("bias", "flat"))
        bias_aligned = 1 if decision.direction == bias else 0
        session = row.get("session_flag", "london")
        price = float(row.get("close_m1", 1.0))
        
        # 1. Quality Filters
        # - News avoidance: atr_ratio > 2.0 (high volatility news event)
        news_event = atr_ratio > 2.0
        
        # - Volatility filter: healthy range
        volatility_healthy = (0.5 <= atr_ratio <= 1.8)
        
        # - Session filter: London & NY only
        session_liquid = session in ("london", "new_york")
        
        # - Spread efficiency filter: spread bps relative to expected move
        expected_move_pct = abs(plan.take_profit - price) / price
        expected_move_bps = expected_move_pct * 10000.0
        
        spread_multiplier = max(1.0, atr_ratio)
        if news_event:
            spread_multiplier *= 1.5
        elif session not in ("london", "new_york"):
            spread_multiplier *= 2.0
            
        effective_spread = self.base_spread_bps * spread_multiplier
        spread_efficient = (effective_spread / expected_move_bps <= 0.25) if expected_move_bps > 0 else False
        
        # 2. Overtrading Filters
        # - Minimum spacing: 60 bars standard, 120 bars cooldown after loss
        required_spacing = 120 if self.last_trade_was_loss else 60
        spacing_ok = self.bars_since_last_trade >= required_spacing
        
        # - Minimum ATR movement
        min_atr_ok = atr_ratio >= 0.5
        
        # - Session limit
        session_limit_ok = self.session_trade_count < 3
        
        # 3. Signal Ranking
        # Critical violations trigger REJECT
        if news_event or not volatility_healthy or not session_liquid or not spread_efficient or not spacing_ok or not min_atr_ok or not session_limit_ok:
            rank = "REJECT"
        else:
            # Passes all overtrading and quality rules -> evaluate ranking
            if regime_confidence >= 0.5 and bias_aligned == 1 and atr_ratio >= 1.0:
                rank = "A+"
            elif regime_confidence >= 0.5:
                rank = "A"
            elif regime_confidence >= 0.3:
                rank = "B"
            else:
                rank = "C"
                
        # 4. Only allow A+ and A trades during high-quality regimes
        allowed = rank in ("A+", "A")
        
        return rank, allowed

    def track_signal(self, row: dict, plan: Any, decision: Any, rank: str, allowed: bool):
        from src.core.regime_engine import detect_regime
        from src.backtest.edge_discovery import classify_setup, classify_session
        
        rs = detect_regime(row, trend_adx_min=20)
        setup = classify_setup(row, decision.direction)
        session_type = classify_session(row)
        
        price = float(row.get("close_m1", 1.0))
        atr_ratio = float(row.get("atr_ratio", 1.0))
        session = row.get("session_flag", "london")
        
        # Calculate expected costs
        spread_multiplier = max(1.0, atr_ratio)
        if atr_ratio > 2.0:
            spread_multiplier *= 1.5
        elif session not in ("london", "new_york"):
            spread_multiplier *= 2.0
            
        effective_spread = self.base_spread_bps * spread_multiplier
        commission_bps = 0.5
        slippage_bps = self.base_slippage_bps * max(1.0, atr_ratio)
        latency_bps = 0.55 * max(1.0, atr_ratio) # average dynamic latency penalty
        
        total_cost_bps = effective_spread + commission_bps + slippage_bps + latency_bps
        cost_dollars = price * total_cost_bps / 10000.0
        
        self.signals_log.append({
            "timestamp": row.get("timestamp"),
            "price": price,
            "direction": decision.direction,
            "regime": rs.regime,
            "session": session,
            "session_type": session_type,
            "setup": setup,
            "atr_ratio": atr_ratio,
            "regime_confidence": float(rs.confidence),
            "rank": rank,
            "allowed": allowed,
            "effective_spread": effective_spread,
            "slippage": slippage_bps,
            "latency": latency_bps,
            "total_cost_bps": total_cost_bps,
            "cost_dollars": cost_dollars,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "executed": False,
            "duration_bars": 0,
            "outcome": "N/A"
        })

    def track_trade_exit(self, exit_pnl: float, duration_bars: int):
        self.bars_since_last_trade = 0
        self.session_trade_count += 1
        self.last_trade_was_loss = exit_pnl < 0
        
        # Find the last signal that was executed and update its outcome
        for sig in reversed(self.signals_log):
            if sig["allowed"] and not sig["executed"]:
                sig["executed"] = True
                sig["net_pnl"] = exit_pnl
                sig["duration_bars"] = duration_bars
                # Gross PnL is before spread, commission, slippage and latency
                # PnL in dollars of trade = exit_price_dollars - entry_price_dollars
                # We added cost to entry and subtracted/added cost to exit.
                # Net PnL = Gross PnL - Entry Cost - Exit Cost
                # Therefore, Gross PnL = Net PnL + 2 * Cost (approx)
                sig["gross_pnl"] = exit_pnl + (2.0 * sig["cost_dollars"])
                sig["outcome"] = "WIN" if exit_pnl > 0 else "LOSS"
                break

    def finalize_analysis(self, output_dir: Path) -> Dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Execution Efficiency Analysis
        executed_signals = [s for s in self.signals_log if s["executed"]]
        
        avg_spread = np.mean([s["effective_spread"] for s in self.signals_log]) if self.signals_log else 0.0
        avg_slippage = np.mean([s["slippage"] for s in self.signals_log]) if self.signals_log else 0.0
        avg_latency = np.mean([s["latency"] for s in self.signals_log]) if self.signals_log else 0.0
        
        total_net_pnl = sum(s["net_pnl"] for s in executed_signals)
        total_costs = sum(s["cost_dollars"] * 2.0 for s in executed_signals) # entry + exit costs
        
        # Expectancy = Net PnL per trade
        expectancy = total_net_pnl / len(executed_signals) if executed_signals else 0.0
        cost_adjusted_expectancy = (total_net_pnl - total_costs) / len(executed_signals) if executed_signals else 0.0
        
        # 2. Edge Analysis: setup survival
        edge_data = []
        setups = {}
        for s in self.signals_log:
            key = (s["regime"], s["direction"])
            if key not in setups:
                setups[key] = {"total_signals": 0, "allowed": 0, "executed": 0, "gross_pnl": 0.0, "net_pnl": 0.0}
            setups[key]["total_signals"] += 1
            if s["allowed"]:
                setups[key]["allowed"] += 1
            if s["executed"]:
                setups[key]["executed"] += 1
                setups[key]["gross_pnl"] += s["gross_pnl"]
                setups[key]["net_pnl"] += s["net_pnl"]
                
        for (regime, direction), stats in setups.items():
            status = "SURVIVED"
            if stats["executed"] > 0:
                if stats["gross_pnl"] > 0 and stats["net_pnl"] <= 0:
                    status = "DIED_FROM_COSTS"
                elif stats["net_pnl"] <= 0:
                    status = "UNPROFITABLE"
            else:
                status = "FILTERED_OUT"
                
            edge_data.append({
                "regime": regime,
                "direction": direction,
                "total_signals": stats["total_signals"],
                "executed": stats["executed"],
                "gross_pnl": stats["gross_pnl"],
                "net_pnl": stats["net_pnl"],
                "status": status
            })
            
        # Session Profitability
        session_profit = {}
        for s in executed_signals:
            sess = s["session"]
            if sess not in session_profit:
                session_profit[sess] = 0.0
            session_profit[sess] += s["net_pnl"]
            
        # Ranking Distribution
        ranks_dist = {"A+": 0, "A": 0, "B": 0, "C": 0, "REJECT": 0}
        for s in self.signals_log:
            ranks_dist[s["rank"]] = ranks_dist.get(s["rank"], 0) + 1
            
        report = {
            "symbol": self.symbol,
            "timestamp": datetime.now().isoformat(),
            "execution_efficiency": {
                "average_spread_bps": float(avg_spread),
                "average_slippage_bps": float(avg_slippage),
                "average_latency_bps": float(avg_latency),
                "total_trades": len(executed_signals),
                "total_net_pnl": float(total_net_pnl),
                "expectancy_dollars": float(expectancy),
                "cost_adjusted_expectancy": float(cost_adjusted_expectancy)
            },
            "ranking_distribution": ranks_dist,
            "session_profitability": session_profit,
            "edge_analysis": edge_data
        }
        
        # Save files
        with open(output_dir / f"{self.symbol}_alpha.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
            
        # Export CSV
        with open(output_dir / f"{self.symbol}_alpha_edge.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["regime", "direction", "total_signals", "executed", "gross_pnl", "net_pnl", "status"])
            writer.writeheader()
            for row in edge_data:
                writer.writerow(row)
                
        # HTML Report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Alpha Research Report - {self.symbol}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #0d1117; color: #c9d1d9; }}
        h1, h2, h3 {{ color: #58a6ff; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #161b22; padding: 25px; border-radius: 8px; border: 1px solid #30363d; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
        th, td {{ padding: 12px; border: 1px solid #30363d; text-align: left; }}
        th {{ background-color: #21262d; color: #f0f6fc; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .SURVIVED {{ background-color: #238636; color: #ffffff; }}
        .DIED_FROM_COSTS {{ background-color: #d29922; color: #0d1117; }}
        .UNPROFITABLE {{ background-color: #da3633; color: #ffffff; }}
        .FILTERED_OUT {{ background-color: #30363d; color: #8b949e; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Alpha Research Audit - {self.symbol}</h1>
        <p>Generated at: {report['timestamp']}</p>
        
        <h3>Execution Efficiency Analysis</h3>
        <table>
            <tr><td>Average Spread (bps)</td><td>{report['execution_efficiency']['average_spread_bps']:.2f}</td></tr>
            <tr><td>Average Slippage (bps)</td><td>{report['execution_efficiency']['average_slippage_bps']:.2f}</td></tr>
            <tr><td>Average Latency (bps)</td><td>{report['execution_efficiency']['average_latency_bps']:.2f}</td></tr>
            <tr><td>Total Trades Executed</td><td>{report['execution_efficiency']['total_trades']}</td></tr>
            <tr><td>Net Expectancy (per trade)</td><td>${report['execution_efficiency']['expectancy_dollars']:.2f}</td></tr>
            <tr><td>Cost-Adjusted Expectancy</td><td>${report['execution_efficiency']['cost_adjusted_expectancy']:.2f}</td></tr>
        </table>
        
        <h3>Signal Ranking Distribution</h3>
        <table>
            <tr><th>Rank</th><th>Count</th></tr>
            <tr><td>A+ (High Quality Breakout)</td><td>{ranks_dist.get('A+', 0)}</td></tr>
            <tr><td>A (High Quality Regime)</td><td>{ranks_dist.get('A', 0)}</td></tr>
            <tr><td>B (Medium Confidence)</td><td>{ranks_dist.get('B', 0)}</td></tr>
            <tr><td>C (Low Confidence)</td><td>{ranks_dist.get('C', 0)}</td></tr>
            <tr><td>REJECT (Violated constraints)</td><td>{ranks_dist.get('REJECT', 0)}</td></tr>
        </table>

        <h3>Edge Analysis: Setup Performance</h3>
        <table>
            <thead>
                <tr>
                    <th>Regime</th>
                    <th>Direction</th>
                    <th>Signals</th>
                    <th>Executed</th>
                    <th>Gross PnL</th>
                    <th>Net PnL</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """
        for row in edge_data:
            html += f"""
                <tr>
                    <td>{row['regime']}</td>
                    <td>{row['direction']}</td>
                    <td>{row['total_signals']}</td>
                    <td>{row['executed']}</td>
                    <td>${row['gross_pnl']:.2f}</td>
                    <td>${row['net_pnl']:.2f}</td>
                    <td><span class="status-badge {row['status']}">{row['status']}</span></td>
                </tr>
            """
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        with open(output_dir / f"{self.symbol}_alpha.html", 'w', encoding='utf-8') as f:
            f.write(html)
            
        return report
