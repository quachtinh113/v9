@echo off
SETLOCAL EnableDelayedExpansion

title Quant Fleet Controller V9.3.1
echo ============================================================
echo   INSTITUTIONAL MULTI-AGENT TRADING FLEET (10 AGENTS)
echo ============================================================
echo.

set ROOT_DIR=d:\V9\projects
set SYMBOLS=gbpusd eurusd usdjpy audusd usdcad usdchf us30 us100 us500 xauusd

echo [1/10] Starting GBPUSD Agent...
start "AGENT-GBPUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_gbpusd && set PYTHONPATH=.&& python -m src.main --mode live"

echo [2/10] Starting EURUSD Agent...
start "AGENT-EURUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_eurusd && set PYTHONPATH=.&& python -m src.main --mode live"

echo [3/10] Starting USDJPY Agent...
start "AGENT-USDJPY" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdjpy && set PYTHONPATH=.&& python -m src.main --mode live"

echo [4/10] Starting AUDUSD Agent...
start "AGENT-AUDUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_audusd && set PYTHONPATH=.&& python -m src.main --mode live"

echo [5/10] Starting USDCAD Agent...
start "AGENT-USDCAD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdcad && set PYTHONPATH=.&& python -m src.main --mode live"

echo [6/10] Starting USDCHF Agent...
start "AGENT-USDCHF" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_usdchf && set PYTHONPATH=.&& python -m src.main --mode live"

echo [7/10] Starting US30 Agent...
start "AGENT-US30" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us30 && set PYTHONPATH=.&& python -m src.main --mode live"

echo [8/10] Starting US100 Agent...
start "AGENT-US100" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us100 && set PYTHONPATH=.&& python -m src.main --mode live"

echo [9/10] Starting US500 Agent...
start "AGENT-US500" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_us500 && set PYTHONPATH=.&& python -m src.main --mode live"

echo [10/10] Starting XAUUSD Agent...
start "AGENT-XAUUSD" cmd /k "cd /d %ROOT_DIR%\quant_v9_3_1_xauusd && set PYTHONPATH=.&& python -m src.main --mode live"

echo.
echo ============================================================
echo   ALL AGENTS DEPLOYED. MONITOR EACH WINDOW FOR STATUS.
echo ============================================================
pause
