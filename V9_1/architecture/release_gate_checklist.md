# NowTrading Quant V9.3.1 Release Gate Checklist

This document details the checklist and requirements for each release stage in our deployment pipeline.

---

## 1. DEV (Development Stage)
- [x] All 7 Sprint 1 core bugs fixed in local template (`quant_v9_3_1_us30`).
- [x] Unit test suite `test_sprint1.py` written and verified locally.
- [x] Profit factor calculations validated mathematically.
- [x] Daily reset logic for drawdowns and loss streaks active.

---

## 2. RC1 (Release Candidate 1)
- [x] Changes propagated to all 10 assets via mass deploy automation (`mass_deploy_and_train.py`).
- [x] Automated smoke tests `smoke_test.py` run on all assets.
- [x] Pytest unit tests pass successfully.
- [x] Backtest aggregator generates consolidated asset metrics.

---

## 3. LAPTOP_TEST (Local Laptop Release) — [CURRENT]
- [x] **Safety Lock Verified:** `live_capital_enabled` set to `false` in `symbol.yaml` configs.
- [x] MT5 connection fails fallback gracefully to safe Mock Paper execution offline.
- [x] Run local validation suite (`run_edge_validation.py`, `run_dashboard.py --check-only`).
- [x] Verification scripts check port 8000 availability, write permissions, and dependency compliance.
- [x] Release packaging directory built containing all artifacts and scripts.
- [x] Dashboard Port 8000 loads and visualizes asset matrix correctly.

---

## 4. PAPER_TEST (Paper Testing / Real-Time Simulation)
- [ ] Deploy bots to dedicated paper-trading local environments.
- [ ] Connect MT5 terminals to Demo Account. Verify adapter connects and executes mock orders successfully.
- [ ] Continuous observation of CPU, RAM, and audit log growth for 48 hours.
- [ ] Verify `stop_all_bots.bat` kills python bot processes cleanly under load.
- [ ] Verify AUM/PnL metrics reflect real-time paper outcomes without duplication.

---

## 5. DEMO (Demo Staging)
- [ ] Sync live market feeds from MetaTrader 5 demo accounts.
- [ ] ML Gatekeeper model updates dynamically based on weekly auto-learning audits.
- [ ] RiskGateway validates order sizes and limits slippage against real broker execution feeds.
- [ ] 0% bypass check verified for all assets.
- [ ] Run edge validation checks to ensure zero overfitting anomalies.

---

## 6. LIVE (Live Capital Deployment) — [LIVE CAPITAL: DISABLED]
- [ ] Executive committee manual approval required.
- [ ] RiskGateway `daily_loss_limit_pct` set to strict risk bounds.
- [ ] Hardware/VPS setup with high availability and automated failovers.
- [ ] Telegram emergency alert system fully connected.
- [ ] Hard drawdown limit vetoes tested and operational.
- [ ] Double-check `.env` for production credential storage.
