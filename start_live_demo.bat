@echo off
title Solace Dignity Care - Live Demo Server
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo =========================================================
echo   SOLACE DIGNITY CARE - LIVE MOBILE DEMO LAUNCHER
echo =========================================================
echo.

:: 1. Start Python Backend if not already running on port 8000
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/2] Starting Solace Care Python Backend...
    start "Solace Backend Server" /min python main.py
    timeout /t 2 /nobreak >nul
) else (
    echo [1/2] Solace Care Backend is already running on port 8000.
)

:: 2. Launch Cloudflare Secure HTTPS Tunnel
echo [2/2] Starting Secure Cloudflare HTTPS Tunnel...
echo.
echo =========================================================
echo   YOUR PHONE LINK (Look for the https://... link below):
echo =========================================================
echo.

if exist ".\tools\cloudflared.exe" (
    .\tools\cloudflared.exe tunnel --url http://127.0.0.1:8000
) else (
    .\cloudflared.exe tunnel --url http://127.0.0.1:8000
)

echo.
echo Server stopped.
pause
