@echo off
REM Windows batch launcher for the HR Data Pipeline
REM Double-click to run the entire pipeline automatically

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo  Indus Weave Textiles HR Data Pipeline
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python is not installed or not in PATH.
    echo Please install Python 3.10 or later from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version

REM Check if venv exists, create if needed
if not exist "venv" (
    echo.
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [FAIL] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate venv
echo.
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [FAIL] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Install requirements
echo.
echo [INFO] Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [FAIL] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Run the pipeline
echo.
echo [INFO] Starting pipeline (this may take a few minutes)...
echo.
python run_pipeline.py --clean
if errorlevel 1 (
    echo.
    echo [FAIL] Pipeline failed. See errors above for details.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] Pipeline completed successfully!
echo ============================================================
echo.
echo Output files:
echo   - Database: db/warehouse.sqlite (star schema data)
echo   - Analytics: analytics/results/ (CSV files with answers)
echo   - Checks: database table warehouse.dq_results
echo.
pause
