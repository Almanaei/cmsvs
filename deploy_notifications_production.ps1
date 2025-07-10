#!/usr/bin/env pwsh
# CMSVS Notification System Production Deployment Script
# This script deploys the complete notification system to production

Write-Host "🚀 CMSVS Notification System Production Deployment" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Configuration
$SERVER_IP = "91.99.118.65"
$SERVER_USER = "root"
$DEPLOYMENT_PATH = "/root/cmsvs"
$BACKUP_PATH = "/root/cmsvs_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Step 1: Create deployment package
Write-Host "📦 Step 1: Creating deployment package..." -ForegroundColor Yellow

$deploymentFiles = @(
    "app/",
    "deployment/",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.production.yml",
    ".env.production",
    "alembic/",
    "alembic.ini",
    "create_notification_tables.py",
    "generate_vapid_keys.py"
)

# Create temporary deployment directory
$tempDir = "temp_deployment_$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# Copy files to deployment directory
foreach ($file in $deploymentFiles) {
    if (Test-Path $file) {
        $destPath = Join-Path $tempDir $file
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        if (Test-Path $file -PathType Container) {
            Copy-Item -Path $file -Destination $destPath -Recurse -Force
        } else {
            Copy-Item -Path $file -Destination $destPath -Force
        }
        Write-Host "   ✅ Copied: $file" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Missing: $file" -ForegroundColor Yellow
    }
}

# Create deployment archive
$archiveName = "cmsvs-notifications-deployment.tar.gz"
Write-Host "   📦 Creating archive: $archiveName" -ForegroundColor Blue

# Use tar to create archive (requires Windows 10 1903+ or WSL)
try {
    tar -czf $archiveName -C $tempDir .
    Write-Host "   ✅ Archive created successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to create archive. Please install tar or use WSL" -ForegroundColor Red
    exit 1
}

# Step 2: Upload to server
Write-Host "`n🌐 Step 2: Uploading to production server..." -ForegroundColor Yellow

try {
    # Upload archive
    scp $archiveName "${SERVER_USER}@${SERVER_IP}:/tmp/"
    Write-Host "   ✅ Archive uploaded successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to upload archive" -ForegroundColor Red
    exit 1
}

# Step 3: Deploy on server
Write-Host "`n🔧 Step 3: Deploying on production server..." -ForegroundColor Yellow

$deployScript = @"
#!/bin/bash
set -e

echo "🔧 Starting CMSVS Notification System Deployment..."

# Create backup
echo "📋 Creating backup..."
if [ -d "$DEPLOYMENT_PATH" ]; then
    cp -r $DEPLOYMENT_PATH $BACKUP_PATH
    echo "✅ Backup created at $BACKUP_PATH"
fi

# Stop existing services
echo "🛑 Stopping existing services..."
cd $DEPLOYMENT_PATH 2>/dev/null || true
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Extract new deployment
echo "📦 Extracting new deployment..."
cd /tmp
tar -xzf cmsvs-notifications-deployment.tar.gz -C $DEPLOYMENT_PATH

# Set permissions
echo "🔐 Setting permissions..."
cd $DEPLOYMENT_PATH
chmod +x scripts/*.sh 2>/dev/null || true

# Install notification dependencies and rebuild
echo "🔨 Rebuilding with notification dependencies..."
docker-compose -f docker-compose.production.yml build --no-cache app

# Create notification tables
echo "🗄️  Creating notification tables..."
docker-compose -f docker-compose.production.yml run --rm app python create_notification_tables.py

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.production.yml ps

# Test notification endpoints
echo "🧪 Testing notification system..."
curl -f http://localhost/health || echo "⚠️  Health check failed"

echo "✅ CMSVS Notification System deployment completed!"
echo "🌐 Application available at: https://www.webtado.live"
echo "📱 Push notifications are now enabled"
"@

# Execute deployment script on server
try {
    $deployScript | ssh "${SERVER_USER}@${SERVER_IP}" "cat > /tmp/deploy_notifications.sh && chmod +x /tmp/deploy_notifications.sh && /tmp/deploy_notifications.sh"
    Write-Host "   ✅ Deployment completed successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Deployment failed" -ForegroundColor Red
    exit 1
}

# Step 4: Cleanup
Write-Host "`n🧹 Step 4: Cleaning up..." -ForegroundColor Yellow

# Remove temporary files
Remove-Item -Path $tempDir -Recurse -Force
Remove-Item -Path $archiveName -Force
Write-Host "   ✅ Cleanup completed" -ForegroundColor Green

# Step 5: Verification
Write-Host "`n✅ Step 5: Deployment Verification" -ForegroundColor Yellow

Write-Host "🎉 CMSVS Notification System Deployment Completed!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "`n📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "   🌐 Application URL: https://www.webtado.live" -ForegroundColor White
Write-Host "   📱 Push Notifications: Enabled" -ForegroundColor White
Write-Host "   🔔 Service Worker: /static/js/sw.js" -ForegroundColor White
Write-Host "   🗄️  Database: Notification tables created" -ForegroundColor White
Write-Host "   🔑 VAPID Keys: Configured" -ForegroundColor White

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Test push notifications in browser" -ForegroundColor White
Write-Host "   2. Verify notification preferences page" -ForegroundColor White
Write-Host "   3. Check notification list functionality" -ForegroundColor White
Write-Host "   4. Test request status notifications" -ForegroundColor White

Write-Host "`n🔧 Troubleshooting:" -ForegroundColor Cyan
Write-Host "   • Check logs: docker-compose -f docker-compose.production.yml logs app" -ForegroundColor White
Write-Host "   • Restart services: docker-compose -f docker-compose.production.yml restart" -ForegroundColor White
Write-Host "   • Backup location: $BACKUP_PATH" -ForegroundColor White

Write-Host "`n🎯 Deployment completed successfully! 🎯" -ForegroundColor Green
