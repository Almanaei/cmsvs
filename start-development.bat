@echo off
echo ========================================
echo Starting CMSVS Development Environment
echo ========================================

echo.
echo Checking Docker Desktop status...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop and wait for it to fully load, then run this script again.
    echo You can start Docker Desktop from:
    echo - Start Menu ^> Docker Desktop
    echo - Or double-click the Docker Desktop icon on your desktop
    echo.
    pause
    exit /b 1
)

echo ✅ Docker Desktop is running!
echo.

echo Stopping any existing containers...
docker compose -f docker-compose.development.yml down

echo.
echo Building and starting development environment...
echo This may take a few minutes on first run...
echo.

docker compose -f docker-compose.development.yml up --build -d

if %errorlevel% neq 0 (
    echo ❌ Failed to start development environment!
    echo.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ✅ Development environment started successfully!
echo.
echo 🌐 Application URLs:
echo    - Main App: http://localhost:8000
echo    - Admin Login: http://localhost:8000/admin/login
echo    - API Docs: http://localhost:8000/docs
echo.
echo 📋 Default Admin Credentials:
echo    - Email: almananei90@gmail.com
echo    - Password: admin123
echo.
echo 🔧 Services Status:
docker compose -f docker-compose.development.yml ps

echo.
echo 📊 To view logs, run:
echo    docker compose -f docker-compose.development.yml logs -f
echo.
echo 🛑 To stop the environment, run:
echo    docker compose -f docker-compose.development.yml down
echo.
echo Press any key to view live logs (Ctrl+C to exit logs)...
pause >nul

echo.
echo 📋 Showing live logs (Press Ctrl+C to exit):
docker compose -f docker-compose.development.yml logs -f
