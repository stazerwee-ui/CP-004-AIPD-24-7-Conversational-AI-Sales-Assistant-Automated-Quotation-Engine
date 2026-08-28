@echo off
title Solace Dignity Care - One-Click Dependency Installer
cd /d "%~dp0"

echo =========================================================
echo   SOLACE DIGNITY CARE - ONE-CLICK INSTALLER
echo =========================================================
echo.

:: 1. Install Python packages
echo [1/2] Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: pip install failed. Check your internet connection,
    echo   and that the virtual environment is active ^(venv\Scripts\activate^).
    pause
    exit /b 1
)
echo.

:: 2. Download model weights and the demo tunnel
::
:: All downloads are handled by the Python script rather than inline here, for
:: two reasons. A multi-line "python -c" does not work in a batch file - cmd
:: treats each line after the first as its own command, so the download silently
:: never runs while the installer still reports success. And the script uses the
:: requests library, which bundles its own CA certificates; urllib fails with
:: CERTIFICATE_VERIFY_FAILED on Windows Python builds that ship without a usable
:: certificate store.
echo [2/2] Downloading models and tools ^(~370 MB, this takes a few minutes^)...
echo.
python scripts\download_models.py
if errorlevel 1 (
    echo.
    echo =========================================================
    echo   SETUP INCOMPLETE - some downloads did not finish.
    echo   The app still runs; see the messages above for what
    echo   is affected. Re-run this script to try again.
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