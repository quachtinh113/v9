import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

def main():
    print("=====================================================")
    print("  7-DAY LIVE MT5 TRADES & DEALS AUDIT")
    print("=====================================================\n")
    
    login = 272576224
    password = "87u3D1$6"
    server = "Exness-MT5Trial14"
    
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
        
    if not mt5.login(login=login, password=password, server=server):
        print(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return
        
    print("Connected to MT5 successfully!")
    
    # 1. Get current active positions
    positions = mt5.positions_get()
    print(f"\nActive Positions Count: {len(positions) if positions is not None else 0}")
    if positions:
        print("-" * 65)
        print(f"{'Position ID':<12} | {'Symbol':<10} | {'Type':<6} | {'Volume':<6} | {'Price':<10} | {'Profit':<8}")
        print("-" * 65)
        for pos in positions:
            pos_type = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
            print(f"{pos.ticket:<12} | {pos.symbol:<10} | {pos_type:<6} | {pos.volume:<6.2f} | {pos.price_open:<10.5f} | {pos.profit:<8.2f}")
            
    # 2. Get history deals from last 7 days
    from_date = datetime.now(timezone.utc) - timedelta(days=7)
    deals = mt5.history_deals_get(from_date)
    print(f"\nExecuted History Deals (Last 7 Days): {len(deals) if deals is not None else 0}")
    if deals:
        print("-" * 85)
        print(f"{'Deal ID':<10} | {'Order ID':<10} | {'Symbol':<10} | {'Type':<6} | {'Volume':<6} | {'Price':<10} | {'Profit':<8} | {'Time (UTC)'}")
        print("-" * 85)
        for d in deals:
            d_type = "BUY" if d.type == mt5.DEAL_TYPE_BUY else ("SELL" if d.type == mt5.DEAL_TYPE_SELL else "OTHER")
            d_time = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{d.ticket:<10} | {d.order:<10} | {d.symbol:<10} | {d_type:<6} | {d.volume:<6.2f} | {d.price:<10.5f} | {d.profit:<8.2f} | {d_time}")
            
    # 3. Get history orders from last 7 days
    orders = mt5.history_orders_get(from_date)
    print(f"\nHistory Orders (Last 7 Days): {len(orders) if orders is not None else 0}")
    if orders:
        print("-" * 85)
        print(f"{'Order ID':<10} | {'Symbol':<10} | {'Type':<6} | {'Volume':<6} | {'Price':<10} | {'State':<15} | {'Time (UTC)'}")
        print("-" * 85)
        for o in orders:
            o_type = "BUY" if o.type == mt5.ORDER_TYPE_BUY else ("SELL" if o.type == mt5.ORDER_TYPE_SELL else "OTHER")
            o_time = datetime.fromtimestamp(o.time_setup, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            state_desc = "UNKNOWN"
            if o.state == mt5.ORDER_STATE_STARTED: state_desc = "STARTED"
            elif o.state == mt5.ORDER_STATE_PLACED: state_desc = "PLACED"
            elif o.state == mt5.ORDER_STATE_CANCELED: state_desc = "CANCELED"
            elif o.state == mt5.ORDER_STATE_PARTIAL: state_desc = "PARTIAL"
            elif o.state == mt5.ORDER_STATE_FILLED: state_desc = "FILLED"
            elif o.state == mt5.ORDER_STATE_REJECTED: state_desc = "REJECTED"
            elif o.state == mt5.ORDER_STATE_EXPIRED: state_desc = "EXPIRED"
            print(f"{o.ticket:<10} | {o.symbol:<10} | {o_type:<6} | {o.volume_initial:<6.2f} | {o.price_open:<10.5f} | {state_desc:<15} | {o_time}")

    mt5.shutdown()

if __name__ == "__main__":
    main()
