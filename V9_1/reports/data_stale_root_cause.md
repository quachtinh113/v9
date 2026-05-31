# Data Stale Root Cause Audit Report

This audit report investigates the operational status and root cause analysis of the `DATA_STALE` alerts triggered across the 11 active asset channels of the Quant V9 fleet.

---

## 1. System-Wide Telemetry Summary

* **Audited Date/Time**: Sunday, May 31, 2026, 13:38:26 UTC (20:38:26 Local System Time)
* **Active Channels**: 11 Symbols
* **Primary System State**: Operational (YELLOW - Heartbeats Active, Data Feeds Stale for non-crypto symbols)
* **Core Code Graph Tracing**: Map referenced via `reports/code_graph_index.json`, linking [pipeline_live.py](file:///c:/Quant%20Trade/v9/V9_1/projects/quant_v9_3_1_btcusd/src/pipeline_live.py) tick collectors to the dashboard API.

---

## 2. Per-Symbol Diagnostic Matrix

The following table documents the exact state of all 11 active symbols retrieved from the real-time bot telemetry files (`heartbeat.jsonl` and `live_pipeline_audit.ndjson`):

| Symbol | Broker Symbol | MT5 OK | Latest Tick Time (UTC) | Heartbeat Time (UTC) | Tick Age (s) | Market Status | Stale Reason |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| **GBPUSD** | `GBPUSDm` | Yes | 2026-05-29 20:58:59 | 2026-05-31 13:38:26 | 146,366.75 | 🔴 CLOSED | Weekend Market Close |
| **EURUSD** | `EURUSDm` | Yes | 2026-05-29 20:58:59 | 2026-05-31 13:38:26 | 146,366.77 | 🔴 CLOSED | Weekend Market Close |
| **USDJPY** | `USDJPYm` | Yes | 2026-05-29 20:58:56 | 2026-05-31 13:38:26 | 146,369.77 | 🔴 CLOSED | Weekend Market Close |
| **AUDUSD** | `AUDUSDm` | Yes | 2026-05-29 20:57:59 | 2026-05-31 13:38:25 | 146,426.38 | 🔴 CLOSED | Weekend Market Close |
| **USDCAD** | `USDCADm` | Yes | 2026-05-29 20:58:59 | 2026-05-31 13:38:25 | 146,366.57 | 🔴 CLOSED | Weekend Market Close |
| **USDCHF** | `USDCHFm` | Yes | 2026-05-29 20:58:59 | 2026-05-31 13:38:25 | 146,366.27 | 🔴 CLOSED | Weekend Market Close |
| **US30** | `US30` | Yes | 2026-05-29 20:54:58 | 2026-05-31 13:38:25 | 146,607.38 | 🔴 CLOSED | Weekend Market Close |
| **US100** | `US100` | Yes | 2026-05-29 20:54:58 | 2026-05-31 13:38:25 | 146,607.46 | 🔴 CLOSED | Weekend Market Close |
| **US500** | `US500` | Yes | 2026-05-29 20:54:58 | 2026-05-31 13:38:26 | 146,607.63 | 🔴 CLOSED | Weekend Market Close |
| **XAUUSD** | `XAUUSDm` | Yes | 2026-05-29 20:57:59 | 2026-05-31 13:38:25 | 146,426.51 | 🔴 CLOSED | Weekend Market Close |
| **BTCUSD** | `BTCUSDm` | Yes | 2026-05-31 13:38:25 | 2026-05-31 13:38:26 | 0.74 | 🟢 OPEN | Active 24/7 Crypto Setup |

---

## 3. Core Audit Questions & Findings

### 1. Is `DATA_STALE` real?
**Yes.** Technically, the calculations are correct. The latest available ticks in the MT5 terminal for 10 out of the 11 active symbols are indeed from Friday evening, May 29, 2026. This data is over **40.6 hours old** relative to the Sunday execution, making it objectively stale from a strict streaming data perspective.

### 2. Is dashboard calculation correct?
**Yes.** The dashboard backend parser in [run_dashboard.py](file:///c:/Quant%20Trade/v9/V9_1/run_dashboard.py) reads the exact metrics from the `heartbeat.jsonl` files and maps them to `DATA_STALE` whenever the `tick_age` exceeds the threshold (e.g., 300 seconds). The frontend correctly visualizes these as orange indicators with precise tick ages.

### 3. Is timestamp timezone incorrect?
**No.** All logs, timestamps, and calculations are fully aligned in UTC (GMT+0) and parsed timezone-safely (preventing naive/aware datetime errors). The time tracking is completely consistent across MT5 tick outputs, local heartbeat timestamps, and backend collectors.

### 4. Is market closure causing false stale?
**Yes.** This is a functional "false positive" warning from an alert standpoint. The data is stale solely because the Forex, Precious Metals (Gold), and Stock Index markets are closed over the weekend. There are no new ticks being published by the broker, causing the latest tick timestamp to remain halted at the Friday market close time.

### 5. Is MT5 feed frozen?
**No.** The MetaTrader 5 API connection and account state are fully active and nominal (`mt5_ok: true` or `mt5_connected: true`). The lack of ticks is a broker-enforced weekend holiday, not a local terminal crash, feed deadlock, or network outage.

### 6. Is parser producing stale values?
**No.** The parser reads the latest actual entries appended by the active agents and performs no artificial delay or logging lag.

---

## 4. Final Verdict

> [!IMPORTANT]
> **SINGLE ROOT CAUSE:** The sole root cause of 10 out of 11 symbols reporting `DATA_STALE` is **Weekend Market Closure** (Forex, Gold, and Stock Indices halt tick updates from Friday evening to Sunday evening). 
> 
> **Operational Verification**: This is mathematically validated by **`BTCUSD`** (Cryptocurrency), which is traded 24/7 on weekends. The BTCUSD agent remains active and has a nominal `tick_age` of **`0.74 seconds`**, resolving to the `SIGNAL_ENGINE` stage.

**Recommendation**: 
Before implementing any strict **Data Circuit Breaker**, the staleness gate should be updated to check whether the current day of the week is a weekend (Saturday/Sunday) and whether the symbol's market is currently open. If the market is closed, `DATA_STALE` is expected behavior and should not trigger blockages or alerts.
