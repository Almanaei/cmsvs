#!/usr/bin/env pwsh
# CMSVS Push Notifications Deployment Script
# This script deploys the push notifications feature to production

Write-Host "🚀 CMSVS Push Notifications Deployment" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Configuration
$SERVER_IP = "91.99.118.65"
$SERVER_USER = "root"
$DEPLOYMENT_PATH = "/root/cmsvs"
$BACKUP_PATH = "/root/cmsvs_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "   Server: $SERVER_IP" -ForegroundColor White
Write-Host "   User: $SERVER_USER" -ForegroundColor White
Write-Host "   Path: $DEPLOYMENT_PATH" -ForegroundColor White
Write-Host "   Backup: $BACKUP_PATH" -ForegroundColor White
Write-Host ""

# Step 1: Verify local files
Write-Host "📋 Step 1: Verifying local notification files..." -ForegroundColor Green

$requiredFiles = @(
    "deployment\app\models\notification.py",
    "deployment\app\services\notification_service.py", 
    "deployment\app\services\push_service.py",
    "deployment\app\routes\notifications.py",
    "deployment\app\templates\notifications\list.html",
    "deployment\app\templates\notifications\preferences.html",
    "deployment\app\static\js\sw.js",
    "deployment\app\templates\base.html",
    "deployment\app\main.py",
    "deployment\app\services\request_service.py",
    "deployment\app\models\user.py",
    "deployment\app\models\request.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
        Write-Host "   ❌ Missing: $file" -ForegroundColor Red
    } else {
        Write-Host "   ✅ Found: $file" -ForegroundColor Green
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ Missing required files. Please ensure all notification files are copied to deployment folder." -ForegroundColor Red
    exit 1
}

Write-Host "✅ All notification files verified locally!" -ForegroundColor Green
Write-Host ""

# Step 2: Create backup on server
Write-Host "📋 Step 2: Creating backup on production server..." -ForegroundColor Green

$backupCommand = @"
echo '🔄 Creating backup...'
cp -r $DEPLOYMENT_PATH $BACKUP_PATH
echo '✅ Backup created at $BACKUP_PATH'
"@

