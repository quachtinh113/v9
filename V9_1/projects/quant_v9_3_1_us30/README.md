# US30 Quant v9.3.1

This repo contains a single-asset quant scaffold upgraded with:
- real RSI / ADX / ATR calculations
- multi-timeframe feature builder (M5 / M15 / H1 / H4)
- single-asset backtest engine with stop / target / timeout
- MT5 adapter stub kept for paper/demo connection later

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python -m src.main
```

## Flow

1. Load M1 OHLCV data
2. Build MTF feature table
3. Evaluate US30 signal profile
4. Create position plan from ATR
5. Run backtest and report metrics


## Data and reports

This repo now includes a realistic sample M1 CSV under `data/raw/` so the backtest can run immediately.
Replace that file with your broker-exported CSV when moving to demo.

Run:

```bash
python -m src.main
```

Outputs are written to:
- `reports/latest/trade_log.csv`
- `reports/latest/summary.json`
- `reports/latest/report.md`

## Demo mode
Paper demo:
```bash
python -m src.run_demo --mode paper
```

MT5 demo bridge:
1. Copy `config/mt5_demo.yaml.example` to `config/mt5_demo.yaml`
2. Fill in demo account details
3. Keep smallest volume and test on demo only
4. Run:
```bash
python -m src.run_demo --mode mt5
```

Journal output:
- `logs/demo_journal.jsonl`
