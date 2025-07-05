#!/bin/bash

# CMSVS Development Environment Setup Script
# This script helps you set up your local development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Set up Git branches
setup_git_branches() {
    print_status "Setting up Git branches..."
    
    # Check if development branch exists
    if git show-ref --verify --quiet refs/heads/development; then
        print_status "Development branch already exists"
    else
        print_status "Creating development branch..."
        git checkout -b development
        git push -u origin development
        print_success "Development branch created and pushed to GitHub"
    fi
    
    # Switch to development branch
    git checkout development
    print_success "Switched to development branch"
}

# Set up development environment
setup_development_env() {
    print_status "Setting up development environment..."
    
    # Create necessary directories
    mkdir -p uploads logs backups db_backups
    
    # Set permissions (if on Linux/Mac)
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        chmod 755 uploads logs backups db_backups
    fi
    
    print_success "Development directories created"
}

# Start development environment
start_development() {
    print_status "Starting development environment..."
    
    # Stop any existing containers
    docker-compose -f docker-compose.development.yml down 2>/dev/null || true
    
    # Start development environment
    docker-compose -f docker-compose.development.yml up -d
    
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check if services are healthy
    print_status "Checking service status..."
    docker-compose -f docker-compose.development.yml ps
}

# Initialize development database
init_development_db() {
    print_status "Initializing development database..."
    
    # Wait a bit more for database to be ready
    sleep 10
    
    # Initialize database
    docker-compose -f docker-compose.development.yml exec -T app python init_db.py
    
    print_success "Development database initialized"
}

# Verify development setup
verify_development() {
    print_status "Verifying development setup..."
    
    # Check if application is responding
    response=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/login 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        print_success "✅ Development application is running correctly"
    else
        print_warning "⚠️  Application might still be starting up (HTTP $response)"
        print_status "Checking application logs..."
        docker-compose -f docker-compose.development.yml logs --tail=10 app
    fi
}

# Main setup process
main() {
    echo "🛠️  CMSVS Development Environment Setup"
    echo "======================================"
    
    print_status "Setting up your development environment..."
    
    # Setup steps
    check_docker
    setup_git_branches
    setup_development_env
    start_development
    init_development_db
    verify_development
    
    echo ""
    print_success "🎉 Development environment setup completed!"
    echo ""
    print_status "Your development environment is ready:"
    echo "  🌐 Application URL: http://localhost:8000"
    echo "  📊 Database: PostgreSQL on localhost:5432"
    echo "  🔄 Redis: localhost:6379"
    echo ""
    print_status "Development credentials:"
    echo "  👤 Username: admin"
    echo "  📧 Email: almananei90@gmail.com"
    echo "  🔑 Password: admin123"
    echo ""
    print_status "Useful commands:"
    echo "  📋 View logs: docker-compose -f docker-compose.development.yml logs -f app"
    echo "  🛑 Stop dev env: docker-compose -f docker-compose.development.yml down"
    echo "  🚀 Deploy to prod: ./deploy.sh"
    echo ""
    print_warning "Remember: Always test your changes locally before deploying to production!"
}

# Run main function
main "$@"
