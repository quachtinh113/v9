@echo off
SETLOCAL EnableDelayedExpansion

title Quant Fleet Controller V9.3.1 - LIVE DEMO MODE
echo ============================================================
echo   WARNING: LAUNCHING MULTI-AGENT TRADING FLEET IN LIVE DEMO
echo ============================================================
echo.

set ROOT_DIR=%~dp0projects
set SYMBOLS=gbpusd eurusd usdjpy audusd usdcad usdchf us30 us100 us500 xauusd btcusd

set MODE=live

set ALLOW_REAL_TRADING=true
set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK
set QUANT_RUNTIME_MODE=live
set LIVE_DEMO_ALLOWED=true

echo Launching fleet in %MODE% mode with real-trading safeguards...

echo [1/11] Starting GBPUSD Agent (LIVE DEMO)...
start "AGENT-GBPUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_gbpusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [2/11] Starting EURUSD Agent (LIVE DEMO)...
start "AGENT-EURUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_eurusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [3/11] Starting USDJPY Agent (LIVE DEMO)...
start "AGENT-USDJPY" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdjpy && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [4/11] Starting AUDUSD Agent (LIVE DEMO)...
start "AGENT-AUDUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_audusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [5/11] Starting USDCAD Agent (LIVE DEMO)...
start "AGENT-USDCAD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdcad && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [6/11] Starting USDCHF Agent (LIVE DEMO)...
start "AGENT-USDCHF" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdchf && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [7/11] Starting US30 Agent (LIVE DEMO)...
start "AGENT-US30" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us30 && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [8/11] Starting US100 Agent (LIVE DEMO)...
start "AGENT-US100" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us100 && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [9/11] Starting US500 Agent (LIVE DEMO)...
start "AGENT-US500" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us500 && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [10/11] Starting XAUUSD Agent (LIVE DEMO)...
start "AGENT-XAUUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_xauusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo [11/11] Starting BTCUSD Agent (LIVE DEMO)...
start "AGENT-BTCUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_btcusd && set PYTHONPATH=.&& set ALLOW_REAL_TRADING=true&& set HUMAN_LIVE_CONFIRM=YES_I_ACCEPT_LIVE_RISK&& set QUANT_RUNTIME_MODE=live&& set LIVE_DEMO_ALLOWED=true&& python -m src.main --mode %MODE%"

echo.
echo ============================================================
echo   ALL LIVE AGENTS DEPLOYED. MONITOR FOR STATUS & RISK VETOES.
echo ============================================================
pause
