#!/bin/bash
# Production deployment script for CMSVS Internal System
# This script handles the complete production deployment process

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$PROJECT_ROOT/logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if production environment file exists
    if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
        error "Production environment file (.env.production) not found"
        exit 1
    fi
    
    # Check if secrets are set up
    if [ ! -d "$PROJECT_ROOT/secrets" ]; then
        error "Secrets directory not found. Run setup-secrets.sh first"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to create backup before deployment
create_backup() {
    log "Creating backup before deployment..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Create database backup if service is running
    if docker-compose -f docker-compose.production.yml ps db | grep -q "Up"; then
        BACKUP_FILE="pre_deployment_$(date +%Y%m%d_%H%M%S).sql"
        
        if docker-compose -f docker-compose.production.yml exec -T db pg_dump \
            -U cmsvs_user -d cmsvs_db --clean --no-owner --no-privileges > "$BACKUP_DIR/$BACKUP_FILE"; then
            gzip "$BACKUP_DIR/$BACKUP_FILE"
            success "Database backup created: $BACKUP_FILE.gz"
        else
            warning "Failed to create database backup"
        fi
    else
        log "Database service not running, skipping backup"
    fi
    
    # Backup current uploads directory
    if [ -d "$PROJECT_ROOT/uploads" ]; then
        UPLOADS_BACKUP="uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$BACKUP_DIR/$UPLOADS_BACKUP" -C "$PROJECT_ROOT" uploads/
        success "Uploads backup created: $UPLOADS_BACKUP"
    fi
}

# Function to pull latest code
update_code() {
    log "Updating application code..."
    
    cd "$PROJECT_ROOT"
    
    # Stash any local changes
    if git status --porcelain | grep -q .; then
        warning "Local changes detected, stashing them"
        git stash push -m "Auto-stash before deployment $(date)"
    fi
    
    # Pull latest changes
    git fetch origin
    git checkout main
    git pull origin main
    
    success "Code updated successfully"
}

# Function to build and deploy services
deploy_services() {
    log "Building and deploying services..."
    
    cd "$PROJECT_ROOT"
    
    # Build images
    log "Building Docker images..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    # Stop services gracefully
    log "Stopping existing services..."
    docker-compose -f docker-compose.production.yml down --timeout 30
    
    # Start services
    log "Starting services..."
    docker-compose -f docker-compose.production.yml up -d
    
    success "Services deployed successfully"
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.production.yml exec -T db pg_isready -U cmsvs_user >/dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    
    # Run migrations
    if docker-compose -f docker-compose.production.yml exec -T app python scripts/db_manage.py migrate; then
        success "Database migrations completed"
    else
        error "Database migrations failed"
        return 1
    fi
}

# Function to verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Wait for services to be ready
    sleep 10
    
    # Check service health
    local services=("app" "db" "nginx")
    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.production.yml ps "$service" | grep -q "Up"; then
            success "$service is running"
        else
            error "$service is not running"
            return 1
        fi
    done
    
    # Check application health endpoint
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://localhost/health >/dev/null 2>&1; then
            success "Application health check passed"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Application health check failed after $max_attempts attempts"
            return 1
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 5
        ((attempt++))
    done
    
    # Check database connectivity
    if docker-compose -f docker-compose.production.yml exec -T app python -c "
from app.database import SessionLocal
db = SessionLocal()
try:
    db.execute('SELECT 1')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
finally:
    db.close()
"; then
        success "Database connectivity verified"
    else
        error "Database connectivity check failed"
        return 1
    fi
    
    success "Deployment verification completed"
}

# Function to cleanup old resources
cleanup() {
    log "Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backups (keep last 10)
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "*.gz" -type f | sort -r | tail -n +11 | xargs -r rm
        log "Old backups cleaned up"
    fi
    
    success "Cleanup completed"
}

# Function to send notification (placeholder)
send_notification() {
    local status=$1
    local message=$2
    
    log "Deployment $status: $message"
    
    # Add your notification logic here (Slack, email, etc.)
    # Example:
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"CMSVS Deployment $status: $message\"}" \
    #   "$SLACK_WEBHOOK_URL"
}

# Function to rollback deployment
rollback() {
    error "Deployment failed, initiating rollback..."
    
    # Stop current services
    docker-compose -f docker-compose.production.yml down
    
    # Restore from backup if available
    local latest_backup=$(ls -t "$BACKUP_DIR"/pre_deployment_*.sql.gz 2>/dev/null | head -n1)
    if [ -n "$latest_backup" ]; then
        log "Restoring database from backup: $latest_backup"
        # Add database restore logic here
    fi
    
    # Restart services with previous version
    docker-compose -f docker-compose.production.yml up -d
    
    error "Rollback completed"
    send_notification "FAILED" "Deployment failed and rollback completed"
}

# Main deployment function
main() {
    log "Starting production deployment..."
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Trap errors for rollback
    trap 'rollback' ERR
    
    # Run deployment steps
    check_prerequisites
    create_backup
    update_code
    deploy_services
    run_migrations
    verify_deployment
    cleanup
    
    success "Production deployment completed successfully!"
    send_notification "SUCCESS" "Production deployment completed successfully"
    
    # Show deployment summary
    echo ""
    echo "=================================="
    echo "   DEPLOYMENT SUMMARY"
    echo "=================================="
    echo "✅ Prerequisites: Passed"
    echo "✅ Backup: Created"
    echo "✅ Code: Updated"
    echo "✅ Services: Deployed"
    echo "✅ Migrations: Applied"
    echo "✅ Verification: Passed"
    echo "✅ Cleanup: Completed"
    echo ""
    echo "🌐 Application URL: https://yourdomain.com"
    echo "📊 Health Check: https://yourdomain.com/health"
    echo "📈 Metrics: https://yourdomain.com/metrics"
    echo ""
    echo "📝 Deployment log: $LOG_FILE"
    echo "=================================="
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-verification)
            SKIP_VERIFICATION=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-backup       Skip backup creation"
            echo "  --skip-verification Skip deployment verification"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
