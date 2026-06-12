from __future__ import annotations
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class MT5Adapter:
    def __init__(self, login: int = 0, password: str = "", server: str = "", path: str = "", enabled: bool = False):
        self.login = int(login) if login else 0
        self.password = password
        self.server = server
        self.path = path
        self.enabled = enabled
        self.connected = False

    def connect(self) -> bool:
        if not self.enabled or not MT5_AVAILABLE:
            logger.info("MT5 connection bypassed: disabled or library not available. Using local paper trading mode.")
            self.connected = False
            return False
            
        try:
            # Initialize connection
            if self.path and os.path.exists(self.path):
                init_ok = mt5.initialize(path=self.path, login=self.login, password=self.password, server=self.server)
            else:
                init_ok = mt5.initialize(login=self.login, password=self.password, server=self.server)
                
            if not init_ok:
                logger.warning(f"MT5 initialize failed: {mt5.last_error()}. Falling back to paper trading.")
                self.connected = False
                return False
                
            # Login to trade account
            login_ok = mt5.login(login=self.login, password=self.password, server=self.server)
            if not login_ok:
                logger.warning(f"MT5 login failed: {mt5.last_error()}. Shutting down MT5, falling back to paper.")
                mt5.shutdown()
                self.connected = False
                return False
                
            logger.info("MT5 Adapter connected and logged in successfully.")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Error during MT5 connection: {e}. Falling back to paper trading.")
            self.connected = False
            return False

    def resolve_broker_symbol(self, base_symbol: str, audit_logger=None) -> str:
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

    def send_order(self, req: Dict[str, Any], audit_logger=None) -> Dict[str, Any]:
        if not self.connected:
            # Safe paper trading response
            return {
                "status": "paper_success",
                "price": req.get("price"),
                "symbol": req.get("symbol"),
                "direction": req.get("direction"),
                "volume": req.get("volume", 0.01),
                "order_id": 999999,
                "comment": req.get("comment", "") + " (paper)"
            }
            
        # MT5 execution logic
        symbol = req.get("symbol", "US30")
        try:
            symbol = self.resolve_broker_symbol(symbol, audit_logger=audit_logger)
        except Exception as e:
            return {
                "status": "failed",
                "comment": f"Failed to select symbol {symbol} or matches in MT5: {e}",
                "error_code": mt5.last_error()
            }

        direction = req.get("direction")
        order_type = mt5.ORDER_TYPE_BUY if direction == "long" else mt5.ORDER_TYPE_SELL
        
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {
                "status": "failed",
                "comment": f"Could not retrieve tick info for symbol {symbol}",
                "error_code": mt5.last_error()
            }
            
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # Build MT5 order request structure
        mt5_req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(req.get("volume", 0.01)),
            "type": order_type,
            "price": price,
            "sl": float(req.get("sl", 0.0)),
            "tp": float(req.get("tp", 0.0)),
            "deviation": int(req.get("deviation", 20)),
            "magic": int(req.get("magic", 93030)),
            "comment": req.get("comment", ""),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        try:
            res = mt5.order_send(mt5_req)
            if res is None:
                return {
                    "status": "failed",
                    "comment": "Order send returned None from terminal",
                    "error_code": mt5.last_error()
                }
                
            if res.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    "status": "failed",
                    "retcode": res.retcode,
                    "comment": f"Order execution failed: retcode={res.retcode}, comment={res.comment}",
                    "error_code": mt5.last_error()
                }
                
            return {
                "status": "success",
                "order_id": res.order,
                "price": res.price,
                "volume": res.volume,
                "comment": f"MT5 trade executed successfully: {res.comment}"
            }
        except Exception as e:
            return {
                "status": "failed",
                "comment": f"Exception during MT5 order_send execution: {e}"
            }


class MT5OrderRequest:
    def __init__(self, **kwargs):
        pass
