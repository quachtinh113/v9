from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
from src.core.models import Trade, RiskDecision
from src.core.risk_engine import RiskGateway
from src.data.loaders import generate_sample_ohlcv, load_ohlcv_csv
from src.data.mtf_builder import build_feature_table
from src.execution.trade_journal import PipelineAuditLog

class SingleAssetBacktester:
    def __init__(self, symbol_config, strategy_module, audit_log=None):
        self.config = symbol_config
        self.strategy_module = strategy_module
        self.audit_log = audit_log
        self.spread_bps = float(symbol_config.get("backtest", {}).get("spread_bps", 2.0))
        self.slippage_bps = float(symbol_config.get("backtest", {}).get("slippage_bps", 1.0))
        self.initial_capital = float(symbol_config.get("backtest", {}).get("initial_capital", 100000))
        self.risk_gateway = RiskGateway(symbol_config.get("risk", {}))

    def run(self, feature_table: pd.DataFrame) -> Dict[str, Any]:
        from src.backtest.realism_engine import RealismSimulator, run_realism_audit
        from src.backtest.alpha_filter import AlphaResearchFilter
        from pathlib import Path
        
        trades: List[Trade] = []
        open_trade = None
        equity = self.initial_capital
        equity_curve = [equity]
        peak_equity = equity
        day_peak_equity = equity
        week_peak_equity = equity
        loss_streak = 0
        max_bars = max(int(self.config.get("position", {}).get("timeout_minutes", 120)), 1)
        
        # Track previous dates for reset boundaries
        last_date = None
        last_week = None
        
        # Alpha research filter
        alpha_filter = AlphaResearchFilter(self.config["symbol"], self.spread_bps, self.slippage_bps)
        
        for _, row in feature_table.iterrows():
            ts = row["timestamp"]
            price = float(row["close_m1"])
            
            # Reset daily metrics
            try:
                current_date = pd.to_datetime(ts).date()
                if last_date is None or current_date != last_date:
                    day_peak_equity = equity
                    loss_streak = 0  # Reset loss streak daily to clear temporary soft blocks
                    last_date = current_date
            except Exception:
                pass
                
            # Reset weekly metrics
            try:
                current_week = pd.to_datetime(ts).isocalendar()[:2]
                if last_week is None or current_week != last_week:
                    week_peak_equity = equity
                    last_week = current_week
            except Exception:
                pass
            
            # Update Alpha Research Filter state
            alpha_filter.on_bar(row.to_dict())
            
            # Dynamic realism cost simulator
            cost = RealismSimulator.calculate_cost(price, row.to_dict(), self.spread_bps, self.slippage_bps)
            
            if open_trade is None:
                plan, decision = self.strategy_module.generate_trade_plan(row.to_dict(), self.config)
                if plan is not None and decision.direction in {"long", "short"}:
                    # Evaluate signal through Alpha Research Filter
                    rank, allowed = alpha_filter.evaluate(row.to_dict(), plan, decision)
                    # Track signal (regardless of execution status for edge analysis)
                    alpha_filter.track_signal(row.to_dict(), plan, decision, rank, allowed)
                    
                    if allowed:
                        daily_dd = max((day_peak_equity - equity) / day_peak_equity * 100, 0.0) if day_peak_equity > 0 else 0.0
                        weekly_dd = max((week_peak_equity - equity) / week_peak_equity * 100, 0.0) if week_peak_equity > 0 else 0.0
                        
                        atr_ratio = float(row.get("atr_ratio", 1.0))
                        condition = RealismSimulator.detect_market_condition(row.to_dict())
                        spread_multiplier = max(1.0, atr_ratio)
                        if condition == "NEWS_VOLATILE":
                            spread_multiplier *= 1.5
                        elif condition == "LOW_LIQUIDITY":
                            spread_multiplier *= 2.0
                        effective_spread = self.spread_bps * spread_multiplier
                        effective_slippage = self.slippage_bps * max(1.0, atr_ratio)
                        
                        market_data = {
                            "session_flag": row.get("session_flag", "london"),
                            "spread_bps": effective_spread,
                            "slippage_bps": effective_slippage,
                            "atr_ratio": atr_ratio
                        }
                        
                        risk_decision = self.risk_gateway.full_gate(
                            {
                                "daily_dd_pct": daily_dd,
                                "weekly_dd_pct": weekly_dd,
                                "loss_streak": loss_streak
                            },
                            market_data
                        )
                        
                        if risk_decision.action == "ALLOW":
                            entry = price + cost if decision.direction == "long" else price - cost
                            from src.backtest.edge_discovery import classify_setup, classify_session
                            setup = classify_setup(row.to_dict(), decision.direction)
                            session_type = classify_session(row.to_dict())
                            open_trade = {
                                "direction": decision.direction,
                                "entry": entry,
                                "entry_time": ts,
                                "stop_loss": plan.stop_loss,
                                "take_profit": plan.take_profit,
                                "bars_held": 0,
                                "setup": setup,
                                "session_type": session_type
                            }
            else:
                open_trade["bars_held"] += 1
                exit_price = None
                exit_reason = None
                if open_trade["direction"] == "long":
                    if float(row.get("low", price)) <= open_trade["stop_loss"]: exit_price, exit_reason = open_trade["stop_loss"] - cost, "stop"
                    elif float(row.get("high", price)) >= open_trade["take_profit"]: exit_price, exit_reason = open_trade["take_profit"] - cost, "target"
                else:
                    if float(row.get("high", price)) >= open_trade["stop_loss"]: exit_price, exit_reason = open_trade["stop_loss"] + cost, "stop"
                    elif float(row.get("low", price)) <= open_trade["take_profit"]: exit_price, exit_reason = open_trade["take_profit"] + cost, "target"
                
                if exit_price is None and open_trade["bars_held"] >= max_bars: exit_price, exit_reason = price, "timeout"
                
                if exit_price is not None:
                    pnl = (exit_price - open_trade["entry"]) if open_trade["direction"] == "long" else (open_trade["entry"] - exit_price)
                    
                    # Apply partial fills
                    pnl = RealismSimulator.apply_partial_fills(pnl)
                    
                    equity += pnl
                    peak_equity = max(peak_equity, equity)
                    day_peak_equity = max(day_peak_equity, equity)
                    week_peak_equity = max(week_peak_equity, equity)
                    if pnl < 0: loss_streak += 1
                    else: loss_streak = 0
                    
                    t = Trade(self.config["symbol"], open_trade["direction"], str(open_trade["entry_time"]), str(ts), open_trade["entry"], exit_price, open_trade["stop_loss"], open_trade["take_profit"], pnl, open_trade["bars_held"], exit_reason)
                    t.setup = open_trade["setup"]
                    t.session_type = open_trade["session_type"]
                    trades.append(t)
                    
                    # Notify Alpha Research Filter of trade exit
                    alpha_filter.track_trade_exit(pnl, open_trade["bars_held"])
                    open_trade = None
            
            # Track floating PnL for true equity curve
            floating_pnl = 0.0
            if open_trade is not None:
                floating_pnl = (price - open_trade["entry"]) if open_trade["direction"] == "long" else (open_trade["entry"] - price)
                
            bar_equity = equity + floating_pnl
            equity_curve.append(bar_equity)
            peak_equity = max(peak_equity, bar_equity)
            day_peak_equity = max(day_peak_equity, bar_equity)
            week_peak_equity = max(week_peak_equity, bar_equity)

        # Generate realism report
        trades_dict = []
        for t in trades:
            trades_dict.append({
                "direction": t.direction,
                "entry": t.entry,
                "exit": t.exit,
                "pnl": t.pnl,
                "bars_held": t.bars_held,
                "exit_reason": t.exit_reason
            })
            
        realism_dir = Path(__file__).resolve().parents[2] / "reports" / "realism_engine"
        realism_report = run_realism_audit(trades_dict, self.initial_capital, realism_dir, self.config["symbol"])

        # Generate Alpha Research report
        alpha_dir = Path(__file__).resolve().parents[2] / "reports" / "alpha_research"
        alpha_report = alpha_filter.finalize_analysis(alpha_dir)

        # Generate Edge Discovery report
        from src.backtest.edge_discovery import EdgeDiscoveryAnalyzer, finalize_edge_discovery_reports
        edge_analyzer = EdgeDiscoveryAnalyzer(self.config["symbol"], self.initial_capital)
        edge_report = edge_analyzer.analyze(alpha_filter.signals_log)
        
        # Simulate Layer 3 (Edge Discovery selective portfolio)
        filtered_trades_dict = []
        for t in trades:
            if t.setup not in edge_report["rejected_setups"]:
                filtered_trades_dict.append({
                    "direction": t.direction,
                    "entry": t.entry,
                    "exit": t.exit,
                    "pnl": t.pnl,
                    "bars_held": t.bars_held,
                    "exit_reason": t.exit_reason
                })
                
        from src.backtest.realism_engine import EquityCurveEngine, MonteCarloSimulator
        filtered_metrics = EquityCurveEngine.calculate_metrics(filtered_trades_dict, self.initial_capital)
        filtered_mc = MonteCarloSimulator.run_simulation(filtered_trades_dict, self.initial_capital)
        
        filtered_pnls = [t["pnl"] for t in filtered_trades_dict]
        filtered_wins = sum(1 for p in filtered_pnls if p > 0)
        filtered_total = len(filtered_trades_dict)
        filtered_winrate = filtered_wins / filtered_total if filtered_total > 0 else 0.0
        
        pos_pnls = [p for p in filtered_pnls if p > 0]
        neg_pnls = [p for p in filtered_pnls if p < 0]
        filtered_pf = sum(pos_pnls) / abs(sum(neg_pnls)) if neg_pnls else (float('inf') if pos_pnls else 0.0)
        
        edge_report["portfolio_metrics"] = {
            "total_trades": filtered_total,
            "winrate": filtered_winrate,
            "net_pnl": float(filtered_metrics["realized_pnl"]),
            "profit_factor": float(filtered_pf),
            "sharpe_ratio": float(filtered_metrics["sharpe_ratio"]),
            "max_drawdown_pct": float(filtered_metrics["max_drawdown_pct"]),
            "mc_worst_case_dd": float(filtered_mc["worst_case_drawdown_95"]),
            "ruin_probability": float(filtered_mc["ruin_probability"]),
            "verdict": "APPROVED" if (filtered_total >= 3 and filtered_metrics["realized_pnl"] > 0 and filtered_mc["ruin_probability"] < 0.01) else "DISABLED"
        }
        
        edge_dir = Path(__file__).resolve().parents[2] / "reports" / "edge_discovery"
        finalize_edge_discovery_reports(edge_dir, edge_report)

        summary = self._summarize(trades, equity_curve)
        summary.update({
            "realism_verdict": realism_report["verdict"],
            "sharpe_ratio": realism_report["sharpe_ratio"],
            "sortino_ratio": realism_report["sortino_ratio"],
            "max_drawdown_pct": realism_report["max_drawdown_pct"],
            "mc_worst_case_dd": realism_report["monte_carlo_95_dd"],
            "ruin_probability": realism_report["ruin_probability"],
            # Alpha metrics
            "alpha_trades": alpha_report["execution_efficiency"]["total_trades"],
            "alpha_net_pnl": alpha_report["execution_efficiency"]["total_net_pnl"],
            "alpha_expectancy": alpha_report["execution_efficiency"]["expectancy_dollars"],
            "alpha_cost_adjusted_expectancy": alpha_report["execution_efficiency"]["cost_adjusted_expectancy"],
            # Edge metrics
            "edge_trades": edge_report["portfolio_metrics"]["total_trades"],
            "edge_net_pnl": edge_report["portfolio_metrics"]["net_pnl"],
            "edge_profit_factor": edge_report["portfolio_metrics"]["profit_factor"],
            "edge_sharpe": edge_report["portfolio_metrics"]["sharpe_ratio"],
            "edge_max_dd": edge_report["portfolio_metrics"]["max_drawdown_pct"],
            "edge_mc_dd": edge_report["portfolio_metrics"]["mc_worst_case_dd"],
            "edge_ruin_prob": edge_report["portfolio_metrics"]["ruin_probability"],
            "edge_verdict": edge_report["portfolio_metrics"]["verdict"]
        })
        return summary

    def _summarize(self, trades: List[Trade], equity_curve: List[float]) -> Dict[str, Any]:
        pnl_series = pd.Series([t.pnl for t in trades], dtype=float)
        wins = int((pnl_series > 0).sum()) if not pnl_series.empty else 0
        total = len(trades)
        net_pnl = float(pnl_series.sum())
        pf = (pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum())) if (pnl_series < 0).any() else float('inf')
        return {"status": "ok", "symbol": self.config["symbol"], "trades": total, "win_rate": wins / total if total else 0, "net_pnl": net_pnl, "profit_factor": pf, "ending_equity": float(equity_curve[-1]), "bars": len(equity_curve) - 1}

def run_backtest(config, strategy_module, csv_path=None):
    df = load_ohlcv_csv(csv_path)
    ft = build_feature_table(df)
    bt = SingleAssetBacktester(config, strategy_module)
    return bt.run(ft)