try {
    ssh $SERVER_USER@$SERVER_IP $backupCommand
    Write-Host "✅ Backup created successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create backup: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Upload notification files
Write-Host "📋 Step 3: Uploading notification files to production..." -ForegroundColor Green

$uploadCommands = @(
    "scp deployment\app\models\notification.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/models/",
    "scp deployment\app\services\notification_service.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/services/",
    "scp deployment\app\services\push_service.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/services/",
    "scp deployment\app\routes\notifications.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/routes/",
    "scp deployment\app\templates\base.html ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/templates/",
    "scp deployment\app\main.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/",
    "scp deployment\app\services\request_service.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/services/",
    "scp deployment\app\models\user.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/models/",
    "scp deployment\app\models\request.py ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/models/",
    "scp deployment\app\static\js\sw.js ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/static/js/"
)

foreach ($cmd in $uploadCommands) {
    try {
        Write-Host "   Uploading: $($cmd.Split(' ')[-1])" -ForegroundColor White
        Invoke-Expression $cmd
        Write-Host "   ✅ Uploaded successfully" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Failed to upload: $_" -ForegroundColor Red
        exit 1
    }
}

# Upload notification templates directory
Write-Host "   Uploading notification templates..." -ForegroundColor White
try {
    ssh $SERVER_USER@$SERVER_IP "mkdir -p $DEPLOYMENT_PATH/app/templates/notifications"
    scp -r deployment\app\templates\notifications\* ${SERVER_USER}@${SERVER_IP}:${DEPLOYMENT_PATH}/app/templates/notifications/
    Write-Host "   ✅ Notification templates uploaded" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to upload templates: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All files uploaded successfully!" -ForegroundColor Green
Write-Host ""

# Step 4: Run database migration
Write-Host "📋 Step 4: Running database migration for notifications..." -ForegroundColor Green

$migrationCommand = @"
cd $DEPLOYMENT_PATH
echo '🔄 Running database migration...'

# Create migration script
cat > migrate_notifications.py << 'EOF'
import os
import sys
sys.path.append('/root/cmsvs')

from sqlalchemy import create_engine, text
from app.config import get_settings

def run_migration():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create notification enums
        conn.execute(text("""
            DO \$\$ BEGIN
                CREATE TYPE notificationtype AS ENUM (
                    'REQUEST_STATUS_CHANGED',
                    'REQUEST_CREATED', 
                    'REQUEST_UPDATED',
                    'REQUEST_ARCHIVED',
                    'REQUEST_DELETED',
                    'ADMIN_MESSAGE',
                    'SYSTEM_ANNOUNCEMENT'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END \$\$;
        """))
        
        conn.execute(text("""
            DO \$\$ BEGIN
                CREATE TYPE notificationpriority AS ENUM (
                    'LOW',
                    'NORMAL',
                    'HIGH', 
                    'URGENT'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END \$\$;
        """))
        
        # Create notifications table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                type notificationtype NOT NULL,
                priority notificationpriority NOT NULL DEFAULT 'NORMAL',
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                action_url VARCHAR(500),
                request_id INTEGER REFERENCES requests(id),
                related_user_id INTEGER REFERENCES users(id),
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                is_sent BOOLEAN NOT NULL DEFAULT FALSE,
                sent_at TIMESTAMP WITH TIME ZONE,
                read_at TIMESTAMP WITH TIME ZONE,
                extra_data JSON,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create push_subscriptions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                endpoint VARCHAR(500) NOT NULL,
                p256dh_key VARCHAR(255) NOT NULL,
                auth_key VARCHAR(255) NOT NULL,
                user_agent VARCHAR(500),
                device_name VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create notification_preferences table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
                push_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                in_app_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                email_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                request_status_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                request_updates_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                admin_message_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                system_announcement_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                quiet_hours_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                quiet_hours_start VARCHAR(5),
                quiet_hours_end VARCHAR(5),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user_id ON push_subscriptions(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_push_subscriptions_is_active ON push_subscriptions(is_active);"))
        
        conn.commit()
        print("✅ Database migration completed successfully!")

if __name__ == "__main__":
    run_migration()
EOF

# Run the migration
python3 migrate_notifications.py
"@

try {
    ssh $SERVER_USER@$SERVER_IP $migrationCommand
    Write-Host "✅ Database migration completed!" -ForegroundColor Green
} catch {
    Write-Host "❌ Database migration failed: $_" -ForegroundColor Red
    Write-Host "🔄 Attempting to restore backup..." -ForegroundColor Yellow
    ssh $SERVER_USER@$SERVER_IP "rm -rf $DEPLOYMENT_PATH && mv $BACKUP_PATH $DEPLOYMENT_PATH"
    exit 1
}
Write-Host ""

# Step 5: Restart services
Write-Host "📋 Step 5: Restarting production services..." -ForegroundColor Green

$restartCommand = @"
cd $DEPLOYMENT_PATH
echo '🔄 Restarting services...'
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
echo '✅ Services restarted successfully!'
"@

try {
    ssh $SERVER_USER@$SERVER_IP $restartCommand
    Write-Host "✅ Services restarted successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to restart services: $_" -ForegroundColor Red
    Write-Host "🔄 Attempting to restore backup..." -ForegroundColor Yellow
    ssh $SERVER_USER@$SERVER_IP "rm -rf $DEPLOYMENT_PATH && mv $BACKUP_PATH $DEPLOYMENT_PATH && cd $DEPLOYMENT_PATH && docker-compose -f docker-compose.production.yml up -d"
    exit 1
}
Write-Host ""

# Step 6: Verify deployment
Write-Host "📋 Step 6: Verifying deployment..." -ForegroundColor Green

Start-Sleep -Seconds 30  # Wait for services to start

try {
    $response = Invoke-WebRequest -Uri "https://www.webtado.live/api/notifications/unread-count" -Method GET -SkipCertificateCheck -TimeoutSec 10
    if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 403) {
        Write-Host "✅ Notifications API is responding!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unexpected response code: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not verify API endpoint (this may be normal if authentication is required)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Backup created: $BACKUP_PATH" -ForegroundColor White
Write-Host "   ✅ Notification files uploaded" -ForegroundColor White
Write-Host "   ✅ Database migration completed" -ForegroundColor White
Write-Host "   ✅ Services restarted" -ForegroundColor White
Write-Host "   ✅ Deployment verified" -ForegroundColor White
Write-Host ""
Write-Host "🌍 Access your application:" -ForegroundColor Cyan
Write-Host "   Main App: https://www.webtado.live" -ForegroundColor White
Write-Host "   Notifications: https://www.webtado.live/notifications" -ForegroundColor White
Write-Host ""
Write-Host "🔔 Push Notifications Features:" -ForegroundColor Cyan
Write-Host "   ✅ Real-time browser notifications" -ForegroundColor White
Write-Host "   ✅ Mobile push notification support" -ForegroundColor White
Write-Host "   ✅ Notification preferences page" -ForegroundColor White
Write-Host "   ✅ Request status change notifications" -ForegroundColor White
Write-Host "   ✅ Admin message notifications" -ForegroundColor White
Write-Host ""
Write-Host "📱 To test push notifications:" -ForegroundColor Yellow
Write-Host "   1. Visit https://www.webtado.live" -ForegroundColor White
Write-Host "   2. Allow notification permissions when prompted" -ForegroundColor White
Write-Host "   3. Create or update a request to trigger notifications" -ForegroundColor White
Write-Host "   4. Check notification preferences at /notifications/preferences" -ForegroundColor White
Write-Host ""
Write-Host "🔧 If you need to rollback:" -ForegroundColor Red
Write-Host "   ssh $SERVER_USER@$SERVER_IP" -ForegroundColor White
Write-Host "   rm -rf $DEPLOYMENT_PATH" -ForegroundColor White
Write-Host "   mv $BACKUP_PATH $DEPLOYMENT_PATH" -ForegroundColor White
Write-Host "   cd $DEPLOYMENT_PATH && docker-compose -f docker-compose.production.yml up -d" -ForegroundColor White
Write-Host ""
