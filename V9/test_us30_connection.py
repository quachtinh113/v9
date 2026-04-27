import MetaTrader5 as mt5
import sys

def test_connection():
    login = 272576224
    password = "87u3D1$6"
    server = "Exness-MT5Trial14"
    
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"Initialize failed, error code: {mt5.last_error()}")
        return False
        
    print("MT5 initialized successfully")
    
    # Try to login
    if not mt5.login(login=login, password=password, server=server):
        print(f"Login failed, error code: {mt5.last_error()}")
        mt5.shutdown()
        return False
        
    print("Logged in successfully")
    
    account_info = mt5.account_info()
    if account_info:
        print(f"Account Info: Balance={account_info.balance}, Equity={account_info.equity}, Company={account_info.company}")
    else:
        print("Failed to get account info")
        
    # Check US30 symbol
    symbol = "US30m"
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
    else:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"Symbol {symbol} Tick: Ask={tick.ask}, Bid={tick.bid}")
        else:
            print(f"No tick data for {symbol}")
            
    mt5.shutdown()
    return True

if __name__ == "__main__":
    test_connection()
