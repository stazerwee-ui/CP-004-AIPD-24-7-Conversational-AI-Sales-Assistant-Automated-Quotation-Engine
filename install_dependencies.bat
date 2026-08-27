@echo off
title Solace Dignity Care - One-Click Dependency Installer
cd /d "%~dp0"

echo =========================================================
echo   SOLACE DIGNITY CARE - ONE-CLICK INSTALLER
echo =========================================================
echo.

:: 1. Install Python Packages
echo [1/3] Installing Python packages...
pip install fastapi uvicorn requests pydantic numpy soundfile python-multipart faster-whisper kokoro-onnx onnxruntime fastembed
echo.

:: 2. Download Cloudflared for instant HTTPS tunnels
if not exist "tools\cloudflared.exe" if not exist "cloudflared.exe" (
    echo [2/3] Downloading Cloudflare Tunnel (tools\cloudflared.exe)...
    if not exist "tools" mkdir "tools"
    python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe', 'tools/cloudflared.exe')"
) else (
    echo [2/3] cloudflared.exe already exists.
)
echo.

:: 3. Download Kokoro-82M Voice AI Model Weights
echo [3/3] Downloading Kokoro Neural Voice models (~110MB)...
python -c "
import os, urllib.request

os.makedirs('models', exist_ok=True)
m_onnx = 'models/kokoro-v1.0.onnx' if not os.path.exists('kokoro-v1.0.onnx') else 'kokoro-v1.0.onnx'
m_bin = 'models/voices-v1.0.bin' if not os.path.exists('voices-v1.0.bin') else 'voices-v1.0.bin'

if not os.path.exists('models/kokoro-v1.0.onnx') and not os.path.exists('kokoro-v1.0.onnx'):
    print('Downloading kokoro-v1.0.onnx into models/... ')
    urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx', 'models/kokoro-v1.0.onnx')

if not os.path.exists('models/voices-v1.0.bin') and not os.path.exists('voices-v1.0.bin'):
    print('Downloading voices-v1.0.bin into models/... ')
    urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin', 'models/voices-v1.0.bin')

print('Kokoro-82M model ready!')
"
echo.

echo =========================================================
echo   ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
echo   You can now run start_live_demo.bat to start the app.
echo =========================================================
echo.
pause
