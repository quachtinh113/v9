@echo off
SETLOCAL EnableDelayedExpansion

title Quant Fleet Controller V9.3.1
echo ============================================================
echo   INSTITUTIONAL MULTI-AGENT TRADING FLEET (11 AGENTS)
echo ============================================================
echo.

set ROOT_DIR=%~dp0projects
set SYMBOLS=gbpusd eurusd usdjpy audusd usdcad usdchf us30 us100 us500 xauusd btcusd

set MODE=%QUANT_RUNTIME_MODE%
if "%MODE%"=="" set MODE=paper

echo Launching fleet in %MODE% mode...

echo [1/11] Starting GBPUSD Agent...
start "AGENT-GBPUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_gbpusd && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [2/11] Starting EURUSD Agent...
start "AGENT-EURUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_eurusd && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [3/11] Starting USDJPY Agent...
start "AGENT-USDJPY" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdjpy && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [4/11] Starting AUDUSD Agent...
start "AGENT-AUDUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_audusd && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [5/11] Starting USDCAD Agent...
start "AGENT-USDCAD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdcad && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [6/11] Starting USDCHF Agent...
start "AGENT-USDCHF" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdchf && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [7/11] Starting US30 Agent...
start "AGENT-US30" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us30 && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [8/11] Starting US100 Agent...
start "AGENT-US100" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us100 && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [9/11] Starting US500 Agent...
start "AGENT-US500" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us500 && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [10/11] Starting XAUUSD Agent...
start "AGENT-XAUUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_xauusd && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo [11/11] Starting BTCUSD Agent...
start "AGENT-BTCUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_btcusd && set PYTHONPATH=.&& python -m src.main --mode %MODE%"

echo.
echo ============================================================
echo   ALL AGENTS DEPLOYED. MONITOR EACH WINDOW FOR STATUS.
echo ============================================================
pause
