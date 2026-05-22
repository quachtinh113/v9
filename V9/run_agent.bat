@echo off
rem Helper script to launch a trading agentem Arguments: %1 = Agent title, %2 = Agent project directory
set "AGENT_TITLE=%~1"
set "AGENT_DIR=%~2"

rem Set window title
title %AGENT_TITLE%

rem Change to project directory
cd /d "%AGENT_DIR%"

rem Ensure Python path includes current directory
set PYTHONPATH=.

rem Launch the agent
python -m src.main --mode live
