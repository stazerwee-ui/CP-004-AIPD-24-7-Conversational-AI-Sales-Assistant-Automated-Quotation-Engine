@echo off
title Solace Dignity Care - One-Click Dependency Installer
cd /d "%~dp0"

echo =========================================================
echo   SOLACE DIGNITY CARE - ONE-CLICK INSTALLER
echo =========================================================
echo.

:: 1. Install Python packages
echo [1/3] Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: pip install failed. Check your internet connection,
    echo   and that the virtual environment is active ^(venv\Scripts\activate^).
    pause
    exit /b 1
)
echo.

:: 2. Download cloudflared for the HTTPS mobile demo
if exist "tools\cloudflared.exe" (
    echo [2/3] cloudflared.exe already present.
) else (
    echo [2/3] Downloading Cloudflare Tunnel...
    if not exist "tools" mkdir "tools"
    python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe', 'tools/cloudflared.exe')"
    if errorlevel 1 echo   WARNING: cloudflared download failed. The phone demo will not work.
)
echo.

:: 3. Download the Kokoro voice model weights
::
:: This calls a separate Python file rather than embedding the code here. A
:: multi-line "python -c" does not work inside a batch script - cmd treats each
:: line after the first as its own command, so the download silently never runs
:: while the installer still reports success.
echo [3/3] Downloading Kokoro voice models ^(~338 MB, this takes a few minutes^)...
echo.
python scripts\download_models.py
if errorlevel 1 (
    echo.
    echo =========================================================
    echo   SETUP INCOMPLETE - the voice models did not download.
    echo   Everything else works; only spoken replies are affected.
    echo   Re-run this script when you have a stable connection.
    echo =========================================================
    pause
    exit /b 1
)

echo.
echo =========================================================
echo   ALL DEPENDENCIES INSTALLED SUCCESSFULLY
echo.
echo   Next steps:
echo     1. copy .env.example .env
echo     2. Set SOLACE_ADMIN_TOKEN inside .env
echo     3. uvicorn main:app --host 127.0.0.1 --port 8000
echo =========================================================
echo.
pause