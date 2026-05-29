from __future__ import annotations
import argparse
import os
from pathlib import Path
from src.backtest.backtest_engine import run_backtest
from src.backtest.reporting import export_summary_json
from src.data.loaders import resolve_csv_source, load_ohlcv_csv
from src.utils.config import load_yaml

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest", "train", "paper", "live"], default="backtest")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config" / "symbol.yaml")

    # Startup summary
    mt5_cfg = load_yaml(root / "config" / "mt5_demo.yaml").get("mt5", {})
    print(f"Runtime Mode   : {args.mode}")
    print(f"Execution Mode : {'Paper' if args.mode == 'paper' else args.mode.title()}")
    print(f"MT5 Account    : {mt5_cfg.get('login', 'N/A')}")
    print(f"MT5 Server     : {mt5_cfg.get('server', 'N/A')}")
    print(f"Allow Real Trading : {os.getenv('ALLOW_REAL_TRADING', 'false')}")

    if args.mode == "train":
        from src.ml.train_xgb_filter import main as train_main
        train_main()
    elif args.mode == "backtest":
        csv = resolve_csv_source(root, config["symbol"])
        strategy_name = str(config["symbol"]).lower() + "_strategy"
        strategy_module = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
        result = run_backtest(config, strategy_module, csv_path=str(csv))
        export_summary_json(result, root / "reports" / "latest")
        print(f"Backtest Complete for {config['symbol']} | PnL: {result['net_pnl']:.2f}")
    elif args.mode == "paper":
        from src.pipeline_live import LivePipeline
        pipeline = LivePipeline(root, runtime_mode="paper")
        pipeline.run_loop()
    elif args.mode == "live":
        if os.getenv("ALLOW_REAL_TRADING", "false").lower() != "true":
            raise SystemExit("[WARN] Live mode disabled. Set ALLOW_REAL_TRADING=true to enable.")
        from src.pipeline_live import LivePipeline
        pipeline = LivePipeline(root, runtime_mode="live")
        pipeline.run_loop()

if __name__ == "__main__":
    main()
