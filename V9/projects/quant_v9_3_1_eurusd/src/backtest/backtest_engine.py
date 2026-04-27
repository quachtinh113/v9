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

    def _cost_buffer(self, price: float) -> float:
        return price * (self.spread_bps + self.slippage_bps) / 10000.0

    def run(self, feature_table: pd.DataFrame) -> Dict[str, Any]:
        trades: List[Trade] = []
        open_trade = None
        equity = self.initial_capital
        equity_curve = [equity]
        peak_equity = equity
        daily_pnl = 0.0
        loss_streak = 0
        max_bars = max(int(self.config.get("position", {}).get("timeout_minutes", 120)), 1)
        
        for _, row in feature_table.iterrows():
            ts = row["timestamp"]
            price = float(row["close_m1"])
            cost = self._cost_buffer(price)
            
            if open_trade is None:
                plan, decision = self.strategy_module.generate_trade_plan(row.to_dict(), self.config)
                if plan is not None and decision.direction in {"long", "short"}:
                    daily_dd = max((peak_equity - equity) / peak_equity * 100, 0.0) if peak_equity > 0 else 0.0
                    risk_decision = self.risk_gateway.full_gate({"daily_dd_pct": daily_dd, "loss_streak": loss_streak}, {"session_flag": row.get("session_flag", "london")})
                    if risk_decision.action == "ALLOW":
                        entry = price + cost if decision.direction == "long" else price - cost
                        open_trade = {"direction": decision.direction, "entry": entry, "entry_time": ts, "stop_loss": plan.stop_loss, "take_profit": plan.take_profit, "bars_held": 0}
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
                    equity += pnl
                    peak_equity = max(peak_equity, equity)
                    if pnl < 0: loss_streak += 1
                    else: loss_streak = 0
                    trades.append(Trade(self.config["symbol"], open_trade["direction"], str(open_trade["entry_time"]), str(ts), open_trade["entry"], exit_price, open_trade["stop_loss"], open_trade["take_profit"], pnl, open_trade["bars_held"], exit_reason))
                    open_trade = None
            equity_curve.append(equity)

        return self._summarize(trades, equity_curve)

    def _summarize(self, trades: List[Trade], equity_curve: List[float]) -> Dict[str, Any]:
        pnl_series = pd.Series([t.pnl for t in trades], dtype=float)
        wins = int((pnl_series > 0).sum()) if not pnl_series.empty else 0
        total = len(trades)
        net_pnl = float(pnl_series.sum())
        pf = (pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum())) if (pnl_series < 0).any() else float('inf')
        return {"status": "ok", "symbol": self.config["symbol"], "trades": total, "win_rate": wins / total if total else 0, "net_pnl": net_pnl, "profit_factor": pf, "ending_equity": float(equity_curve[-1])}

def run_backtest(config, strategy_module, csv_path=None):
    df = load_ohlcv_csv(csv_path)
    ft = build_feature_table(df)
    bt = SingleAssetBacktester(config, strategy_module)
    return bt.run(ft)
