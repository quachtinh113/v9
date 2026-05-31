# Start All Bots Launcher & Runtime Bottleneck Audit Report

**Audit Date:** 2026-05-31
**Auditor:** Senior Quantitative Systems Auditor
**Overall Verdict:** **LAUNCHER MODE LOCKED (START_ALL_STILL_PAPER_LOCKED)**
**Main Bottleneck:** **START_ALL_STILL_PAPER_LOCKED**

---

## 1. Git Synchronization Verification

A formal synchronization check was performed on the local workspace repository (`d:\05_Quant\v9`) to determine if it aligns with GitHub PR #1 branch `RC02`.

* **Current Branch:** `RC02` (Verified via `git branch --show-current`)
* **HEAD Commit:** `19e6357601936ba3d668030ebda713d87bdf48ec` ("push audit")
* **Status:** The local repository is fully up to date with the remote branch `origin/RC02`.
* **Verdict:** **YES** - Local code is updated to PR #1 RC02.

---

## 2. Launcher Configurations Inspection

The fleet launchers in the root workspace `D:\05_Quant\v9\V9_1` were audited to identify the execution mode configured for each symbol.

### A. `start_all_bots.bat`
* **Execution Mode Lock:** **PAPER** (`set MODE=paper`)
* **safeguards/Flags:**
  - `ALLOW_REAL_TRADING` is not configured.
  - `QUANT_RUNTIME_MODE` is not configured.
* **Commands Executed per Symbol:**
  - **GBPUSD:** `start "AGENT-GBPUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_gbpusd && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **EURUSD:** `start "AGENT-EURUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_eurusd && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **USDJPY:** `start "AGENT-USDJPY" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdjpy && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **AUDUSD:** `start "AGENT-AUDUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_audusd && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **USDCAD:** `start "AGENT-USDCAD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdcad && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **USDCHF:** `start "AGENT-USDCHF" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdchf && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **US30:** `start "AGENT-US30" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us30 && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **US100:** `start "AGENT-US100" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us100 && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **US500:** `start "AGENT-US500" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us500 && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **XAUUSD:** `start "AGENT-XAUUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_xauusd && set PYTHONPATH=.&& python -m src.main --mode paper"`
  - **BTCUSD:** `start "AGENT-BTCUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_btcusd && set PYTHONPATH=.&& python -m src.main --mode paper"`

### B. `start_all_bots_live_demo.bat`
* **Execution Mode Lock:** **LIVE** (`set MODE=live`)
* **Safeguards/Flags:**
  - `set ALLOW_REAL_TRADING=true`
  - `set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK`
  - `set QUANT_RUNTIME_MODE=live`
  - `set LIVE_DEMO_ALLOWED=true`
* **Commands Executed per Symbol:**
  - Runs each agent with `--mode live` and mounts all environment safeguards.
  - **GBPUSD:** `start "AGENT-GBPUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_gbpusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode live"`
  - *(Same launcher syntax applied recursively to all 11 assets).*

---

## 3. main.py Live Support Check

All 11 symbol workspaces under `projects/quant_v9_3_1_*` were scanned for the presence of the live routing block inside `src/main.py`:
```python
    elif args.mode == "live":
        if os.getenv("ALLOW_REAL_TRADING", "false").lower() != "true":
            raise SystemExit("[WARN] Live mode disabled. Set ALLOW_REAL_TRADING=true to enable.")
        from src.pipeline_live import LivePipeline
        pipeline = LivePipeline(root, runtime_mode="live")
        pipeline.run_loop()
```
* **Findings:** All 11 symbols **successfully contain** this live support block in `src/main.py` at line 39. There are no missing symbols.

---

## 4. Signal Bottleneck Evaluation

Since the fleet was started using `start_all_bots.bat`, it locked all agents to `--mode paper`, resulting in paper routing execution. If the user wishes to unlock active real/paper execution flow under live conditions, they must transition to using `start_all_bots_live_demo.bat`.

### Summary Matrix
- **Is local code updated to PR #1 RC02?** YES
- **Is `start_all_bots` using updated code?** YES
- **Is `start_all_bots` still paper-locked?** YES
- **Which launcher should be used now?** `start_all_bots_live_demo.bat`
- **Did any symbol reach execution layer?** NO (All restricted to mock paper engine)
- **Main Bottleneck:** **START_ALL_STILL_PAPER_LOCKED**

---

## 5. Next Steps & Recommendations

1. **Launcher Transition:** Decommission the use of `start_all_bots.bat` for forward-demo testing. Deploy using `start_all_bots_live_demo.bat`.
2. **Environment Validation:** Verify that environment variables `ALLOW_REAL_TRADING=true` are correctly registered in the running shell sessions.
3. **Symbol Config Audit:** Inspect `config/symbol.yaml` under each project directory to verify that `live_capital_enabled` parameters are configured appropriately (either `false` for paper fallback or `true` for live broker order routing).
