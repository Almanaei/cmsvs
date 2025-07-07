@echo off
echo ========================================
echo Setting up CMSVS Development Database
echo ========================================

echo.
echo This will create the development database and user.
echo You will be prompted for your PostgreSQL password.
echo.

echo Creating database and user...
psql -h localhost -U postgres -f setup-local-db.sql

if %errorlevel% equ 0 (
    echo.
    echo ✅ Database setup completed successfully!
    echo.
    echo Database: cmsvs_dev
    echo User: cmsvs_user
    echo Password: cmsvs_password123
    echo.
    echo You can now start the application with:
    echo python run.py
    echo.
) else (
    echo.
    echo ❌ Database setup failed.
    echo Please check the error messages above.
    echo.
)

echo Press any key to continue...
pause >nul
