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
        self.adapter = MT5Adapter(enabled=mt5_cfg.get("enabled", False))
        self.journal = TradeJournal(root / "logs" / "live_journal.jsonl")
        self.audit_log = PipelineAuditLog(root / "logs" / "live_pipeline_audit.ndjson")
        self.router = OrderRouter(self.adapter, exec_cfg, telegram=self.telegram)
        
        if self.telegram.enabled:
            self.telegram.send_message(f"✅ <b>Pipeline Started</b> [{self.symbol}]\nMT5: {'Live' if self.adapter.enabled else 'Paper'}")
        
        if self.telegram.enabled:
            self.telegram.send_message(f"✅ <b>Pipeline Started</b> [{self.symbol}]\nMT5: {'Live' if self.adapter.enabled else 'Paper'}")

    def tick(self):
        csv = resolve_csv_source(self.root, self.symbol)
        df = load_ohlcv_csv(csv)
        ft = build_feature_table(df)
        if ft.empty: return
        row = ft.iloc[-1].to_dict()
        plan, decision = self.strategy.generate_trade_plan(row, self.config)
        if plan:
            print(f"Signal: {decision.direction} Score: {decision.score}")
            # Risk/Route logic...

    def run_loop(self):
        while True:
            try: self.tick()
            except Exception as e: logger.error(e)
            time.sleep(60)
