# Signal Quality Root Cause Audit (last 5000 rows)
Total rows analyzed: 4104

## Regime Distribution
- off_session: 900 (21.93%)
- sideway: 619 (15.08%)
- transition: 416 (10.14%)
- trend: 228 (5.56%)
- N/A: 1 (0.02%)

## Signal Distribution
- flat: 1854 (45.18%)
- short: 196 (4.78%)
- long: 113 (2.75%)
- N/A: 1 (0.02%)

## Session Distribution (raw field)
- unknown: 2164 (52.73%)

## ML Mode Distribution
- observe_only: 2164

## ML Score Statistics
- min: 0.0000
- max: 0.9710
- mean: 0.2258
- median: 0.0821

## Risk Decisions
- N/A: 1855
- ALLOW: 309

## Execution Modes
- paper: 2087
- live: 77

## Order Send Called
- False: 1855
- True: 309

## Top Blocked Reasons
- STRATEGY_FLAT: 1715 (41.79%)
- ML_GATEKEEPER_BLOCK: 224 (5.46%)

## Feature Quality Issues
- rsi14_m15: missing=2164, zero=0, nan=0
- adx14_h1: missing=2164, zero=0, nan=0
- atr14_m1: missing=2164, zero=0, nan=0
- spread: missing=2164, zero=0, nan=0
- regime: missing=2164, zero=0, nan=0

## Inferred Root Cause Categories (A-F)
D