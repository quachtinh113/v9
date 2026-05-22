# README - QUANT V9.3.1 LAPTOP TEST RELEASE

## Introduction
This is the pre-release packaging for running NowTrading Quant Core V9.3.1 on a local laptop test environment. Live trading is strictly disabled.

## How to Start the Dashboard
1. Open terminal in this folder.
2. Run command:
   ```bash
   python run_dashboard.py
   ```
3. Open browser at [http://localhost:8000](http://localhost:8000).

## How to Start the Bots
1. Run `start_all_bots.bat` to launch the 10 trading agents in separate shell processes.
2. They will run in Paper Trading mode by default.

## How to Stop the Bots (Emergency Stop)
1. Run `stop_all_bots.bat` to kill all running Python processes instantly.

## Where Logs are Stored
- Live execution decisions are logged in `projects/quant_v9_3_1_[symbol]/logs/live_pipeline_audit.ndjson`.

## How to Verify Paper Mode
- Open `projects/quant_v9_3_1_[symbol]/config/symbol.yaml` and verify that `live_capital_enabled` is absent or set to `false`.
- The agents will print "Paper Trading Mock Executed" in the command prompts on tick events.

## Critical Warnings
- DO NOT add real API credentials to `.env` in this directory.
- DO NOT run any bot with live capital enabled.
