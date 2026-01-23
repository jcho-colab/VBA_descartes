@echo off
REM ============================================
REM FTA Tariff Processor - Windows Launcher
REM ============================================

echo ========================================
echo FTA Tariff Processing System
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python detected
echo.

REM Check if dependencies are installed
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] First-time setup: Installing dependencies...
    echo This may take a few minutes...
    echo.
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo.
    echo [SUCCESS] Dependencies installed!
    echo.
) else (
    echo [INFO] Dependencies already installed
    echo.
)

REM Create folders if they don't exist
if not exist "input XML" mkdir "input XML"
if not exist "output_generated" mkdir "output_generated"

echo [INFO] Starting Tariff Processor...
echo.
echo The application will open in your browser.
echo Close this window to stop the application.
echo.
echo ========================================
echo.

REM Run Streamlit
streamlit run app.py --server.headless=true

pause
