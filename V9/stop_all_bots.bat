@echo off
title Quant Fleet Terminator
echo Terminating all Python trading processes...
taskkill /F /IM python.exe /T
taskkill /F /IM python3.exe /T
taskkill /F /FI "WINDOWTITLE eq AGENT-*" /T
echo Done.
pause
