@echo off
title Quant Fleet Terminator
echo Terminating all Python trading processes...
taskkill /F /IM python.exe /T
echo Done.
pause
