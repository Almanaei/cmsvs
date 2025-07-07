@echo off
echo ========================================
echo Starting PostgreSQL Server
echo ========================================

echo.
echo Method 1: Starting PostgreSQL service...
net start postgresql-x64-15 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL service started successfully!
    goto :check_connection
)

echo Trying alternative service names...
net start postgresql-x64-14 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL service started successfully!
    goto :check_connection
)

net start postgresql-x64-13 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL service started successfully!
    goto :check_connection
)

net start postgresql 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL service started successfully!
    goto :check_connection
)

echo ⚠️  Could not start PostgreSQL service automatically.
echo.
echo Please try one of these methods:
echo.
echo 1. Open Services (services.msc) and start PostgreSQL manually
echo 2. Use pgAdmin to start the server
echo 3. Check if PostgreSQL is already running
echo.

:check_connection
echo.
echo Checking PostgreSQL connection...
echo.

:: Try to connect to PostgreSQL
psql -h localhost -U postgres -c "SELECT version();" 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL is running and accessible!
    echo.
    echo You can now run: start-local.bat
    echo.
) else (
    echo ❌ Cannot connect to PostgreSQL
    echo.
    echo Troubleshooting steps:
    echo 1. Check if PostgreSQL service is running in Services
    echo 2. Verify PostgreSQL is installed
    echo 3. Check if port 5432 is available
    echo 4. Try connecting with pgAdmin
    echo.
)

echo.
echo Press any key to continue...
pause >nul
