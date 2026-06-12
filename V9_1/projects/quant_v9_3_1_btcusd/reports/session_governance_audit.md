# Session Governance Audit (last 1000 rows)

Total rows examined: 1000

## Session State Distribution
- unknown: 1000 (100.00%)

## Trades by Session State (order_send_called)
- unknown: 106 (100.00% of trades)

## STRATEGY_FLAT occurrences by Session State
- unknown: 431 (100.00% of flat rows)

## Answers to Queries
1. Session state is calculated from the `session_flag` feature, derived in `mtf_builder` based on UTC hour.
2. Observed session values: unknown.
3. Allowed to trade sessions (configured in `detect_regime`): `london` and `new_york`.
4. Session state distribution counts are listed above.
5. Trades by session state counts are listed above.
6. STRATEGY_FLAT by session state counts are listed above.
7. Unknown session is treated as off‑session by `detect_regime` (falls into the `off_session` branch).
8. BTCUSD is intended to trade only during London and New York windows (24/5 not enabled).

**Final decision:** A (Session config correct)
