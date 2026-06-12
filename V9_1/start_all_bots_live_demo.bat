@echo off
REM Supervised startup for Quant V9 fleet (LIVE DEMO mode)

REM Ensure we are in the V9_1 root directory
cd /d "%~dp0"

REM Run the Python supervisor which handles per‑bot logging and PID verification
python -u scripts\supervisor_launch.py

pause
