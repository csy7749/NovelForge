@echo off
setlocal

cd /d "%~dp0"

start "Backend" powershell -NoExit -Command "Set-Location -LiteralPath '%~dp0backend'; python main.py"
timeout /t 5 /nobreak >nul
start "Frontend Web" powershell -NoExit -Command "Set-Location -LiteralPath '%~dp0frontend'; npm run dev:web"
