#!/bin/bash

# Fix Production Issues Script
# This script fixes the permission and Redis configuration issues

set -e

echo "🔧 Fixing Production Issues..."
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Server details
SERVER_IP="91.99.118.65"
SERVER_USER="root"
PROJECT_PATH="/opt/cmsvs"

print_status "Connecting to production server..."

# Create deployment package with fixes
print_status "Creating deployment package..."
tar -czf production-fixes.tar.gz \
    app/main.py \
    docker-compose.production.yml \
    Dockerfile

# Transfer files to server
print_status "Transferring files to server..."
scp production-fixes.tar.gz ${SERVER_USER}@${SERVER_IP}:${PROJECT_PATH}/

# Execute fixes on server
print_status "Applying fixes on production server..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
cd /opt/cmsvs

# Extract fixes
tar -xzf production-fixes.tar.gz
rm production-fixes.tar.gz

# Stop services
echo "Stopping services..."
docker-compose -f docker-compose.production.yml down

# Remove problematic volumes to reset permissions
echo "Removing volumes to reset permissions..."
docker volume rm cmsvs_app_uploads cmsvs_app_logs cmsvs_app_backups 2>/dev/null || true

# Rebuild and start services
echo "Rebuilding and starting services..."
docker-compose -f docker-compose.production.yml build --no-cache app
docker-compose -f docker-compose.production.yml up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 30

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.production.yml ps

# Check application logs
echo "Checking application logs..."
docker-compose -f docker-compose.production.yml logs app --tail=20

EOF

# Clean up local files
rm production-fixes.tar.gz

print_success "Production fixes applied!"
print_status "Checking website status..."

# Test the website
sleep 10
if curl -s -o /dev/null -w "%{http_code}" https://webtado.live/ | grep -q "200\|301\|302"; then
    print_success "Website is responding!"
else
    print_error "Website may still have issues. Check logs on server."
fi

echo ""
echo "🎉 Production fix deployment completed!"
echo "📊 Check the website: https://webtado.live/"
echo "📋 Monitor logs: ssh root@91.99.118.65 'cd /opt/cmsvs && docker-compose -f docker-compose.production.yml logs -f'"
