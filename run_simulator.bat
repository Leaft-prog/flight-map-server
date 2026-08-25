@echo off
:: Self-elevate to Administrator 
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~f0' -ArgumentList '%* ' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
python main_simulator.py %*

pause