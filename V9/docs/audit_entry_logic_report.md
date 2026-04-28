# Quant V9 System Audit: Entry Logic & Risk Violations

This report details the architectural and logic flaws identified in the Quant V9 trading system, specifically explaining why the bot executes uniform BUY orders across all assets, utilizes a fixed lot size, and bypasses critical risk guardrails.

## Executive Summary

The V9 architecture is solid conceptually, but the current implementation in `us30_strategy.py` and the core engines contains hardcoded values and logical bypasses that completely undermine the system's risk-first philosophy.

## Detailed Findings

### 1. Simultaneous Multi-Asset BUY Orders
*   **Severity:** **CRITICAL**
*   **Location:** `src/data/mtf_builder.py` and `src/core/signal_engine.py`
*   **Description:** The feature builder currently mocks data with `df["bias"] = "long"`. The `signal_engine.py` assigns a score of 50 for any valid regime and adds 30 if `bias != "flat"`. This results in a score of 80 (passing the threshold of 70). Consequently, `direction` always equals `bias` ("long").
*   **Fix:** Replace hardcoded bias in `mtf_builder.py` with actual RSI/EMA calculation logic. Implement Multi-Timeframe (MTF) alignment checks before returning a valid bias.

### 2. Fixed Lot Sizing (0.25) & Hardcoded TP/SL
*   **Severity:** **CRITICAL**
*   **Location:** `src/strategies/us30_strategy.py`
*   **Description:** The strategy completely ignores the `position_engine.py`. It hardcodes the `PositionPlan` creation: `PositionPlan(features["close_m1"], features["close_m1"]*0.99, features["close_m1"]*1.02, 0.25, 120)`. This forces a fixed lot size of 0.25 and static percentage-based SL/TP (1% SL, 2% TP) regardless of the asset's ATR or tick value.
*   **Fix:** Refactor the strategy to call `position_engine.build_position(...)`. Update `build_position` to use dynamic, risk-based lot sizing: `lot = risk_money / (SL_distance * tick_value_per_lot)`.

### 3. Missing Variable Bug in Position Engine
*   **Severity:** **HIGH**
*   **Location:** `src/core/position_engine.py` (Line 8)
*   **Description:** The variable `tp_mult` is used but never defined (the parameter is named `tp_atr_mult`). If the position engine were actually called, it would crash immediately with a `NameError`.
*   **Fix:** Rename `tp_mult` to `tp_atr_mult` in the formula.

### 4. Excessive Pending Orders & Missing Correlation Guards
*   **Severity:** **HIGH**
*   **Location:** `src/core/risk_engine.py`
*   **Description:** The `RiskGateway` only checks `daily_dd_pct` and `loss_streak`. It completely fails to check `open_positions`, `pending_orders`, or `correlation_exposure`. This allows the bot to flood the market with pending orders (especially for indices like US30).
*   **Fix:** Implement a robust `configs/risk_config.yaml` and update `RiskGateway` to validate against `max_pending_orders_per_symbol`, `max_basket_risk_pct`, and `max_same_direction_assets`.

### 5. Execution Engine Bypassing Risk Block
*   **Severity:** **CRITICAL**
*   **Location:** `src/pipeline_live.py` (Line 58)
*   **Description:** The live pipeline retrieves the signal but only prints it. The comment `# Risk/Route logic...` indicates the risk veto and execution routing are entirely missing from the live loop. If an order were placed here, it would bypass the Risk Engine completely.
*   **Fix:** Implement the full sequence: `Signal -> Risk Check -> Position Sizing -> OrderRouter`. Ensure `OrderRouter` respects `RiskDecision == "BLOCK"`.

## Refactoring Priority
1. **Fix Risk Engine:** Block trades that exceed exposure limits or pending order limits.
2. **Fix Position Sizing:** Remove fixed 0.25 lot, implement dynamic sizing based on ATR.
3. **Connect the Pipeline:** Ensure `pipeline_live.py` correctly passes the plan through the Risk Engine before sending it to MT5.
