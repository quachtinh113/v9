from __future__ import annotations
import os
import sys
import time
from pathlib import Path
import MetaTrader5 as mt5

# GIA CAT & QUANT FLEET ONE-SHOT ORDER PLACER (0.01 LOT / MIN LOT)
# ===============================================================
# This script logs into the running Exness MT5 demo account (272576224) 
# and routes orders for all 11 fleet symbols.
#
# Custom adjustments based on Exness specifications:
# 1. US100 maps to USTECm (Exness standard)
# 2. US500m minimum lot size is 0.03 (under 0.03 is rejected by the broker)
# 3. Filling mode uses ORDER_FILLING_IOC (fully supported by Exness indices/forex)

FLEET_AGENTS = [
    {"name": "GBPUSD", "symbol": "GBPUSD", "volume": 0.01},
    {"name": "EURUSD", "symbol": "EURUSD", "volume": 0.01},
    {"name": "USDJPY", "symbol": "USDJPY", "volume": 0.01},
    {"name": "AUDUSD", "symbol": "AUDUSD", "volume": 0.01},
    {"name": "USDCAD", "symbol": "USDCAD", "volume": 0.01},
    {"name": "USDCHF", "symbol": "USDCHF", "volume": 0.01},
    {"name": "US30",   "symbol": "US30",   "volume": 0.01},
    {"name": "US100",  "symbol": "USTEC",  "volume": 0.01}, # USTECm in Exness
    {"name": "US500",  "symbol": "US500",  "volume": 0.03}, # Min lot is 0.03
    {"name": "XAUUSD", "symbol": "XAUUSD", "volume": 0.01},
    {"name": "BTCUSD", "symbol": "BTCUSD", "volume": 0.01}
]

def place_order_for_symbol(agent: dict) -> dict:
    print(f"--------------------------------------------------")
    name = agent["name"]
    base_symbol = agent["symbol"]
    volume = agent["volume"]
    print(f"[*] Processing agent symbol: {name} (using {base_symbol}, vol={volume})")
    
    # Try selecting symbol and matching suffix (e.g. symbol + "m")
    target_symbol = base_symbol
    if not mt5.symbol_select(target_symbol, True):
        matched = False
        for suffix in ["m", "", "m1", "m2"]:
            candidate = base_symbol + suffix
            if mt5.symbol_select(candidate, True):
                target_symbol = candidate
                matched = True
                break
        if not matched:
            print(f"[-] Error: Cannot select symbol {base_symbol} or any suffix in MT5.")
            return {"symbol": name, "status": "failed", "comment": "Symbol not selected"}
    
    # Get latest tick info
    tick = mt5.symbol_info_tick(target_symbol)
    if not tick:
        print(f"[-] Error: Could not get tick info for {target_symbol}.")
        return {"symbol": name, "status": "failed", "comment": "No tick data"}
        
    ask_price = tick.ask
    
    # Build MT5 order request structure (using IOC)
    order_req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": target_symbol,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY,
        "price": ask_price,
        "deviation": 20,
        "magic": 93030,
        "comment": f"fleet_{volume}_all",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print(f"   Routing BUY {volume} {target_symbol} @ price {ask_price}...")
    res = mt5.order_send(order_req)
    
    if res is None:
        print(f"[-] Error: order_send returned None for {target_symbol}. Trying ORDER_FILLING_RETURN...")
        order_req["type_filling"] = mt5.ORDER_FILLING_RETURN
        res = mt5.order_send(order_req)
        if res is None:
            print(f"[-] Critical Error: order_send still returned None.")
            return {"symbol": name, "status": "failed", "comment": "order_send returned None"}
            
    if res.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[-] Order Failed for {target_symbol}! Retcode: {res.retcode}, Comment: {res.comment}")
        return {
            "symbol": name, 
            "status": "failed", 
            "retcode": res.retcode, 
            "comment": res.comment
        }
    
    print(f"[+] Success! Routed {target_symbol} order. Ticket: {res.order}, Price: {res.price}")
    return {
        "symbol": name,
        "status": "success",
        "ticket": res.order,
        "price": res.price,
        "volume": res.volume
    }

def main():
    print("==================================================")
    print("   QUANT FLEET ORDER DEPLOYER - 0.01 LOT ALL BOTS")
    print("==================================================")
    
    # Initialize connection to running MT5
    login = 272576224
    password = "87u3D1$6"
    server = "Exness-MT5Trial14"
    
    print(f"Initializing connection to Exness Demo Account {login}...")
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"[-] Critical Error: MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)
        
    if not mt5.login(login=login, password=password, server=server):
        print(f"[-] Critical Error: MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        sys.exit(1)
        
    print("Connected successfully. Fetching account details...")
    acc_info = mt5.account_info()
    if acc_info:
        print(f"Account: {acc_info.name} | Balance: {acc_info.balance:.2f} {acc_info.currency} | Company: {acc_info.company}")
    else:
        print("[*] Warning: Could not retrieve account details.")
        
    results = []
    for agent in FLEET_AGENTS:
        res = place_order_for_symbol(agent)
        results.append(res)
        time.sleep(0.5)
        
    mt5.shutdown()
    
    print("\n==================================================")
    print("                 FINAL VERDICT")
    print("==================================================")
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count
    
    print(f"Total processed symbols : {len(FLEET_AGENTS)}")
    print(f"Successfully placed     : {success_count}")
    print(f"Failed                  : {failed_count}")
    print("--------------------------------------------------")
    for r in results:
        status_icon = "[OK]" if r["status"] == "success" else "[ERR]"
        details = f"Ticket: {r.get('ticket')} @ {r.get('price')}" if r["status"] == "success" else f"Comment: {r.get('comment')}"
        print(f"{status_icon} {r['symbol']}: {r['status'].upper()} | {details}")
    print("==================================================")

if __name__ == "__main__":
    main()
