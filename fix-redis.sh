#!/bin/bash

# Fix Redis Connection Issues
echo "🔧 Fixing Redis connection issues..."

# Server details
SERVER_IP="91.99.118.65"
SERVER_USER="root"
PROJECT_PATH="/opt/cmsvs"

# Create deployment package with Redis fixes
echo "Creating Redis fixes package..."
tar -czf redis-fixes.tar.gz \
    docker-compose.production.yml \
    .env.production

# Transfer files to server
echo "Transferring files to server..."
scp redis-fixes.tar.gz ${SERVER_USER}@${SERVER_IP}:${PROJECT_PATH}/

# Execute fixes on server
echo "Applying Redis fixes on production server..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
cd /opt/cmsvs

# Extract fixes
tar -xzf redis-fixes.tar.gz
rm redis-fixes.tar.gz

# Restart Redis and app services to apply fixes
echo "Restarting Redis and app services..."
docker-compose -f docker-compose.production.yml restart redis app

# Wait for services to restart
echo "Waiting for services to restart..."
sleep 20

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.production.yml ps

# Check Redis connection
echo "Testing Redis connection..."
docker-compose -f docker-compose.production.yml exec -T redis redis-cli -a "5IdBdB2AWPKuIigfjEujtB6Gd" ping

EOF

# Clean up local files
rm redis-fixes.tar.gz

echo "✅ Redis fixes applied!"
echo "🌐 Website should now be fully functional: https://webtado.live/"
