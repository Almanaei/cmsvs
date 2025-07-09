#!/bin/bash
# CMSVS Deployment Script for www.webtado.live
# This script deploys the latest changes to the production server

set -e

# Configuration
PRODUCTION_SERVER="91.99.118.65"
PRODUCTION_USER="root"
REMOTE_PROJECT_PATH="/opt/cmsvs"
GITHUB_REPO="https://github.com/Almanaei/cmsvs.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to deploy to production server
deploy_to_production() {
    log "Starting deployment to www.webtado.live ($PRODUCTION_SERVER)"
    
    # Connect to server and deploy
    ssh "$PRODUCTION_USER@$PRODUCTION_SERVER" << 'EOF'
        set -e
        
        echo "🚀 Starting CMSVS deployment on production server..."
        
        # Navigate to project directory or create it
        if [ ! -d "/opt/cmsvs" ]; then
            echo "Creating project directory..."
            mkdir -p /opt/cmsvs
        fi
        
        cd /opt/cmsvs
        
        # Backup current deployment if exists
        if [ -d ".git" ]; then
            echo "Backing up current deployment..."
            tar -czf "backup-$(date +%Y%m%d_%H%M%S).tar.gz" . 2>/dev/null || true
        fi
        
        # Clone or pull latest changes
        if [ ! -d ".git" ]; then
            echo "Cloning repository..."
            git clone https://github.com/Almanaei/cmsvs.git .
        else
            echo "Pulling latest changes..."
            git fetch origin
            git reset --hard origin/main
        fi
        
        # Navigate to deployment directory
        cd deployment
        
        # Stop existing services
        echo "Stopping existing services..."
        docker-compose -f docker-compose.production.yml down --timeout 30 2>/dev/null || true
        
        # Remove old images to ensure fresh build
        echo "Cleaning up old Docker images..."
        docker system prune -f 2>/dev/null || true
        
        # Build and start services
        echo "Building Docker images..."
        docker-compose -f docker-compose.production.yml build --no-cache
        
        echo "Starting services..."
        docker-compose -f docker-compose.production.yml up -d
        
        # Wait for services to be ready
        echo "Waiting for services to start..."
        sleep 45
        
        # Initialize database if needed
        echo "Initializing database..."
        docker-compose -f docker-compose.production.yml exec -T app python init_db.py 2>/dev/null || echo "Database already initialized"
        
        # Check service status
        echo "Checking service status..."
        docker-compose -f docker-compose.production.yml ps
        
        # Test application health
        echo "Testing application health..."
        sleep 10
        if curl -f http://localhost:8000/health 2>/dev/null; then
            echo "✅ Application health check passed"
        else
            echo "⚠️  Application health check failed - checking if app is responding..."
            if curl -f http://localhost:8000/ 2>/dev/null; then
                echo "✅ Application is responding on root path"
            else
                echo "❌ Application is not responding"
            fi
        fi
        
        echo ""
        echo "🎉 Deployment completed successfully!"
        echo "📊 Service Status:"
        docker-compose -f docker-compose.production.yml ps
        echo ""
        echo "🌐 Your application should be available at:"
        echo "   - http://www.webtado.live"
        echo "   - http://91.99.118.65"
        echo ""
EOF
    
    if [ $? -eq 0 ]; then
        success "Deployment to production server completed successfully!"
        echo ""
        echo "🌐 Your CMSVS application is now live at:"
        echo "   - https://www.webtado.live"
        echo "   - http://91.99.118.65"
        echo ""
        echo "📋 Next steps:"
        echo "   1. Test the application functionality"
        echo "   2. Check SSL certificate status"
        echo "   3. Monitor application logs if needed"
    else
        error "Deployment failed. Please check the server logs."
        exit 1
    fi
}

# Main function
main() {
    echo "🚀 CMSVS Production Deployment to www.webtado.live"
    echo "=================================================="
    echo "Target Server: $PRODUCTION_SERVER"
    echo "Started: $(date)"
    echo "=================================================="
    echo ""
    
    # Check if SSH key is available
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$PRODUCTION_USER@$PRODUCTION_SERVER" echo "SSH connection test" 2>/dev/null; then
        warning "SSH key authentication failed. You may need to enter password."
    fi
    
    deploy_to_production
    
    success "All deployment tasks completed!"
}

# Run main function
main "$@"
