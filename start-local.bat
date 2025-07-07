@echo off
echo ========================================
echo CMSVS Local Development with PostgreSQL
echo ========================================

echo.
echo This will start CMSVS using your local PostgreSQL database.
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH!
    echo Please install Python and try again.
    pause
    exit /b 1
)

echo ✅ Python is available
echo.

echo Starting local development environment...
python run-local-development.py

echo.
echo Press any key to exit...
pause >nul
