
- MT5 time compatible: YES
- UTC diff: 0.038 seconds
- Time mismatch: NO
- Session bug: BTC_SESSION_POLICY_MISMATCH
- pipeline_live.py is class/module only, not launcher
- Need launcher fix + BTC always_on session policy

- Runtime stable: YES (Running successfully with fresh heartbeats)
- Signal pipeline alive: YES (Processing MTF indicators, scoring signals)
- Risk passed/veto reason: PASS (Order was initially allowed), then blocked by strict RSI bounds (e.g. si_out_of_trend_bounds_short_23.7).
- Execution mode: DEMO (LivePipeline verified demo account via mt5_demo.yaml config, safely dispatched demo order).
- Any new blocker: No logic blockers. Strict signal thresholds (like RSI > 25 for short trend) are working correctly and not an error.
