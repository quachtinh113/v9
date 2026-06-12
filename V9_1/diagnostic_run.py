import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import MetaTrader5 as mt5

def clear_src_modules():
    to_delete = [m for m in sys.modules if m.startswith('src.') or m == 'src']
    for m in to_delete:
        del sys.modules[m]

def signal_trace(symbol):
    print(f"\n{'='*50}\nSignal Trace: {symbol}\n{'='*50}")
    repo_name = f"quant_v9_3_1_{symbol.lower()}"
    root = Path(f"C:/Quant Trade/v9/V9_1/projects/{repo_name}")
    clear_src_modules()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
        
    original_cwd = os.getcwd()
    os.chdir(str(root)) # Fix relative paths for ML models
    
    try:
        from src.data.mt5_live_adapter import MT5LiveAdapter
        from src.utils.config import load_yaml
        config = load_yaml(root / "config" / "symbol.yaml")
        mt5_cfg = load_yaml(root / "config" / "mt5_demo.yaml").get("mt5", {})
        
        adapter = MT5LiveAdapter(
            login=mt5_cfg.get("login"),
            password=mt5_cfg.get("password"),
            server=mt5_cfg.get("server")
        )
        adapter.initialize_mt5()
        broker_symbol = adapter.resolve_broker_symbol(symbol)
        ft, rates = adapter.build_live_feature_table(broker_symbol)
        
        if ft is None or ft.empty:
            print("Failed to build feature table.")
            return
            
        row = ft.iloc[-1].to_dict()
        
        strategy_name = symbol.lower() + "_strategy"
        strategy = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
        
        print("\n--- 1. Raw Strategy Evaluation ---")
        from src.core.signal_engine import evaluate_signal
        dec_raw = evaluate_signal(row, config)
        print(f"Regime: {dec_raw.regime}")
        print(f"Score: {dec_raw.score} / {config.get('entry', {}).get('score_threshold', 70)}")
        print(f"Gate Status: {dec_raw.gate_status}")
        print(f"Gate Blocks: {dec_raw.blocked_reasons}")
        
        print("\n--- 2. Passes ---")
        print(f"  Regime Pass: True (assumed if not in blocked_reasons)")
        print(f"  Session Pass: {dec_raw.session_pass}")
        print(f"  RSI Pass: {dec_raw.rsi_mtf_pass}")
        print(f"  ADX Pass: {dec_raw.adx_pass}")
        print(f"  ATR Pass: {dec_raw.atr_pass}")
        print(f"  Alignment Pass: {dec_raw.direction_alignment_pass}")
        
        print("\n--- 3. ML Filter ---")
        print(f"ML Decision: {dec_raw.ml_decision}")
        print(f"ML Score: {dec_raw.ml_score}")
        print(f"ML Reason: {getattr(dec_raw, 'ml_reason', 'N/A')}")
        
        print("\n--- 4. Position Plan Evaluation ---")
        plan, dec_final = strategy.generate_trade_plan(row, config)
        print(f"Final Direction: {dec_final.direction}")
        print(f"Final Blocks: {dec_final.blocked_reasons}")
        
        print("\n--- 5. Risk Hand-off ---")
        risk_received_signal = (dec_final.direction in ["long", "short"])
        print(f"Risk Engine Received Signal: {risk_received_signal}")
        
        if not risk_received_signal:
            print(f"\n=> FLATTEN REASON: {dec_final.blocked_reasons}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_cwd)
        if str(root) in sys.path:
            sys.path.remove(str(root))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal-trace", type=str, help="Symbol to trace (e.g. GBPUSD)")
    args = parser.parse_args()

    if args.signal_trace:
        signal_trace(args.signal_trace)
    else:
        print("Run with --signal-trace <SYMBOL>")
