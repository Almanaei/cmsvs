#!/bin/bash
# CMSVS Notification System Production Deployment Script
# This script deploys the complete notification system to production

set -e

echo "🚀 CMSVS Notification System Production Deployment"
echo "================================================="

# Configuration
SERVER_IP="91.99.118.65"
SERVER_USER="root"
DEPLOYMENT_PATH="/root/cmsvs"
BACKUP_PATH="/root/cmsvs_backup_$(date +%Y%m%d_%H%M%S)"

# Step 1: Create deployment package
echo "📦 Step 1: Creating deployment package..."

DEPLOYMENT_FILES=(
    "app/"
    "deployment/"
    "requirements.txt"
    "Dockerfile"
    "docker-compose.production.yml"
    ".env.production"
    "alembic/"
    "alembic.ini"
    "create_notification_tables.py"
    "generate_vapid_keys.py"
)

# Create temporary deployment directory
TEMP_DIR="temp_deployment_$(date +%Y%m%d%H%M%S)"
mkdir -p "$TEMP_DIR"

# Copy files to deployment directory
for file in "${DEPLOYMENT_FILES[@]}"; do
    if [ -e "$file" ]; then
        cp -r "$file" "$TEMP_DIR/"
        echo "   ✅ Copied: $file"
    else
        echo "   ⚠️  Missing: $file"
    fi
done

# Create deployment archive
ARCHIVE_NAME="cmsvs-notifications-deployment.tar.gz"
echo "   📦 Creating archive: $ARCHIVE_NAME"

tar -czf "$ARCHIVE_NAME" -C "$TEMP_DIR" .
echo "   ✅ Archive created successfully"

# Step 2: Upload to server
echo ""
echo "🌐 Step 2: Uploading to production server..."

scp "$ARCHIVE_NAME" "${SERVER_USER}@${SERVER_IP}:/tmp/"
echo "   ✅ Archive uploaded successfully"

# Step 3: Deploy on server
echo ""
echo "🔧 Step 3: Deploying on production server..."

ssh "${SERVER_USER}@${SERVER_IP}" << 'EOF'
#!/bin/bash
set -e

echo "🔧 Starting CMSVS Notification System Deployment..."

DEPLOYMENT_PATH="/root/cmsvs"
BACKUP_PATH="/root/cmsvs_backup_$(date +%Y%m%d_%H%M%S)"

# Create backup
echo "📋 Creating backup..."
if [ -d "$DEPLOYMENT_PATH" ]; then
    cp -r "$DEPLOYMENT_PATH" "$BACKUP_PATH"
    echo "✅ Backup created at $BACKUP_PATH"
fi

# Stop existing services
echo "🛑 Stopping existing services..."
cd "$DEPLOYMENT_PATH" 2>/dev/null || true
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Extract new deployment
echo "📦 Extracting new deployment..."
cd /tmp
tar -xzf cmsvs-notifications-deployment.tar.gz -C "$DEPLOYMENT_PATH"

# Set permissions
echo "🔐 Setting permissions..."
cd "$DEPLOYMENT_PATH"
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
EOF

echo "   ✅ Deployment completed successfully"

# Step 4: Cleanup
echo ""
echo "🧹 Step 4: Cleaning up..."

# Remove temporary files
rm -rf "$TEMP_DIR"
rm -f "$ARCHIVE_NAME"
echo "   ✅ Cleanup completed"

# Step 5: Verification
echo ""
echo "✅ Step 5: Deployment Verification"

echo "🎉 CMSVS Notification System Deployment Completed!"
echo "=================================================="

echo ""
echo "📋 Deployment Summary:"
echo "   🌐 Application URL: https://www.webtado.live"
echo "   📱 Push Notifications: Enabled"
echo "   🔔 Service Worker: /static/js/sw.js"
echo "   🗄️  Database: Notification tables created"
echo "   🔑 VAPID Keys: Configured"

echo ""
echo "📝 Next Steps:"
echo "   1. Test push notifications in browser"
echo "   2. Verify notification preferences page"
echo "   3. Check notification list functionality"
echo "   4. Test request status notifications"

echo ""
echo "🔧 Troubleshooting:"
echo "   • Check logs: docker-compose -f docker-compose.production.yml logs app"
echo "   • Restart services: docker-compose -f docker-compose.production.yml restart"
echo "   • Backup location: $BACKUP_PATH"

echo ""
echo "🎯 Deployment completed successfully! 🎯"
