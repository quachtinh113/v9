import MetaTrader5 as mt5

def list_symbols():
    login = 272576224
    password = "87u3D1$6"
    server = "Exness-MT5Trial14"

    if not mt5.initialize(login=login, password=password, server=server):
        print(f"Initialize failed: {mt5.last_error()}")
        return

    if not mt5.login(login=login, password=password, server=server):
        print(f"Login failed: {mt5.last_error()}")
        mt5.shutdown()
        return

    print("Connected successfully!\n")

    # Get all symbols
    symbols = mt5.symbols_get()
    if not symbols:
        print("No symbols found")
        mt5.shutdown()
        return

    # Search for index-related symbols (US30, US100, US500, NAS, etc.)
    search_terms = ["US30", "US100", "US500", "NAS", "USTEC", "SPX", "DJ", "DOW",
                    "GBP", "EUR", "USD", "AUD", "CHF", "JPY", "XAU", "GOLD"]

    print(f"Total symbols available: {len(symbols)}\n")
    print("=" * 60)
    print("MATCHING SYMBOLS FOR YOUR AGENTS:")
    print("=" * 60)

    for term in search_terms:
        matches = [s.name for s in symbols if term.upper() in s.name.upper()]
        if matches:
            print(f"\n  [{term}] -> {', '.join(sorted(matches)[:10])}")

    print("\n" + "=" * 60)
    print("ALL AVAILABLE SYMBOLS:")
    print("=" * 60)
    for s in sorted(symbols, key=lambda x: x.name):
        print(f"  {s.name}")

    mt5.shutdown()

if __name__ == "__main__":
    list_symbols()
