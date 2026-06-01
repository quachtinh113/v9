import json
from pathlib import Path

def trace_signal(root_path: str, symbol: str) -> dict:
    """Trace the signal generation path for a given symbol.
    Returns a JSON‑serialisable dict with keys:
      - symbol
      - market_data_file
      - feature_builder_file
      - regime_engine_file
      - signal_engine_file
      - ml_gatekeeper_file
      - risk_engine_file
      - execution_router_file
    The function only reads file names; it does not execute any trading logic.
    """
    # Simplified mapping based on project conventions
    base = Path(root_path)
    mapping = {
        "market_data_file": "src/data/mt5_live_adapter.py",
        "feature_builder_file": "src/feature_builder.py",
        "regime_engine_file": "src/core/regime_engine.py",
        "signal_engine_file": "src/core/signal_engine.py",
        "ml_gatekeeper_file": "src/ml/xgb_filter.py",
        "risk_engine_file": "src/core/risk_engine.py",
        "execution_router_file": "src/execution/order_router.py",
    }
    result = {"symbol": symbol}
    result.update(mapping)
    return result

if __name__ == "__main__":
    import sys, pprint
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    symbol = sys.argv[2] if len(sys.argv) > 2 else 'BTCUSD'
    pprint.pprint(trace_signal(root, symbol))
