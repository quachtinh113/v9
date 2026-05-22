@echo off
SETLOCAL EnableDelayedExpansion

title Quant Fleet Controller V9.3.1
start "" "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\MetaTrader 5\MetaTrader 5.lnk"
echo ============================================================
echo   INSTITUTIONAL MULTI-AGENT TRADING FLEET (10 AGENTS)
echo ============================================================
echo.

set ROOT_DIR=c:\Quant Trade\v9\V9\projects

echo [1/10] Starting GBPUSD Agent...
start "AGENT-GBPUSD" /D "%ROOT_DIR%\quant_v9_3_1_gbpusd" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [2/10] Starting EURUSD Agent...
start "AGENT-EURUSD" /D "%ROOT_DIR%\quant_v9_3_1_eurusd" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [3/10] Starting USDJPY Agent...
start "AGENT-USDJPY" /D "%ROOT_DIR%\quant_v9_3_1_usdjpy" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [4/10] Starting AUDUSD Agent...
start "AGENT-AUDUSD" /D "%ROOT_DIR%\quant_v9_3_1_audusd" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [5/10] Starting USDCAD Agent...
start "AGENT-USDCAD" /D "%ROOT_DIR%\quant_v9_3_1_usdcad" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [6/10] Starting USDCHF Agent...
start "AGENT-USDCHF" /D "%ROOT_DIR%\quant_v9_3_1_usdchf" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [7/10] Starting US30 Agent...
start "AGENT-US30" /D "%ROOT_DIR%\quant_v9_3_1_us30" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [8/10] Starting US100 Agent...
start "AGENT-US100" /D "%ROOT_DIR%\quant_v9_3_1_us100" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [9/10] Starting US500 Agent...
start "AGENT-US500" /D "%ROOT_DIR%\quant_v9_3_1_us500" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"
ping -n 3 127.0.0.1 >nul

echo [10/10] Starting XAUUSD Agent...
start "AGENT-XAUUSD" /D "%ROOT_DIR%\quant_v9_3_1_xauusd" cmd /k "set PYTHONPATH=. && python -m src.main --mode live"

echo.
echo ============================================================
echo   ALL AGENTS DEPLOYED. MONITOR EACH WINDOW FOR STATUS.
echo ============================================================
