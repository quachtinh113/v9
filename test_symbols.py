import MetaTrader5 as mt5

def main():
    login = 272576224
    password = "87u3D1$6"
    server = "Exness-MT5Trial14"
    path = "C:/Program Files/MetaTrader 5/terminal64.exe"
    
    if not mt5.initialize(path=path, login=login, password=password, server=server):
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
        
    if not mt5.login(login=login, password=password, server=server):
        print(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return
        
    print("Connected to MT5 successfully!")
    
    symbols = mt5.symbols_get()
    print(f"Total symbols found: {len(symbols) if symbols is not None else 0}")
    
    print("\nMatching US100/Nasdaq/Index symbols:")
    if symbols:
        for s in symbols:
            name = s.name.upper()
            if "100" in name or "USTEC" in name or "NAS" in name or "TEC" in name or "US30" in name:
                print(f"  - {s.name} (Visible: {s.visible})")
                
    mt5.shutdown()

if __name__ == "__main__":
    main()
