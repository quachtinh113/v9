from __future__ import annotations
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

    def resolve_broker_symbol(self, base_symbol, audit_logger=None):
        if not self.connected: return base_symbol
        mappings = {
            "US100": "USTECm",
            "US30": "US30m",
            "US500": "US500m"
        }
        symbol_upper = base_symbol.upper()
        if symbol_upper in mappings:
            mapped_symbol = mappings[symbol_upper]
            if mt5.symbol_select(mapped_symbol, True):
                return mapped_symbol
            base_symbol = mappings[symbol_upper][:-1]
            
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
                if s.name.upper() == base_symbol.upper() or s.name.upper() == (base_symbol + "M").upper():
                    mt5.symbol_select(s.name, True)
                    return s.name
                    
        if audit_logger:
            audit_logger.write_blocked("SYMBOL_UNRESOLVED", base_symbol)
        from src.core.models import DataIncompleteError
        raise DataIncompleteError(f"Symbol {base_symbol} could not be resolved on MT5 broker.")

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

    def build_live_feature_table(self, symbol, audit_logger=None):
        if not self.connected:
            return None, {"M5":0, "M15":0, "H1":0, "H4":0}
            
        df_m1 = self.get_rates(symbol, mt5.TIMEFRAME_M1, 10000)
        
        df_m5 = self.get_rates(symbol, mt5.TIMEFRAME_M5, 10)
        df_m15 = self.get_rates(symbol, mt5.TIMEFRAME_M15, 10)
        df_h1 = self.get_rates(symbol, mt5.TIMEFRAME_H1, 10)
        df_h4 = self.get_rates(symbol, mt5.TIMEFRAME_H4, 10)
        
        rates_sizes = {
            "M5": len(df_m5) if df_m5 is not None else 0,
            "M15": len(df_m15) if df_m15 is not None else 0,
            "H1": len(df_h1) if df_h1 is not None else 0,
            "H4": len(df_h4) if df_h4 is not None else 0,
        }
        
        if df_m1 is None or df_m1.empty:
            if audit_logger:
                audit_logger.write_blocked("DATA_STALE_OR_UNRESOLVED", symbol)
            from src.core.models import DataIncompleteError
            raise DataIncompleteError(f"M1 rates data for {symbol} is None or empty.")
            
        from src.data.mtf_builder import build_feature_table
        ft = build_feature_table(df_m1)
        return ft, rates_sizes
