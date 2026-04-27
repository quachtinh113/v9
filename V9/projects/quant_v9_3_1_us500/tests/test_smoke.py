from pathlib import Path

from src.backtest.backtest_engine import run_backtest
from src.backtest.reporting import export_report_md, export_summary_json, export_trade_log_csv
from src.data.loaders import generate_sample_ohlcv, load_ohlcv_csv
from src.data.mtf_builder import build_feature_table
from src.indicators.rsi import compute_rsi
from src.indicators.adx import compute_adx
from src.indicators.atr import compute_atr
from src.utils.config import load_yaml


SYMBOL = "US500"


def test_indicators_return_series():
    df = generate_sample_ohlcv(SYMBOL, periods=300)
    assert compute_rsi(df["close"]).notna().sum() > 0
    assert compute_adx(df).notna().sum() > 0
    assert compute_atr(df).notna().sum() > 0


def test_feature_builder_contains_mtf_columns():
    df = generate_sample_ohlcv(SYMBOL, periods=10000)
    features = build_feature_table(df)
    expected = {"close_m5", "rsi14_m15", "adx14_h1", "atr14_h4", "bias", "atr_ratio"}
    assert expected.issubset(set(features.columns))
    assert len(features) > 50


def test_backtest_engine_runs_on_csv_and_exports_reports(tmp_path):
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config" / "symbol.yaml")
    strategy_name = str(config["symbol"]).lower() + "_strategy"
    strategy_module = __import__(f"src.strategies.{strategy_name}", fromlist=["generate_trade_plan"])
    csv_path = root / "data" / "raw" / f"{config['symbol']}_M1_sample.csv"
    df = load_ohlcv_csv(csv_path)
    assert len(df) > 1000
    result = run_backtest(config, strategy_module, csv_path=str(csv_path))
    out_dir = tmp_path / "reports"
    log_path = export_trade_log_csv(result, out_dir)
    summary_path = export_summary_json(result, out_dir)
    report_path = export_report_md(result, out_dir)
    assert result["status"] == "ok"
    assert result["bars"] > 50
    assert log_path.exists() and summary_path.exists() and report_path.exists()
