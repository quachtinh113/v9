# Weekly Signal Evaluation Matrix

**Audit Period:** 2026-05-24 to 2026-05-31
**System State:** **INACTIVE (BOT_NOT_RUNNING)**

---

## 1. Portfolio Signal Summary Table

This table tracks the performance of the strategy indicators, machine learning filters, and risk gateways for each currency and index symbol in the Quant V9 fleet. Due to the fleet being offline, all metrics are zeroed.

| Asset Symbol | Strategy | Raw Signals | ML Approved | ML Blocked | Risk Passed | Risk Vetoed | Executed | Primary Bottleneck / Block Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **AUDUSD** | EURUSD_Clone | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **BTCUSD** | Crypto_Trend | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **EURUSD** | Mean_Reversion | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **GBPUSD** | Trend_Follow | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **US30** | Index_Momentum| 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **US100** | Index_Momentum| 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **US500** | Index_Momentum| 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **USDCAD** | Mean_Reversion | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **USDCHF** | Mean_Reversion | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **USDJPY** | Trend_Follow | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **XAUUSD** | Metal_Volat   | 0 | 0 | 0 | 0 | 0 | 0 | BOT_NOT_RUNNING |
| **TOTAL** | - | **0** | **0** | **0** | **0** | **0** | **0** | **BOT_NOT_RUNNING** |

---

## 2. Gateway Telemetry Summary

### A. Machine Learning (XGBoost Meta-Filter)
* **Status:** INACTIVE
* **Configured Threshold:** `0.50` (Meta-filter gatekeeper)
* **Total Evaluations:** 0
* **ML Veto Count:** 0
* **ML Approval Rate:** 0.00%

### B. Risk Governance Gateway
* **Status:** INACTIVE
* **Configured Protections:**
  - Spread Multiplier Guard: **Armed (Inactive)**
  - Slippage Shock Guard: **Armed (Inactive)**
  - ATR Shock Block: **Armed (Inactive)**
  - Daily Drawdown Limit: **Armed (Inactive)**
* **Risk Engine Vetoes:** 0
* **Risk Engine Approvals:** 0

---

## 3. Analytical Findings
1. **Zero Heartbeats Detected:** No scheduling tick events were triggered. The loop frequency requires checking market feeds every 60 seconds, which would have produced approximately `10,080` evaluations per symbol over a 7-day period if operational.
2. **Missing Environment Packages:** The system lacks the critical `psutil` environment module, halting verification services and dashboard process monitoring.
3. **No Active Paper Fallback Logs:** Although paper trading fallback is armed, the lack of process execution prevented any fallback logs or standard outputs from being generated.
