# Strategy Flat Decision Audit (last 1000 rows)

Total rows examined (last 1000): 1000
Rows with flat direction or STRATEGY_FLAT reason: 405

## Top Blocked Reasons (by count)
- rsi_neutral_in_sideway: 165 (40.74%)
- score_below_threshold_50_vs_70: 165 (40.74%)
- transition_regime_disabled: 120 (29.63%)
- no_trade_in_regime_transition: 120 (29.63%)
- score_below_threshold_40_vs_70: 120 (29.63%)
- off_session_regime_no_trade: 120 (29.63%)
- invalid_session_off: 120 (29.63%)
- no_trade_in_regime_off_session: 120 (29.63%)
- score_below_threshold_30_vs_70: 120 (29.63%)
- rsi_not_in_mean_reversion_bounds_36.5: 15 (3.70%)

## High-Level Failure Categories
- score_below: 405 (100.00%)
- rsi: 330 (81.48%)
- other: 240 (59.26%)
- off_session_regime: 240 (59.26%)
- invalid_session: 120 (29.63%)

## Field Statistics (non-null values)
- rsi14_m15: count=405, min=36.06, mean=46.79, max=65.25
- adx14_h1: count=405, min=12.39, mean=18.01, max=21.87
- atr14_m1: count=405, min=18.57, mean=38.44, max=158.30

## Answers to Requested Checks
1. Exact rule causing STRATEGY_FLAT: **rsi_neutral_in_sideway**
2. RSI condition failing? Yes (count=330)
3. ADX condition failing? No (count=0)
4. ATR/volatility condition failing? No (count=0)
5. Spread guard failing? No (count=0)
6. Regime/session condition failing? Yes (count=360)
7. Signal score below threshold? Yes (count=405)
