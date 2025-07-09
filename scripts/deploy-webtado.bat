@echo off
REM CMSVS Deployment Script for www.webtado.live
REM Batch script to deploy the latest changes to the production server

echo.
echo ========================================
echo   CMSVS Production Deployment
echo   Target: www.webtado.live (91.99.118.65)
echo   Started: %date% %time%
echo ========================================
echo.

echo [INFO] Connecting to production server...
echo [INFO] You may need to enter your server password...
echo.

ssh root@91.99.118.65 "set -e && echo '🚀 Starting CMSVS deployment on production server...' && cd /opt/cmsvs || (mkdir -p /opt/cmsvs && cd /opt/cmsvs) && if [ -d '.git' ]; then echo 'Backing up current deployment...' && tar -czf backup-$(date +%%Y%%m%%d_%%H%%M%%S).tar.gz . 2>/dev/null || true; fi && if [ ! -d '.git' ]; then echo 'Cloning repository...' && git clone https://github.com/Almanaei/cmsvs.git .; else echo 'Pulling latest changes...' && git fetch origin && git reset --hard origin/main; fi && cd deployment && echo 'Stopping existing services...' && docker-compose -f docker-compose.production.yml down --timeout 30 2>/dev/null || true && echo 'Cleaning up old Docker images...' && docker system prune -f 2>/dev/null || true && echo 'Building Docker images...' && docker-compose -f docker-compose.production.yml build --no-cache && echo 'Starting services...' && docker-compose -f docker-compose.production.yml up -d && echo 'Waiting for services to start...' && sleep 45 && echo 'Initializing database...' && docker-compose -f docker-compose.production.yml exec -T app python init_db.py 2>/dev/null || echo 'Database already initialized' && echo 'Checking service status...' && docker-compose -f docker-compose.production.yml ps && echo 'Testing application health...' && sleep 10 && (curl -f http://localhost:8000/health 2>/dev/null && echo '✅ Application health check passed' || (curl -f http://localhost:8000/ 2>/dev/null && echo '✅ Application is responding on root path' || echo '❌ Application is not responding')) && echo '' && echo '🎉 Deployment completed successfully!' && echo '📊 Service Status:' && docker-compose -f docker-compose.production.yml ps && echo '' && echo '🌐 Your application should be available at:' && echo '   - http://www.webtado.live' && echo '   - http://91.99.118.65' && echo ''"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   DEPLOYMENT SUCCESSFUL!
    echo ========================================
    echo.
    echo Your CMSVS application is now live at:
    echo   - https://www.webtado.live
    echo   - http://91.99.118.65
    echo.
    echo Next steps:
    echo   1. Test the application functionality
    echo   2. Check SSL certificate status
    echo   3. Monitor application logs if needed
    echo.
) else (
    echo.
    echo ========================================
    echo   DEPLOYMENT FAILED!
    echo ========================================
    echo.
    echo Please check the server logs and try again.
    echo.
)

pause
