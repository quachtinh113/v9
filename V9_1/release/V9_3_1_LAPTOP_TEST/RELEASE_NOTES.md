# RELEASE NOTES - QUANT V9.3.1 LAPTOP TEST SPRINT 1

## Sprint 1 Key Features & Fixes
1. **Drawdown Lockout Reset**: Daily and weekly drawdowns automatically reset at midnight.
2. **Correct Profit Factor Formula**: Calculated using net win divided by net loss dollar values.
3. **Risk Guards**: Active spread limit, slippage limit, and ATR volatility checks inside `risk_engine.py`.
4. **ML Gatekeeper**: XGBoost model signal filtering with 50x caching.
5. **Realism Outcome Training Labels**: Evaluated based on true look-forward boundaries instead of random numbers.
6. **Live Execution Compliance**: Enforced routing flow: Signal -> ML -> Risk -> Router.
7. **Paper Fallback**: Graceful MT5 offline handling.
