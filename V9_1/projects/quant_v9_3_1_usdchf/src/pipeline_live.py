from __future__ import annotations
import logging, time, argparse
from pathlib import Path
from src.utils.config import load_yaml
from src.utils.telegram_bot import TelegramBot
from src.data.loaders import load_ohlcv_csv, resolve_csv_source
from src.data.mtf_builder import build_feature_table
from src.execution.mt5_adapter import MT5Adapter
from src.execution.order_router import OrderRouter
from src.execution.trade_journal import TradeJournal, PipelineAuditLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class LivePipeline:
    def __init__(self, root: Path):
        self.root = root
        self.config = load_yaml(root / "config" / "symbol.yaml")
        # Telegram & Model Path Setup
        tg_cfg = self.config.get("telegram", {})
        self.telegram = TelegramBot(tg_cfg.get("token"), tg_cfg.get("chat_id"), tg_cfg.get("enabled", False))
        
        self.model_path = root / "models" / "active" / "xgb_trade_filter.json"
        if not self.model_path.exists():
            # Initial fallback
            old_path = root / "models" / "xgb_trade_filter.json"
            if old_path.exists():
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy(old_path, self.model_path)

        self.symbol = self.config["symbol"]
        strategy_name = self.symbol.lower() + "_strategy"
        self.strategy = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
        
        mt5_cfg = load_yaml(root / "config" / "mt5_demo.yaml").get("mt5", {})
        exec_cfg = load_yaml(root / "config" / "mt5_demo.yaml").get("execution", {})
        self.adapter = MT5Adapter(
            login=mt5_cfg.get("login"),
            password=mt5_cfg.get("password"),
            server=mt5_cfg.get("server"),
            path=mt5_cfg.get("path"),
            enabled=mt5_cfg.get("enabled", False)
        )
        self.adapter.connect()
        self.journal = TradeJournal(root / "logs" / "live_journal.jsonl")
        self.audit_log = PipelineAuditLog(root / "logs" / "live_pipeline_audit.ndjson")
        self.router = OrderRouter(self.adapter, exec_cfg, self.journal, telegram=self.telegram)
        
        from src.core.risk_engine import RiskGateway
        self.risk_gateway = RiskGateway(self.config.get("risk", {}))
        self.equity = 100000.0
        self.peak_equity = 100000.0
        self.week_peak_equity = 100000.0
        self.loss_streak = 0
        self.last_date = None
        self.last_week = None
        
        if self.telegram.enabled:
            self.telegram.send_message(f"✅ <b>Pipeline Started</b> [{self.symbol}]\nMT5: {'Live' if self.adapter.enabled else 'Paper'}")

    def tick(self):
        csv = resolve_csv_source(self.root, self.symbol)
        df = load_ohlcv_csv(csv)
        ft = build_feature_table(df)
        if ft.empty: return
        row = ft.iloc[-1].to_dict()
        
        # Reset daily/weekly metrics at boundary crossings
        ts = row.get("timestamp")
        if ts:
            try:
                import pandas as pd
                current_date = pd.to_datetime(ts).date()
                if self.last_date is None or current_date != self.last_date:
                    self.day_start_equity = self.equity
                    self.peak_equity = self.equity
                    self.loss_streak = 0
                    self.last_date = current_date
            except Exception:
                pass
                
            try:
                import pandas as pd
                current_week = pd.to_datetime(ts).isocalendar()[:2]
                if self.last_week is None or current_week != self.last_week:
                    self.week_peak_equity = self.equity
                    self.last_week = current_week
            except Exception:
                pass

        plan, decision = self.strategy.generate_trade_plan(row, self.config)
        if plan and decision.direction in {"long", "short"}:
            print(f"Signal: {decision.direction} Score: {decision.score} ML: {decision.ml_decision}")
            
            # Drawdown and risk gateway checks
            daily_dd = max((self.peak_equity - self.equity) / self.peak_equity * 100, 0.0) if self.peak_equity > 0 else 0.0
            weekly_dd = max((self.week_peak_equity - self.equity) / self.week_peak_equity * 100, 0.0) if self.week_peak_equity > 0 else 0.0
            
            # Volatility & spread calculations for guards
            atr_ratio = float(row.get("atr_ratio", 1.0))
            from src.backtest.realism_engine import RealismSimulator
            condition = RealismSimulator.detect_market_condition(row)
            spread_multiplier = max(1.0, atr_ratio)
            if condition == "NEWS_VOLATILE":
                spread_multiplier *= 1.5
            elif condition == "LOW_LIQUIDITY":
                spread_multiplier *= 2.0
            
            base_spread_bps = float(self.config.get("backtest", {}).get("spread_bps", 2.0))
            base_slippage_bps = float(self.config.get("backtest", {}).get("slippage_bps", 1.0))
            effective_spread = base_spread_bps * spread_multiplier
            effective_slippage = base_slippage_bps * max(1.0, atr_ratio)
            
            account_data = {
                "daily_dd_pct": daily_dd,
                "weekly_dd_pct": weekly_dd,
                "loss_streak": self.loss_streak,
            }
            market_data = {
                "session_flag": row.get("session_flag", "london"),
                "spread_bps": effective_spread,
                "slippage_bps": effective_slippage,
                "atr_ratio": atr_ratio
            }
            
            risk_decision = self.risk_gateway.full_gate(account_data, market_data)
            
            # Log audit trail
            self.audit_log.write_tick(
                bar_ts=str(ts),
                regime=decision.regime,
                regime_confidence=0.85,
                signal_direction=decision.direction,
                signal_score=decision.score,
                ml_score=decision.ml_score,
                ml_decision=decision.ml_decision,
                risk_action=risk_decision.action,
                risk_reasons=risk_decision.reasons,
                execution_status="paper_only",
                position_size=plan.size
            )
            
            # Route order
            res = self.router.route_order(plan, decision, risk_decision, bar_ts=str(ts))
            print(f"Order Routing Result: {res}")

    def run_loop(self):
        while True:
            try: self.tick()
            except Exception as e: logger.error(e)
            time.sleep(60)
