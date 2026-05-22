# Portfolio Command Center Dashboard Architecture

This document describes the structure, components, and layout design of the NowTrading Quant Core V9.3.1 Portfolio Command Center dashboard.

## Overview
The dashboard is designed as a glassmorphism client-side web application served locally on port 8000. It reads simulated telemetry, historical backtest reports, and configuration parameters from the workspace directory and provides visual metrics.

## Front-end Component Layout

### 1. Sidebar Navigation
- **Navigation Items:** Command Center, Asset Matrix, Risk Settings, Architecture (new).
- **System Status Indicator:** Pulsing status dot representing local status (`SYS_READY_LIVE` or `SYS_READY_PAPER`).
- **Server Clock:** Dynamic local system time displayed in monospace format.

### 2. KPI Panel
- **Total AUM:** Calculated as `$10,000 * Approved Count * Global Multiplier`.
- **Cumulative PnL:** Cumulative net profit of all approved systems scaled by the multiplier.
- **Value at Risk (VaR):** Estimated 95% worst-case drawdown scaled by the global multiplier.
- **Approved Channels:** Ratio of approved assets out of the 10 loaded targets.

### 3. Asset Matrix Table
- Lists all 10 assets with their ticker, asset class, validation verdict (`APPROVED` / `DISABLED`), Sharpe ratio, Profit Factor, scaled AUM allocation, and allocation weight.
- Supports interactive selection: clicking on a row updates the Risk Engine Guards Monitor to focus on the selected symbol.

### 4. Simulated Equity Growth Curve
- Uses Chart.js to render a compound interest trend showing simulated portfolio equity growth.
- **Global Multiplier Slider:** Interactive range slider (0.1x to 3.0x) that dynamically recalculates and redraws the equity curve, AUM allocations, and total metrics on-the-fly.

### 5. Risk Engine Guards Monitor
- Visualizes status of the 7 risk engines guards for the selected asset.
- Shows indicators for `Spread Guard` (`ACTIVE` / `DISABLED`), `Slippage Guard` (`ACTIVE` / `DISABLED`), `ATR Shock Block` (`ACTIVE` / `DISABLED`), and exact thresholds for Max Daily Loss, Weekly Soft Stop, and Hard Drawdown limits.

### 6. System Live Audit Stream
- Monospaced terminal window showing simulation logs in real-time. Highlights timestamps, asset symbols, and event messages (such as backtester outcomes and pipeline initialization checks).

### 7. Architecture Control Center (New)
- **Regime Execution Flow:** Visual pipeline tracing the transition from Regime classification to Audit Log.
- **Module Health Grid:** Grid showing loaded python files, their risk level, ownership, and standby statuses.
- **Asset Registry Cards:** Display cards of all 10 asset subprojects, detailing M1 data status and model availability.
- **Forbidden Bypass Rules Alert:** Red alarm panel detailing forbidden direct paths that bypass RiskGateway and ML Gatekeeper checks.

---

## Local Laptop Test Mode Configuration
- **Port Binding:** Local port 8000 (binds to localhost / `0.0.0.0` for local access).
- **Data Fallbacks:** If consolidated reports (`realism_engine/summary.json` or `edge_discovery/summary.json`) are missing or incomplete, the dashboard defaults gracefully to fallback values rather than crashing.
- **Mock Feeds:** Telemetry endpoints generate simulated stream ticks to keep the front-end interface active during laptop-only testing.
