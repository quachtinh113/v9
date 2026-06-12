import os
import sys
from pathlib import Path

NEW_TICK_METHOD = """    def tick(self):
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
            broker_symbol = self.live_adapter.resolve_broker_symbol(self.symbol)
            symbol_visible = True
            
            latest_tick = self.live_adapter.get_latest_tick(broker_symbol)
            if latest_tick:
                from datetime import datetime, timezone
                tick_time = datetime.fromtimestamp(latest_tick.time, tz=timezone.utc)
                tick_age_seconds = (datetime.now(timezone.utc) - tick_time).total_seconds()
            
            ft, rates_sizes = self.live_adapter.build_live_feature_table(broker_symbol)
        else:
            csv = resolve_csv_source(self.root, self.symbol)
            df = load_ohlcv_csv(csv)
            ft = build_feature_table(df)
            
        if ft is None or ft.empty: return
        row = ft.iloc[-1].to_dict()
        
        if data_source == "csv" and "timestamp" in row:
            from datetime import datetime, timezone
            try:
                import pandas as pd
                ts_pd = pd.to_datetime(row["timestamp"])
                tick_age_seconds = (datetime.now(timezone.utc) - ts_pd).total_seconds()
            except: pass
        
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

        # ------------------ DYNAMIC OBSERVE HEARTBEATS ------------------
        # 1. Local Heartbeat
        try:
            import json
            from datetime import datetime, timezone
            hb_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "symbol": self.symbol,
                "ml_ok": ml_ok,
                "mt5_ok": mt5_connected,
                "tick_age": tick_age_seconds
            }
            with open(self.root / "logs" / "heartbeat.jsonl", "w") as f_hb:
                f_hb.write(json.dumps(hb_entry) + "\\n")
        except: pass

        # 2. Global Heartbeat robustly
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
                        f_ghb.write(json.dumps(hb_entry) + "\\n")
                    break
                except IOError:
                    time.sleep(0.1)
        except: pass

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

            # 4. Risk Gate Logging
            logger.info(f"[GATE:RISK] {self.symbol} - Action: {risk_decision.action}, Reasons: {risk_decision.reasons}")
                
            # Telegram critical alerts for HARD_KILL vetoes
            if risk_decision.action == "HARD_KILL" and self.telegram.enabled:
                try:
                    self.telegram.send_message(
                        f"🚨 <b>CRITICAL RISK HARD KILL TRIGGERED</b> [{self.symbol}]\\n"
                        f"Status: VETOED\\n"
                        f"Reasons: <code>{', '.join(risk_decision.reasons)}</code>\\n"
                        f"Daily Drawdown: {daily_dd:.2f}%\\n"
                        f"Weekly Drawdown: {weekly_dd:.2f}%\\n"
                        f"Loss Streak: {self.loss_streak}"
                    )
                except: pass

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
                        flog.write(json.dumps(log_entry) + "\\n")
                except: pass
            
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
            final_act = "ORDER_SENT" if res else ("BLOCKED_BY_RISK" if (risk_act != "ALLOW" and risk_act != "N/A") else f"BLOCKED_BY_SIGNAL: {decision.reason}")
            print(f"[DIAGNOSTIC] Sym: {self.symbol} | Regime: {decision.regime} | Signal: {decision.direction} ({decision.score:.0f}) | ML: {decision.ml_decision} ({decision.ml_score:.2f}) | Risk: {risk_act} | Action: {final_act}")
"""

def patch_pipeline(proj_dir):
    pipe_path = proj_dir / "src" / "pipeline_live.py"
    if not pipe_path.exists():
        print(f"File not found: {pipe_path}")
        return False
        
    with open(pipe_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Find the start of def tick(self):
    start_idx = content.find("    def tick(self):")
    if start_idx == -1:
        print(f"Could not find def tick(self): in {proj_dir.name}")
        return False
        
    # Find the start of def run_loop(self):
    end_idx = content.find("    def run_loop(self):")
    if end_idx == -1:
        print(f"Could not find def run_loop(self): in {proj_dir.name}")
        return False
        
    # Replace the tick method
    new_content = content[:start_idx] + NEW_TICK_METHOD + "\n" + content[end_idx:]
    
    with open(pipe_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Patched {proj_dir.name} successfully.")
    return True

def main():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    patched_count = 0
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            if patch_pipeline(proj):
                patched_count += 1
                
    print(f"Total patched: {patched_count} projects with heartbeats and alerts.")

if __name__ == "__main__":
    main()
