#!/bin/bash

# CMSVS Production Deployment Script
# This script helps you deploy changes to production safely

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION_SERVER="91.99.118.65"
SSH_KEY="$HOME/.ssh/cmsvs_deploy_key_ed25519"
DEPLOY_PATH="/opt/cmsvs"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're on the main branch
check_branch() {
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        print_error "You must be on the 'main' branch to deploy to production"
        print_status "Current branch: $current_branch"
        print_status "Switch to main branch: git checkout main"
        exit 1
    fi
}

# Check if there are uncommitted changes
check_uncommitted_changes() {
    if ! git diff-index --quiet HEAD --; then
        print_error "You have uncommitted changes. Please commit or stash them first."
        git status --short
        exit 1
    fi
}

# Push changes to GitHub
push_changes() {
    print_status "Pushing changes to GitHub..."
    git push origin main
    print_success "Changes pushed to GitHub"
}

# Create backup of current production
create_backup() {
    print_status "Creating backup of current production..."
    ssh -i "$SSH_KEY" root@$PRODUCTION_SERVER "
        cd $DEPLOY_PATH
        timestamp=\$(date +%Y%m%d_%H%M%S)
        cp .env.production .env.production.backup.\$timestamp
        echo 'Backup created: .env.production.backup.'\$timestamp
    "
    print_success "Backup created"
}

# Deploy to production
deploy_to_production() {
    print_status "Deploying to production server..."
    
    ssh -i "$SSH_KEY" root@$PRODUCTION_SERVER "
        cd $DEPLOY_PATH
        
        echo '🔄 Pulling latest changes...'
        git pull origin main
        
        echo '🛑 Stopping services...'
        docker-compose -f docker-compose.production.yml down
        
        echo '🔨 Building application...'
        docker-compose -f docker-compose.production.yml build --no-cache app
        
        echo '🚀 Starting services...'
        docker-compose -f docker-compose.production.yml up -d
        
        echo '⏳ Waiting for services to be healthy...'
        sleep 30
        
        echo '✅ Checking service status...'
        docker-compose -f docker-compose.production.yml ps
    "
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check if application is responding
    response=$(ssh -i "$SSH_KEY" root@$PRODUCTION_SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/login")
    
    if [ "$response" = "200" ]; then
        print_success "✅ Application is responding correctly (HTTP $response)"
    else
        print_error "❌ Application is not responding correctly (HTTP $response)"
        print_status "Checking application logs..."
        ssh -i "$SSH_KEY" root@$PRODUCTION_SERVER "cd $DEPLOY_PATH && docker-compose -f docker-compose.production.yml logs --tail=20 app"
        exit 1
    fi
}

# Main deployment process
main() {
    echo "🚀 CMSVS Production Deployment"
    echo "=============================="
    
    # Pre-deployment checks
    print_status "Running pre-deployment checks..."
    check_branch
    check_uncommitted_changes
    
    # Confirm deployment
    echo ""
    print_warning "You are about to deploy to PRODUCTION server ($PRODUCTION_SERVER)"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
    
    # Deployment steps
    echo ""
    print_status "Starting deployment process..."
    
    push_changes
    create_backup
    deploy_to_production
    verify_deployment
    
    echo ""
    print_success "🎉 Deployment completed successfully!"
    print_status "Your application is now live at: http://$PRODUCTION_SERVER"
    
    echo ""
    print_status "Post-deployment checklist:"
    echo "  ✅ Test login functionality"
    echo "  ✅ Check all main features"
    echo "  ✅ Monitor application logs for any issues"
    echo ""
    print_status "To monitor logs: ssh -i $SSH_KEY root@$PRODUCTION_SERVER 'cd $DEPLOY_PATH && docker-compose -f docker-compose.production.yml logs -f app'"
}

# Run main function
main "$@"
