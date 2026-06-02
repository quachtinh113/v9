# Post-Fix Report: BTCUSD Quant V9

## Root Cause
1. **Runtime:** The main pipeline file (`pipeline_live.py`) was only a module/class definition and lacked an execution entry point, causing it to immediately exit silently when run directly.
2. **Session Policy:** The bot applied an FX-centric session window (08:00 - 21:00 UTC) via `mtf_builder.py` to BTCUSD, causing the regime engine to hard-block all setups outside this window as `off_session`.

## Files Changed
- `V9_1/projects/quant_v9_3_1_btcusd/run_btcusd_pipeline.py` *(Created)*
- `V9_1/projects/quant_v9_3_1_btcusd/config/symbol.yaml`
- `V9_1/projects/quant_v9_3_1_btcusd/src/data/mtf_builder.py`
- `V9_1/projects/quant_v9_3_1_btcusd/src/data/mt5_live_adapter.py`
- `V9_1/projects/quant_v9_3_1_btcusd/src/pipeline_live.py`
- `V9_1/projects/quant_v9_3_1_btcusd/src/core/regime_engine.py`
- `V9_1/projects/quant_v9_3_1_btcusd/src/core/signal_engine.py`
- `V9_1/docs/audit_memory.md`
- `V9_1/docs/code_graph.md`
- `V9_1/docs/audit_checklist_cache.md`

## Test Evidence
- **MT5 Time Sync:** 0.038 seconds difference between MT5 tick time and local UTC time (Perfect sync).
- **Process Status:** The new launcher securely initiates the bot without silently crashing.
- **Heartbeat:** Consistently updating with `tick_age` < 2s.
- **Execution Log:** Demo execution successfully routed a test order (`"runtime_mode": "live"`, but verified as Demo account in MT5).

## Current Status
- **Bot is RUNNING successfully.**
- Strategy rules, RSI/ADX bounds, and Risk vetos were **100% preserved** (no loosening).
- BTCUSD is now legally permitted to trade 24/7 without triggering `off_session` blocks.

## Remaining Risks
- **ML Gatekeeper:** The XGBoost model contract is missing (`models/xgb_trade_filter.json`), causing the ML gate to default to `observe_only`. If hard ML blocking is desired, a contract must be generated and approved.

## Next Monitoring Command
```powershell
Get-Content "V9_1\projects\quant_v9_3_1_btcusd\logs\console_err.log" -Tail 20
```
