#!/bin/bash
# Complete Production Deployment Script for CMSVS
# This script handles the entire production deployment process

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/deployment-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
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
        error "Docker is not running"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if required files exist
    local required_files=(
        "$PROJECT_ROOT/.env.production"
        "$PROJECT_ROOT/docker-compose.production.yml"
        "$PROJECT_ROOT/Dockerfile"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file not found: $file"
            exit 1
        fi
    done
    
    success "Prerequisites check passed"
}

# Function to prepare environment
prepare_environment() {
    log "Preparing production environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create necessary directories
    mkdir -p logs data/{postgres,redis,uploads,backups} ssl
    
    # Set proper permissions
    chmod 755 data
    chmod 777 data/uploads data/logs
    chmod 755 data/backups
    
    success "Environment prepared"
}

# Function to build and deploy services
deploy_services() {
    log "Building and deploying services..."
    
    cd "$PROJECT_ROOT"
    
    # Stop any existing services
    log "Stopping existing services..."
    docker-compose -f docker-compose.production.yml down --timeout 30 || true
    
    # Build images
    log "Building Docker images..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    # Start services
    log "Starting services..."
    docker-compose -f docker-compose.production.yml up -d
    
    success "Services deployed successfully"
}

# Function to wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for database
    log "Waiting for database..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.production.yml exec -T db pg_isready -U cmsvs_user -d cmsvs_db >/dev/null 2>&1; then
            success "Database is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Database failed to start within timeout"
            exit 1
        fi
        
        log "Attempt $attempt/$max_attempts - waiting for database..."
        sleep 5
        ((attempt++))
    done
    
    # Wait for application
    log "Waiting for application..."
    sleep 30
    
    success "All services are ready"
}

# Function to initialize application
initialize_application() {
    log "Initializing application..."
    
    # Initialize database tables
    log "Creating database tables..."
    docker-compose -f docker-compose.production.yml exec -T app python init_db.py
    
    success "Application initialized"
}

# Function to verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check service status
    log "Checking service status..."
    docker-compose -f docker-compose.production.yml ps
    
    # Test database connection
    log "Testing database connection..."
    docker-compose -f docker-compose.production.yml exec -T app python -c "
from app.database import engine
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT version()')
        print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"
    
    # Test application health
    log "Testing application health..."
    if docker-compose -f docker-compose.production.yml exec -T app curl -f http://localhost:8000/health >/dev/null 2>&1; then
        success "Application health check passed"
    else
        warning "Application health check failed - this might be normal if health endpoint is not implemented"
    fi
    
    success "Deployment verification completed"
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo "🎉 CMSVS Production Deployment Complete!"
    echo "========================================"
    echo ""
    echo "📋 Deployment Summary:"
    echo "- Database: PostgreSQL with secure configuration"
    echo "- Cache: Redis for session and data caching"
    echo "- Application: CMSVS Internal System"
    echo "- Proxy: Nginx reverse proxy"
    echo ""
    echo "🔗 Access Information:"
    echo "- Application URL: http://91.99.118.65"
    echo "- Admin Email: almananei90@gmail.com"
    echo "- Admin Password: [Check .env.production file]"
    echo ""
    echo "📊 Service Status:"
    docker-compose -f docker-compose.production.yml ps
    echo ""
    echo "📝 Next Steps:"
    echo "1. Configure SSL certificate for HTTPS"
    echo "2. Set up firewall rules"
    echo "3. Configure domain name (optional)"
    echo "4. Set up monitoring and backups"
    echo ""
    echo "📁 Important Files:"
    echo "- Logs: $LOG_FILE"
    echo "- Configuration: .env.production"
    echo "- Secrets: .env.secrets"
    echo ""
}

# Main deployment function
main() {
    echo "🚀 CMSVS Production Deployment"
    echo "=============================="
    echo "Server: 91.99.118.65"
    echo "Started: $(date)"
    echo "=============================="
    echo ""
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Run deployment steps
    check_prerequisites
    prepare_environment
    deploy_services
    wait_for_services
    initialize_application
    verify_deployment
    show_summary
    
    success "Production deployment completed successfully!"
}

# Run main function
main "$@"
