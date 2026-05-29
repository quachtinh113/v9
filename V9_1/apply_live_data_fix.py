import os
import sys
from pathlib import Path

MT5_ADAPTER_CODE = """from __future__ import annotations
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone

class MT5LiveAdapter:
    def __init__(self, login, password, server):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
        
    def initialize_mt5(self):
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            return False
        if not mt5.login(login=self.login, password=self.password, server=self.server):
            return False
        self.connected = True
        return True

    def resolve_broker_symbol(self, base_symbol):
        if not self.connected: return base_symbol
        if base_symbol.upper() == "US100":
            base_symbol = "USTEC"
        if mt5.symbol_select(base_symbol, True):
            return base_symbol
        for suffix in ["m", "c", "m1", "m2", "f", "i", "x"]:
            sym = base_symbol + suffix
            if mt5.symbol_select(sym, True):
                return sym
        # search all symbols
        all_syms = mt5.symbols_get()
        if all_syms:
            for s in all_syms:
                if s.name.startswith(base_symbol):
                    mt5.symbol_select(s.name, True)
                    return s.name
        return base_symbol

    def get_latest_tick(self, symbol):
        if not self.connected: return None
        return mt5.symbol_info_tick(symbol)

    def get_rates(self, symbol, timeframe, bars):
        if not self.connected: return None
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df.rename(columns={'time': 'timestamp', 'tick_volume': 'volume'}, inplace=True)
        return df

    def build_live_feature_table(self, symbol):
        if not self.connected:
            return None, {"M5":0, "M15":0, "H1":0, "H4":0}
            
        df_m1 = self.get_rates(symbol, mt5.TIMEFRAME_M1, 10000)
        
        rates_sizes = {
            "M5": len(self.get_rates(symbol, mt5.TIMEFRAME_M5, 10) or []),
            "M15": len(self.get_rates(symbol, mt5.TIMEFRAME_M15, 10) or []),
            "H1": len(self.get_rates(symbol, mt5.TIMEFRAME_H1, 10) or []),
            "H4": len(self.get_rates(symbol, mt5.TIMEFRAME_H4, 10) or []),
        }
        
        if df_m1 is None or df_m1.empty:
            return None, rates_sizes
            
        from src.data.mtf_builder import build_feature_table
        ft = build_feature_table(df_m1)
        return ft, rates_sizes
"""

def update_pipeline_live(proj_dir):
    pipe_path = proj_dir / "src" / "pipeline_live.py"
    if not pipe_path.exists(): return False
    
    with open(pipe_path, "r", encoding="utf-8") as f:
        content = f.read()

    # If already patched, skip
    if "mt5_live_adapter" in content:
        return True

    # Find def tick(self):
    if "def tick(self):" not in content:
        return False

    old_tick = """    def tick(self):
        csv = resolve_csv_source(self.root, self.symbol)
        df = load_ohlcv_csv(csv)
        ft = build_feature_table(df)
        if ft.empty: return
        row = ft.iloc[-1].to_dict()"""

    new_tick = """    def tick(self):
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
        
        if self.adapter.enabled and mt5_connected:  # Live mode
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
            except: pass"""

    if old_tick in content:
        content = content.replace(old_tick, new_tick)
    else:
        print(f"Could not find exact old_tick block in {proj_dir.name}")
        return False
        
    old_decision = """        plan, decision = self.strategy.generate_trade_plan(row, self.config)
        if plan and decision.direction in {"long", "short"}:"""

    new_decision = """        # Stale data guard
        stale_veto = False
        max_tick_age_seconds = 300 # 5 minutes
        if tick_age_seconds > max_tick_age_seconds and data_source == "mt5_live":
            stale_veto = True
            
        plan, decision = self.strategy.generate_trade_plan(row, self.config)
        
        if stale_veto:
            decision.direction = "flat"
            decision.reason = "STALE_MT5_TICK"

        if plan and decision.direction in {"long", "short"}:"""
        
    if old_decision in content:
        content = content.replace(old_decision, new_decision)
    else:
        print(f"Could not find old_decision block in {proj_dir.name}")
        return False

    old_risk = """            risk_decision = self.risk_gateway.full_gate(account_data, market_data)"""
    new_risk = """            risk_decision = self.risk_gateway.full_gate(account_data, market_data)
            if stale_veto:
                risk_decision.action = "HARD_KILL"
                risk_decision.reasons.append("stale_data")
                
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
                except: pass"""

    if old_risk in content:
        content = content.replace(old_risk, new_risk)
    else:
        print(f"Could not find old_risk block in {proj_dir.name}")
        return False
        
    with open(pipe_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return True

def apply_fix():
    projects_dir = Path("c:/Quant Trade/v9/V9_1/projects")
    success_count = 0
    for proj in projects_dir.iterdir():
        if proj.is_dir() and proj.name.startswith("quant_v9_3_1_"):
            # Write adapter
            adapter_path = proj / "src" / "data" / "mt5_live_adapter.py"
            with open(adapter_path, "w", encoding="utf-8") as f:
                f.write(MT5_ADAPTER_CODE)
            
            # Update pipeline
            if update_pipeline_live(proj):
                success_count += 1
                print(f"Patched {proj.name}")
            else:
                print(f"Failed to patch {proj.name}")
                
    print(f"Successfully patched {success_count} projects.")

if __name__ == "__main__":
    apply_fix()
