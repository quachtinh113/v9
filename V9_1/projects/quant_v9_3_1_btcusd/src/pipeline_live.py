from __future__ import annotations
import logging, time, argparse, os
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
    def __init__(self, root: Path, runtime_mode: str = "live"):
        self.root = root
        self.runtime_mode = runtime_mode
        self.execution_mode = "paper" if runtime_mode == "paper" else "live"
        self.config = load_yaml(root / "config" / "symbol.yaml")
        # Load model registry for provenance validation
        self.model_registry = load_yaml(root / "models" / "registry.yaml")
        # Determine active model entry based on model_path
        self.model_path = root / "models" / "active" / "xgb_trade_filter.json"
        # Find matching entry in registry
        entry = next((m for m in self.model_registry.get('models', []) if m.get('model_path') == str(self.model_path)), None)
        if entry is None:
            # Fallback to legacy path handling (same as before)
            old_path = root / "models" / "xgb_trade_filter.json"
            if old_path.exists():
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy(old_path, self.model_path)
            entry = next((m for m in self.model_registry.get('models', []) if m.get('model_path') == str(self.model_path)), None)
        # Extract provenance fields
        if entry:
            self.model_id = entry.get('model_id')
            self.model_status = entry.get('status')
            self.allowed_to_block = entry.get('allowed_to_block', False)
        else:
            self.model_id = None
            self.model_status = None
            self.allowed_to_block = False
        # Determine ML gate mode based on registry fields
        if not self.allowed_to_block:
            self.ml_gate_mode = "observe_only"
            self.model_provenance_valid = False
        else:
            self.ml_gate_mode = "block"
            self.model_provenance_valid = True
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
        # Pass execution mode into router config
        exec_cfg["mode"] = self.execution_mode
        self.journal = TradeJournal(root / "logs" / "live_journal.jsonl")
        self.audit_log = PipelineAuditLog(root / "logs" / "live_pipeline_audit.ndjson")
        if self.execution_mode == "live":
            try:
                assert self.runtime_mode == "live", f"BLOCKED: self.runtime_mode must be 'live' (current: {self.runtime_mode})"
                assert os.getenv("ALLOW_REAL_TRADING") == "true", "ALLOW_REAL_TRADING is not true"
                assert os.getenv("HUMAN_LIVE_CONFIRM") == "YES_I_ACCEPT_LIVE_RISK", "HUMAN_LIVE_CONFIRM is not YES_I_ACCEPT_LIVE_RISK"
                assert os.getenv("LIVE_DEMO_ALLOWED") == "true", "LIVE_DEMO_ALLOWED is not true"
                
                import MetaTrader5 as mt5
                acc_info = mt5.account_info()
                if acc_info is None:
                    raise AssertionError("Could not retrieve MetaTrader5 account info for live mode verification")
                
                trade_mode = getattr(acc_info, 'trade_mode', None)
                if trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO and trade_mode != 0:
                    raise AssertionError(f"BLOCKED: Live execution ONLY allowed on DEMO account (trade_mode={trade_mode})")
                if trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL or trade_mode == 2:
                    raise AssertionError(f"BLOCKED: Live execution attempted on a REAL account (trade_mode={trade_mode})")
                
                server = str(getattr(acc_info, 'server', '')).lower()
                if "real" in server or "live" in server or "prod" in server:
                    raise AssertionError(f"BLOCKED: Live execution attempted on a REAL server ({getattr(acc_info, 'server')})")
                
                print(f"[SECURITY CONTROL] Live demo verification successful. Server: {getattr(acc_info, 'server')}, Login: {getattr(acc_info, 'login')}")
            except AssertionError as e:
                self.audit_log.write_blocked("LIVE_PERMISSION_NOT_CONFIRMED", self.symbol, stage="EXECUTION", details={"error": str(e)})
                raise RuntimeError(f"LIVE_PERMISSION_NOT_CONFIRMED: Live mode blocked for {self.symbol} due to assertion failure: {e}")
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
        # Startup summary prints
        print(f"Runtime Mode   : {self.runtime_mode}")
        print("Data Source    : MT5_REALTIME")
        print(f"Execution Mode : {'PAPER' if self.execution_mode == 'paper' else 'LIVE'}")
        print(f"Real Order Send Enabled: {self.execution_mode == 'live'}")

    def tick(self):
        tick_ok = False
        data_stale = False
        regime_result = "N/A"
        signal_result = "N/A"
        risk_decision = "N/A"
        execution_mode = self.execution_mode
        order_send_called = False
        broker_symbol = self.symbol
        ml_mode = "observe_only"
        ml_score = 0.0
        
        self.last_tick_metrics = {
            "broker_symbol": self.symbol,
            "data_stale": False,
            "regime_result": "N/A",
            "signal_result": "N/A",
            "ml_mode": "observe_only",
            "ml_score": 0.0,
            "risk_decision": "N/A",
            "order_send_called": False,
            "ml_ok": True,
            "mt5_ok": False,
            "tick_age": 999999999
        }
        
        try:
            self._tick_internal()
            tick_ok = True
            
            # Read variables set during the run
            metrics = getattr(self, "last_tick_metrics", {})
            broker_symbol = metrics.get("broker_symbol", self.symbol)
            data_stale = metrics.get("data_stale", False)
            regime_result = metrics.get("regime_result", "N/A")
            signal_result = metrics.get("signal_result", "N/A")
            ml_mode = metrics.get("ml_mode", "observe_only")
            ml_score = metrics.get("ml_score", 0.0)
            risk_decision = metrics.get("risk_decision", "N/A")
            order_send_called = metrics.get("order_send_called", False)
            
        except Exception as e:
            from src.core.models import DataIncompleteError
            if not isinstance(e, DataIncompleteError):
                stage = "DATA"
                if "Risk" in type(e).__name__ or "risk" in str(e).lower():
                    stage = "RISK"
                elif "Order" in type(e).__name__ or "router" in str(e).lower():
                    stage = "EXECUTION"
                elif "Strategy" in type(e).__name__:
                    stage = "SIGNAL"
                
                if hasattr(self, 'audit_log') and self.audit_log:
                    self.audit_log.write_blocked(
                        reason="UNHANDLED_EXCEPTION",
                        symbol=self.symbol,
                        stage=stage,
                        details={"error_type": type(e).__name__, "message": str(e)}
                    )
            logger.error(f"Error in tick: {e}")
            raise e
        finally:
            # 1. Write Heartbeats
            try:
                import json
                from datetime import datetime, timezone
                metrics = getattr(self, "last_tick_metrics", {})
                (self.root / "logs").mkdir(parents=True, exist_ok=True)
                hb_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "symbol": self.symbol,
                    "ml_ok": metrics.get("ml_ok", True),
                    "mt5_ok": metrics.get("mt5_ok", False),
                    "tick_age": metrics.get("tick_age", 999999999)
                }
                with open(self.root / "logs" / "heartbeat.jsonl", "w") as f_hb:
                    f_hb.write(json.dumps(hb_entry) + "\n")
            except Exception as e:
                if hasattr(self, 'audit_log') and self.audit_log:
                    self.audit_log.write_blocked(
                        reason="LOCAL_HEARTBEAT_FAILED",
                        symbol=self.symbol,
                        stage="DATA",
                        details={"error": str(e)}
                    )

            try:
                import json, time
                from datetime import datetime, timezone
                global_hb = self.root.parents[2] / "logs" / "heartbeat.jsonl"
                global_hb.parent.mkdir(parents=True, exist_ok=True)
                hb_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "symbol": self.symbol
                }
                for _ in range(5):
                    try:
                        with open(global_hb, "w") as f_ghb:
                            f_ghb.write(json.dumps(hb_entry) + "\n")
                        break
                    except IOError as e:
                        time.sleep(0.1)
            except Exception as e:
                if hasattr(self, 'audit_log') and self.audit_log:
                    self.audit_log.write_blocked(
                        reason="GLOBAL_HEARTBEAT_FAILED",
                        symbol=self.symbol,
                        stage="DATA",
                        details={"error": str(e)}
                    )

            # 2. Write Loop Audit Log
            if hasattr(self, 'audit_log') and self.audit_log:
                self.audit_log.write_loop_audit(
                    symbol=self.symbol,
                    tick_ok=tick_ok,
                    broker_symbol=broker_symbol,
                    data_stale=data_stale,
                    regime_result=regime_result,
                    signal_result=signal_result,
                    ml_mode=ml_mode,
                    ml_score=ml_score,
                    risk_decision=risk_decision,
                    execution_mode=execution_mode,
                    order_send_called=order_send_called,
                    ml_gate_mode=getattr(self, "ml_gate_mode", "observe_only"),
                    ml_block_applied=decision.ml_decision == "BLOCK" and getattr(self, "ml_gate_mode", "observe_only") != "observe_only",
                    ml_reason=decision.ml_reason,
                    model_provenance_valid=getattr(self, "model_provenance_valid", False)
                )

    def _tick_internal(self):
        self.last_tick_metrics = {
            "broker_symbol": self.symbol,
            "data_stale": False,
            "regime_result": "N/A",
            "signal_result": "N/A",
            "ml_mode": "observe_only",
            "ml_score": 0.0,
            "risk_decision": "N/A",
            "order_send_called": False
        }
        # MT5 Live Data Adapter Integration
        if not hasattr(self, 'live_adapter'):
            from src.data.mt5_live_adapter import MT5LiveAdapter
            mt5_cfg = load_yaml(self.root / "config" / "mt5_demo.yaml").get("mt5", {})
            self.live_adapter = MT5LiveAdapter(
                login=mt5_cfg.get("login"),
                password=mt5_cfg.get("password"),
                server=mt5_cfg.get("server")
            )
            self.live_adapter.initialize_mt5()
        
        data_source = "csv"
        rates_sizes = {"M5":0, "M15":0, "H1":0, "H4":0}
        tick_age_seconds = 999999999
        mt5_connected = self.live_adapter.connected
        symbol_visible = False
        broker_symbol = self.symbol
        tick_time = None
        
        if mt5_connected:  # Data feed always enabled in both modes
            data_source = "mt5_live"
            broker_symbol = self.live_adapter.resolve_broker_symbol(self.symbol, self.audit_log)
            symbol_visible = True
            
            latest_tick = self.live_adapter.get_latest_tick(broker_symbol)
            if latest_tick:
                from datetime import datetime, timezone
                tick_time = datetime.fromtimestamp(latest_tick.time, tz=timezone.utc)
                tick_age_seconds = (datetime.now(timezone.utc) - tick_time).total_seconds()
            
            ft, rates_sizes = self.live_adapter.build_live_feature_table(broker_symbol, self.audit_log)
        else:
            csv = resolve_csv_source(self.root, self.symbol)
            df = load_ohlcv_csv(csv)
            ft = build_feature_table(df)
            
        if ft is None or ft.empty:
            self.audit_log.write_blocked(
                reason="EMPTY_OR_NONE_FEATURE_TABLE",
                symbol=self.symbol,
                stage="DATA",
                details={"data_source": data_source, "mt5_connected": mt5_connected}
            )
            from src.core.models import DataIncompleteError
            raise DataIncompleteError("Feature table is empty or None")
        row = ft.iloc[-1].to_dict()
        
        if data_source == "csv" and "timestamp" in row:
            from datetime import datetime, timezone
            try:
                import pandas as pd
                ts_pd = pd.to_datetime(row["timestamp"])
                tick_age_seconds = (datetime.now(timezone.utc) - ts_pd).total_seconds()
            except Exception as e:
                self.audit_log.write_blocked(
                    reason="TIMESTAMP_PARSE_FAILED",
                    symbol=self.symbol,
                    stage="DATA",
                    details={"error": str(e)}
                )
        
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
            except Exception as e:
                self.audit_log.write_blocked(
                    reason="DAILY_METRIC_RESET_FAILED",
                    symbol=self.symbol,
                    stage="DATA",
                    details={"error": str(e)}
                )
                
            try:
                import pandas as pd
                current_week = pd.to_datetime(ts).isocalendar()[:2]
                if self.last_week is None or current_week != self.last_week:
                    self.week_peak_equity = self.equity
                    self.last_week = current_week
            except Exception as e:
                self.audit_log.write_blocked(
                    reason="WEEKLY_METRIC_RESET_FAILED",
                    symbol=self.symbol,
                    stage="DATA",
                    details={"error": str(e)}
                )

        # Stale data guard
        stale_veto = False
        max_tick_age_seconds = 300 # 5 minutes
        if tick_age_seconds > max_tick_age_seconds and data_source == "mt5_live":
            stale_veto = True
            
        plan, decision = self.strategy.generate_trade_plan(row, self.config)
        
        if stale_veto:
            decision.direction = "flat"
            decision.reason = "STALE_MT5_TICK"
            decision.blocked_reasons.append("stale_data_veto")

        # Determine ML loading status
        ml_ok = True
        if decision and decision.ml_decision == "BLOCK" and "ML Error" in getattr(decision, "ml_reason", ""):
            ml_ok = False

        self.last_tick_metrics["broker_symbol"] = broker_symbol
        self.last_tick_metrics["data_stale"] = stale_veto
        if decision:
            self.last_tick_metrics["regime_result"] = decision.regime
            self.last_tick_metrics["signal_result"] = decision.direction
            self.last_tick_metrics["ml_score"] = float(getattr(decision, "ml_score", 0.0))
            self.last_tick_metrics["ml_mode"] = "observe_only"

        # Stage bypass/block auditing
        if not (plan and decision.direction in {"long", "short"}):
            self.audit_log.write_blocked(
                reason="STRATEGY_FLAT" if decision.direction == "flat" else "NO_STRATEGY_PLAN",
                symbol=self.symbol,
                stage="SIGNAL",
                details={
                    "regime": decision.regime,
                    "direction": decision.direction,
                    "blocked_reasons": decision.blocked_reasons,
                    "indicators": {
                        "rsi14_m15": row.get("rsi14_m15"),
                        "adx14_h1": row.get("adx14_h1"),
                        "atr14_m1": row.get("atr14_m1")
                    }
                }
            )
        
        if decision and decision.ml_decision == "BLOCK":
            if getattr(self, "ml_gate_mode", "observe_only") != "observe_only":
                # Apply ML block as configured
                self.audit_log.write_blocked(
                    reason="ML_GATEKEEPER_BLOCK",
                    symbol=self.symbol,
                    stage="SIGNAL",
                    details={
                        "ml_score": decision.ml_score,
                        "ml_reason": decision.ml_reason
                    }
                )
            else:
                # In observe_only mode, record that block was not applied
                decision.ml_reason = "model_provenance_missing"
                # No audit_block written; will be captured in loop audit

        # Heartbeat variables are stored in self.last_tick_metrics and written in the finally block of tick()
        self.last_tick_metrics["ml_ok"] = ml_ok
        self.last_tick_metrics["mt5_ok"] = mt5_connected
        self.last_tick_metrics["tick_age"] = tick_age_seconds

        # ------------------ PIPELINE GATE LOGGING ------------------
        # 1. Regime Gate
        logger.info(f"[GATE:REGIME] {self.symbol} - Regime: {decision.regime} (ADX H1: {row.get('adx14_h1', 0.0):.1f}, ATR Ratio: {row.get('atr_ratio', 1.0):.2f})")
        
        # 2. Signal Gate
        logger.info(f"[GATE:SIGNAL] {self.symbol} - Direction: {decision.direction}, Score: {decision.score}, Blocks: {decision.blocked_reasons}")
        
        # 3. ML Gate
        logger.info(f"[GATE:ML] {self.symbol} - Score: {decision.ml_score:.4f}, Decision: {decision.ml_decision}, Reason: {decision.ml_reason}")
        
        risk_decision = None
        res = None
        
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
            if stale_veto:
                risk_decision.action = "HARD_KILL"
                risk_decision.reasons.append("stale_data")

            self.last_tick_metrics["risk_decision"] = risk_decision.action

            # Risk Stage Veto Auditing
            if risk_decision.action != "ALLOW":
                self.audit_log.write_blocked(
                    reason=risk_decision.action,
                    symbol=self.symbol,
                    stage="RISK",
                    details={
                        "reasons": risk_decision.reasons,
                        "account_data": account_data,
                        "market_data": market_data
                    }
                )

            # 4. Risk Gate Logging
            logger.info(f"[GATE:RISK] {self.symbol} - Action: {risk_decision.action}, Reasons: {risk_decision.reasons}")
                
            # Telegram critical alerts for HARD_KILL vetoes
            if risk_decision.action == "HARD_KILL" and self.telegram.enabled:
                try:
                    self.telegram.send_message(
                        f"🚨 <b>CRITICAL RISK HARD KILL TRIGGERED</b> [{self.symbol}]\n"
                        f"Status: VETOED\n"
                        f"Reasons: <code>{', '.join(risk_decision.reasons)}</code>\n"
                        f"Daily Drawdown: {daily_dd:.2f}%\n"
                        f"Weekly Drawdown: {weekly_dd:.2f}%\n"
                        f"Loss Streak: {self.loss_streak}"
                    )
                except Exception as e:
                    self.audit_log.write_blocked(
                        reason="TELEGRAM_SEND_FAILED",
                        symbol=self.symbol,
                        stage="RISK",
                        details={"error": str(e)}
                    )

            # Logging before NO_TRADE/VETO
            if decision.direction == "flat" or risk_decision.action != "ALLOW":
                try:
                    import json
                    from datetime import datetime, timezone
                    log_entry = {
                        "timestamp": str(datetime.now(timezone.utc)),
                        "internal_symbol": self.symbol,
                        "broker_symbol": broker_symbol,
                        "mt5_connected": mt5_connected,
                        "tick_time": str(tick_time) if tick_time else None,
                        "tick_age_seconds": tick_age_seconds,
                        "rates_rows_M5": rates_sizes.get("M5", 0),
                        "rates_rows_M15": rates_sizes.get("M15", 0),
                        "rates_rows_H1": rates_sizes.get("H1", 0),
                        "rates_rows_H4": rates_sizes.get("H4", 0),
                        "data_source": data_source,
                        "decision": decision.direction,
                        "reason_code": "stale_data" if stale_veto else ("strategy_flat" if decision.direction == "flat" else risk_decision.action),
                        "reason_text": getattr(decision, "reason", "") + " | " + str(risk_decision.reasons),
                        "indicator_values": {k: v for k, v in row.items() if isinstance(v, (int, float))}
                    }
                    with open(self.root / "logs" / "no_entry_audit.jsonl", "a") as flog:
                        flog.write(json.dumps(log_entry) + "\n")
                except Exception as e:
                    self.audit_log.write_blocked(
                        reason="NO_ENTRY_AUDIT_LOG_FAILED",
                        symbol=self.symbol,
                        stage="DATA",
                        details={"error": str(e)}
                    )
            
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
                execution_status=self.execution_mode,
                position_size=plan.size
            )
            
            # Route order
            if risk_decision.action == "ALLOW":
                # 5. Execution Gate Logging
                logger.info(f"[GATE:EXECUTION] {self.symbol} - Approved. Sending order size: {plan.size}")
                self.last_tick_metrics["order_send_called"] = True
                res = self.router.route_order(plan, decision, risk_decision, bar_ts=str(ts))
                print(f"Order Routing Result: {res}")
            else:
                logger.info(f"[GATE:EXECUTION] {self.symbol} - Blocked by risk. No order sent.")
        else:
            # 5. Execution Gate Logging
            logger.info(f"[GATE:EXECUTION] {self.symbol} - Flat or no signal. No order sent.")

        # ------------------ DIAGNOSTIC MODE SUMMARY ------------------
        import os
        if os.getenv("DIAGNOSTIC_MODE", "false").lower() == "true":
            risk_act = risk_decision.action if risk_decision else "N/A"
            risk_reasons = risk_decision.reasons if risk_decision else []
            final_act = "ORDER_SENT" if res else ("BLOCKED_BY_RISK" if (risk_act != "ALLOW" and risk_act != "N/A") else f"BLOCKED_BY_SIGNAL")
            all_blocks = decision.blocked_reasons + risk_reasons
            
            ts_val = row.get("timestamp", "N/A")
            raw_sig = getattr(decision, "raw_signal", decision.direction)
            ml_thresh = self.config.get("ml", {}).get("block_threshold", 0.50)
            
            # Extract indicators safely
            rsi_m15 = row.get("rsi14_m15", 0.0)
            adx_val = row.get("adx14_h1", 0.0)
            atr_val = row.get("atr14_m1", 0.001)
            
            h1_bias = row.get("bias_h1", "flat")
            h4_bias = row.get("bias_h4", "flat")
            m15_bias = row.get("bias", "flat")
            pullback_detected = "true" if getattr(decision, "pullback_detected", False) else "false"
            score_before_pb = getattr(decision, "score_before_pullback", decision.score)
            score_after_pb = getattr(decision, "score_after_pullback", decision.score)
            entry_reasons = getattr(decision, "entry_reasons", [])
            blocked_reasons = decision.blocked_reasons
            
            print(f"[DIAGNOSTIC] symbol={self.symbol} | timestamp={ts_val} | regime={decision.regime} | rsi_m15={rsi_m15:.2f} | rsi_h1=N/A | rsi_h4=N/A | adx={adx_val:.2f} | atr={atr_val:.6f} | raw_signal={raw_sig} | signal_score={decision.score:.0f} | ml_score={decision.ml_score:.4f} | ml_threshold={ml_thresh:.2f} | ml_decision={decision.ml_decision} | risk_decision={risk_act} | final_action={final_act} | block_reason={blocked_reasons} | entry_reasons={entry_reasons} | h1_bias={h1_bias} | h4_bias={h4_bias} | m15_bias={m15_bias} | pullback_detected={pullback_detected} | score_before_pullback={score_before_pb:.0f} | score_after_pullback={score_after_pb:.0f}")

    def run_loop(self):
        while True:
            try: self.tick()
            except Exception as e: logger.error(e)
            time.sleep(60)
