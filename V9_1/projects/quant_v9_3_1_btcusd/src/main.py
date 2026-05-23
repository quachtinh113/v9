from __future__ import annotations
import argparse
from pathlib import Path
from src.backtest.backtest_engine import run_backtest
from src.backtest.reporting import export_summary_json
from src.data.loaders import resolve_csv_source, load_ohlcv_csv
from src.utils.config import load_yaml

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest", "train", "live"], default="backtest")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config" / "symbol.yaml")
    
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
    elif args.mode == "live":
        from src.pipeline_live import LivePipeline
        pipeline = LivePipeline(root)
        pipeline.run_loop()

if __name__ == "__main__": main()
