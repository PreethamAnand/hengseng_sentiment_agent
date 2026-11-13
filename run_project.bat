@echo off
setlocal enabledelayedexpansion
title HengSeng / KRX Sentiment Price Prediction Agent

echo ===============================================================================
echo        HengSeng / KRX Sentiment -^> n+1 Price Prediction Agent
echo ===============================================================================
echo.

:: 1. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.10 or higher from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Python detected:
python --version
echo.

:: 2. Install dependencies
echo [*] Checking and installing required dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Pip install encountered an issue, retrying without quiet flag...
    pip install -r requirements.txt
)
echo [*] Dependencies are up to date.
echo.

:: 3. Run unit tests
echo [*] Running test suite...
pytest -q tests
if errorlevel 1 (
    echo [WARNING] Some tests failed or pytest encountered a warning. Continuing...
) else (
    echo [OK] All unit tests passed!
)
echo.

:: 4. Prompt execution mode
echo ===============================================================================
echo Please select execution mode:
echo   [1] Demo Mode (Offline Synthetic Data - Instant evaluation, no API key needed) [DEFAULT]
echo   [2] Live Mode: KRX (Naver Finance + Telegram + Exa News + Yahoo Finance)
echo   [3] Live Mode: Full (HKEX + KRX Live Data)
echo   [4] Run Unit Tests Only
echo ===============================================================================
echo Automatically starting Demo Mode in 10 seconds if no key is pressed...
echo.

choice /C 1234 /N /T 10 /D 1 /M "Enter your choice [1, 2, 3, 4] (Default is 1): "
set USER_CHOICE=!errorlevel!

echo.
if "!USER_CHOICE!"=="1" (
    echo [*] Executing DEMO MODE (Offline Synthetic Pipeline)...
    python run_pipeline.py --demo
) else if "!USER_CHOICE!"=="2" (
    echo [*] Executing LIVE KRX PIPELINE...
    python run_pipeline.py --live --exchanges KRX --days 5
) else if "!USER_CHOICE!"=="3" (
    echo [*] Executing FULL LIVE PIPELINE (HKEX + KRX)...
    python run_pipeline.py --live --days 5
) else if "!USER_CHOICE!"=="4" (
    echo [*] Running full tests...
    pytest -v tests
    goto :done
)

if errorlevel 1 (
    echo.
    echo [ERROR] The pipeline execution encountered an error.
    echo If running Live Mode, please ensure your API keys in .env are valid and have credits.
    echo You can always run Demo Mode without any API keys.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo [*] Execution completed successfully!
echo [*] Generated Output Artifacts (in outputs/ folder):
echo      - outputs\report.html       (Interactive visual dashboard with charts)
echo      - outputs\predictions.csv   (Model predictions, direction, trade signals)
echo      - outputs\metrics.json      (OOS performance metrics: MAE, RMSE, dir_acc)
echo      - outputs\posts.csv         (Normalized social sentiment posts)
echo      - outputs\news.csv          (Normalized Exa news items)
echo ===============================================================================
echo.
echo [*] Opening visual report in your default browser...
if exist "outputs\report.html" (
    start "" "outputs\report.html"
)

:done
echo.
echo Press any key to exit...
pause >nul
