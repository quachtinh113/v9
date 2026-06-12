Layer | Status | Evidence | Recheck Trigger
---|---|---|---
Runtime | PASS | run_btcusd_pipeline.py running PID | Recheck if heartbeat stops
Heartbeat | PASS | tick_age < 2.0s | Check logs/heartbeat.jsonl
Time compatibility | PASS | MT5 UTC diff 0.038s | Recheck only after broker/VPS/timezone change
BTC session policy | PASS | session_flag = crypto_24_7 | Recheck after config change
Signal pipeline | PASS | Signal generated and scored | Check logs/live_pipeline_audit.ndjson
Risk engine | PASS | Action: ALLOW passed | Check logs/console_err.log
Execution demo safety | PASS | mt5_demo.yaml demo verification | Recheck if LIVE is requested
