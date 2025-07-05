#!/bin/bash
# Production Environment Setup Script for CMSVS
# Sets up secure PostgreSQL and application environment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Function to generate secure passwords
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to generate secret key
generate_secret_key() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-50
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "openssl" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to create secure environment file
create_production_env() {
    log "Creating secure production environment..."
    
    local env_file="$PROJECT_ROOT/.env.production"
    local env_secrets="$PROJECT_ROOT/.env.secrets"
    
    # Generate secure passwords
    local postgres_password=$(generate_password)
    local postgres_readonly_password=$(generate_password)
    local redis_password=$(generate_password)
    local secret_key=$(generate_secret_key)
    local admin_password=$(generate_password)
    
    # Create secrets file (not committed to git)
    cat > "$env_secrets" <<EOF
# CMSVS Production Secrets - DO NOT COMMIT TO GIT
# Generated on $(date)

# Database Passwords
POSTGRES_PASSWORD=$postgres_password
POSTGRES_READONLY_PASSWORD=$postgres_readonly_password

# Redis Password
REDIS_PASSWORD=$redis_password

# Application Secrets
SECRET_KEY=$secret_key
ADMIN_PASSWORD=$admin_password

# Email Password (update with your actual SMTP password)
SMTP_PASSWORD=CHANGE_THIS_EMAIL_PASSWORD
EOF

    # Update .env.production with generated values
    if [[ -f "$env_file" ]]; then
        # Backup existing file
        cp "$env_file" "$env_file.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update critical values
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" "$env_file"
        sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$admin_password/" "$env_file"
        sed -i "s/DATABASE_URL=postgresql:\/\/cmsvs_user:admin@/DATABASE_URL=postgresql:\/\/cmsvs_user:$postgres_password@/" "$env_file"
    fi
    
    # Set proper permissions
    chmod 600 "$env_secrets"
    chmod 600 "$env_file"
    
    success "Production environment created"
    warning "Secrets saved to: $env_secrets"
    warning "Keep this file secure and do not commit to git!"
    
    # Display credentials for manual setup
    echo ""
    echo "🔐 Generated Credentials:"
    echo "========================"
    echo "Database Password: $postgres_password"
    echo "Redis Password: $redis_password"
    echo "Admin Password: $admin_password"
    echo "Secret Key: $secret_key"
    echo ""
    echo "⚠️  Save these credentials securely!"
}

# Function to setup directories
setup_directories() {
    log "Setting up directory structure..."
    
    cd "$PROJECT_ROOT"
    
    # Create data directories
    mkdir -p data/{postgres,redis,uploads,logs,backups}
    mkdir -p ssl
    mkdir -p secrets
    
    # Set proper permissions
    chmod 755 data
    chmod 700 secrets
    chmod 755 ssl
    chmod 777 data/uploads
    chmod 777 data/logs
    chmod 755 data/backups
    
    success "Directory structure created"
}

# Function to test database connection
test_database() {
    log "Testing database connection..."
    
    # Source the secrets
    if [[ -f "$PROJECT_ROOT/.env.secrets" ]]; then
        source "$PROJECT_ROOT/.env.secrets"
    fi
    
    # Run the database test script
    cd "$PROJECT_ROOT"
    python scripts/test-db-connection.py
}

# Function to setup SSL certificates (self-signed for testing)
setup_ssl() {
    log "Setting up SSL certificates..."
    
    local ssl_dir="$PROJECT_ROOT/ssl"
    
    if [[ ! -f "$ssl_dir/server.crt" ]]; then
        # Generate self-signed certificate for testing
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/server.key" \
            -out "$ssl_dir/server.crt" \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=91.99.118.65"
        
        chmod 600 "$ssl_dir/server.key"
        chmod 644 "$ssl_dir/server.crt"
        
        success "Self-signed SSL certificate created"
        warning "For production, replace with a valid SSL certificate"
    else
        log "SSL certificate already exists"
    fi
}

# Function to initialize database
init_database() {
    log "Initializing database..."
    
    cd "$PROJECT_ROOT"
    
    # Start only the database service first
    docker-compose -f docker-compose.production.yml up -d db
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 30
    
    # Run database initialization
    docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "SELECT version();"
    
    success "Database initialized"
}

# Main function
main() {
    echo "🚀 CMSVS Production Environment Setup"
    echo "====================================="
    echo ""
    
    check_prerequisites
    setup_directories
    create_production_env
    setup_ssl
    
    echo ""
    echo "✅ Production environment setup completed!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Review and update .env.production with your specific settings"
    echo "2. Update SSL certificates with valid ones for your domain"
    echo "3. Configure your firewall to allow only necessary ports"
    echo "4. Run: docker-compose -f docker-compose.production.yml up -d"
    echo "5. Test the deployment with: python scripts/test-db-connection.py"
    echo ""
    echo "🔒 Security Reminders:"
    echo "- Keep .env.secrets file secure and never commit to git"
    echo "- Change default passwords after first login"
    echo "- Regularly update and patch your system"
    echo "- Monitor logs for suspicious activity"
    echo ""
}

# Run main function
main "$@"
