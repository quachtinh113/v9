# Signal Engine Audit Report: BTCUSD Bottleneck & Weekend Market Closed Integration

This audit investigates the rule-based quantitative entry rules for the active **BTCUSD** cryptocurrency channel and validates the implementation of **Weekend Market Closed** state awareness across all other symbol channels of the Quant V9 fleet.

---

## 1. Trace of BTCUSD Pipeline Execution Flow

The active live pipeline execution for the BTCUSD agent follows a strict sequential gate check from raw data input to execution decisions:

```
[DATA] -> MT5 ticks pulled via MetaTrader 5 API (Live/Demo Connection: mt5_ok: true)
   ↓
[FEATURE] -> High-frequency technical metrics calculated (e.g. adx14_h1, rsi14_m15, atr_ratio)
   ↓
[SIGNAL] -> evaluate_signal() parses features (detects sideway regime, calculates score=50)
   ↓
[ML] -> apply_ml_gatekeeper() runs dedicated XGBoost model (ml_score=0.0192, ml_decision=PASS)
   ↓
[RISK] -> RiskGateway parses limits and spread guards (spread=1400, risk_decision=ALLOW)
   ↓
[EXECUTION] -> OrderRouter processes output. Hard entry gate failed (score=50 vs threshold=70), resulting in FLAT
```

---

## 2. Location & Source Trace of Signal Veto

The exact source producing the `"rsi_not_in_mean_reversion_bounds"` block has been isolated as follows:

* **Source File**: [signal_engine.py](file:///c:/Quant%20Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/src/core/signal_engine.py)
* **Function**: `evaluate_signal(features, config)`
* **Caller Chain**:
  `src.main.main()`
  ➔ `src.pipeline_live.run_live_loop()`
  ➔ `src.core.signal_engine.evaluate_signal()`

### isolated source code logic:
```python
        elif regime == "sideway":
            # Mean reversion: BUY on oversold, SELL on overbought
            if rsi <= 35:
                rsi_pass = True
            elif rsi >= 65:
                rsi_pass = True
            else:
                blocked_reasons.append(f"rsi_not_in_mean_reversion_bounds_{rsi:.1f}")
```

---

## 3. BTCUSD Real-Time Diagnostic Values

* **Current RSI (M15)**: `47.1` (or `52.3` in the previous cycle)
* **Current ADX (H1)**: `11.0`
* **Current ATR (M1)**: `20.67`
* **Current Signal Score**: `50.0`
* **Required Entry Score**: `70.0`
* **ML Score**: `0.0192` (Pass)
* **Final Signal Output**: `FLAT` (Blocked by Signal Engine)

---

## 4. Signal Engine Behavioral Analysis

### Is the Signal Engine behaving correctly?
**Yes.** The Signal Engine is behaving exactly as designed by the quantitative architecture:
1. **Regime Identification**: Because `adx14_h1 <= 18` (`11.0` <= `18.0`), the market is correctly classified as `sideway` (range-bound).
2. **Mean Reversion Logic**: In a sideways regime, the bot is restricted to mean-reversion pullbacks. Entering a trade when RSI is at `47.1` or `52.3` (right in the middle of the range, perfectly neutral) possesses **zero statistical edge**. Enforcing `rsi <= 35` for longs or `rsi >= 65` for shorts is critical to avoid trading random noise and suffering unnecessary drawdown.
3. **Verdict**: The entry threshold logic is 100% mathematically correct and valid. No parameters should be forced or lowered to push a trade.

---

## 5. Audit Questions & Actionable Recommendations

### 1. Why is BTCUSD blocked?
BTCUSD is blocked because it is in a sideways regime and the M15 RSI is currently neutral (`47.1`), failing both the RSI range filter and the Direction Alignment pullback filter. This prevents the signal score from reaching the required threshold of `70`.

### 2. Is the block valid?
**Yes.** The block is completely valid. Taking a trade at neutral RSI in a sideways range represents low-expectancy trading and is hard-blocked to protect capital.

### 3. Which symbol is closest to execution?
**BTCUSD** is the closest (and only) symbol near execution because it is a cryptocurrency that trades 24/7. All other 10 symbols are suspended under `MARKET_CLOSED` for the weekend.

### 4. Should any threshold be changed?
**No.** Enforcing these strict parameters prevents the bot from over-trading choppy, range-bound environments. The thresholds should remain unchanged to maintain risk governance.

### 5. Recommended next action:
* **Observe BTCUSD**: Let the BTCUSD agent run in the background. It will automatically enter a `LONG` trade if RSI falls to `≤ 35` or a `SHORT` trade if RSI spikes to `≥ 65`.
* **Weekend Operational Security**: The newly implemented **`MARKET_CLOSED`** awareness correctly identifies that Forex, Gold, and Stock Index markets are closed over the weekend. Operational checks are clean.
