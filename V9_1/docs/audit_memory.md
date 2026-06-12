
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

## Fleet Verification Baseline (2026-06-02 13:52:56 UTC)
- **Heartbeats:** Freshness verified across fleet.
- **Strategy Active:** Confirmed pipeline is processing data and evaluating rules (Signals: 0, Vetoes: 0, Execs: 0 observed in recent logs).
- **Errors:** Fleet is running cleanly without traceback crashes.
- **Snapshot Location:** `docs/fleet_health_snapshot.md`

## Fleet Verification Baseline (2026-06-02 13:55:21 UTC)
- **Heartbeats:** Freshness verified across fleet.
- **Strategy Active:** Confirmed pipeline is processing data and evaluating rules (Signals: 0, Vetoes: 0, Execs: 0 observed).
- **Errors:** Fleet is running cleanly without traceback crashes.
- **Snapshot Location:** `docs/fleet_health_snapshot.md`
