#!/bin/bash

# CMSVS Production Deployment Script
# Server: 91.99.118.65

set -e  # Exit on any error

echo "🚀 CMSVS Production Deployment Script"
echo "====================================="

# Configuration
SERVER_IP="91.99.118.65"
APP_NAME="cmsvs"
DEPLOY_USER="root"  # Change this to your server user
DEPLOY_PATH="/opt/cmsvs"
SSH_KEY="$HOME/.ssh/cmsvs_deploy_key_ed25519"  # SSH key for deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we can connect to the server
check_server_connection() {
    print_status "Checking server connection..."

    # Try Windows ping first, then Linux ping
    if ping -n 1 $SERVER_IP > /dev/null 2>&1 || ping -c 1 $SERVER_IP > /dev/null 2>&1; then
        print_success "Server is reachable"
    else
        print_error "Cannot reach server $SERVER_IP"
        print_error "Please check:"
        print_error "1. Server is online and accessible"
        print_error "2. No firewall blocking the connection"
        print_error "3. Correct IP address: $SERVER_IP"
        exit 1
    fi
}

# Prepare deployment files
prepare_deployment() {
    print_status "Preparing deployment files..."
    
    # Create deployment directory
    mkdir -p deployment
    
    # Copy necessary files
    cp -r app deployment/
    cp -r nginx deployment/
    cp docker-compose.production.yml deployment/
    cp .env.production deployment/
    cp Dockerfile deployment/
    cp requirements.txt deployment/
    cp init_db.py deployment/
    cp -r static deployment/ 2>/dev/null || true
    
    # Create deployment archive
    tar -czf cmsvs-deployment.tar.gz deployment/
    
    print_success "Deployment files prepared"
}

# Transfer files to server
transfer_files() {
    print_status "Transferring files to server..."

    # Create directory on server
    ssh -i "$SSH_KEY" $DEPLOY_USER@$SERVER_IP "mkdir -p $DEPLOY_PATH"

    # Transfer deployment archive
    scp -i "$SSH_KEY" cmsvs-deployment.tar.gz $DEPLOY_USER@$SERVER_IP:$DEPLOY_PATH/

    # Extract on server
    ssh -i "$SSH_KEY" $DEPLOY_USER@$SERVER_IP "cd $DEPLOY_PATH && tar -xzf cmsvs-deployment.tar.gz --strip-components=1"

    print_success "Files transferred successfully"
}

# Install Docker and Docker Compose on server
install_docker() {
    print_status "Installing Docker and Docker Compose on server..."

    ssh -i "$SSH_KEY" $DEPLOY_USER@$SERVER_IP << 'EOF'
        # Update system
        apt-get update
        
        # Install Docker
        if ! command -v docker &> /dev/null; then
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            systemctl enable docker
            systemctl start docker
        fi
        
        # Install Docker Compose
        if ! command -v docker-compose &> /dev/null; then
            curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
        fi
        
        # Verify installations
        docker --version
        docker-compose --version
EOF
    
    print_success "Docker and Docker Compose installed"
}

# Deploy application
deploy_application() {
    print_status "Deploying application on server..."

    ssh -i "$SSH_KEY" $DEPLOY_USER@$SERVER_IP << EOF
        cd $DEPLOY_PATH
        
        # Stop existing containers if any
        docker-compose -f docker-compose.production.yml down 2>/dev/null || true
        
        # Build and start services
        docker-compose -f docker-compose.production.yml build
        docker-compose -f docker-compose.production.yml up -d
        
        # Wait for services to start
        sleep 30
        
        # Initialize database
        docker-compose -f docker-compose.production.yml exec -T app python init_db.py
        
        # Check service status
        docker-compose -f docker-compose.production.yml ps
EOF
    
    print_success "Application deployed successfully"
}

# Configure firewall
configure_firewall() {
    print_status "Configuring firewall..."

    ssh -i "$SSH_KEY" $DEPLOY_USER@$SERVER_IP << 'EOF'
        # Install ufw if not present
        apt-get install -y ufw
        
        # Configure firewall rules
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
        
        # Allow SSH
        ufw allow 22/tcp
        
        # Allow HTTP and HTTPS
        ufw allow 80/tcp
        ufw allow 443/tcp
        
        # Enable firewall
        ufw --force enable
        
        # Show status
        ufw status
EOF
    
    print_success "Firewall configured"
}

# Main deployment function
main() {
    echo
    print_status "Starting production deployment to $SERVER_IP"
    echo
    
    # Check prerequisites
    if ! command -v ssh &> /dev/null; then
        print_error "SSH client not found. Please install SSH."
        exit 1
    fi
    
    if ! command -v scp &> /dev/null; then
        print_error "SCP not found. Please install SSH utilities."
        exit 1
    fi
    
    # Run deployment steps
    check_server_connection
    prepare_deployment
    
    print_warning "About to connect to server $SERVER_IP"
    print_warning "Make sure you have SSH access to the server"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        transfer_files
        install_docker
        deploy_application
        configure_firewall
        
        echo
        print_success "🎉 Deployment completed successfully!"
        print_success "Your application should be accessible at:"
        print_success "  HTTP:  http://$SERVER_IP"
        print_success "  HTTPS: https://$SERVER_IP (after SSL setup)"
        echo
        print_warning "Next steps:"
        print_warning "1. Configure SSL certificates"
        print_warning "2. Set up domain name (optional)"
        print_warning "3. Configure backup strategy"
        echo
    else
        print_warning "Deployment cancelled"
    fi
    
    # Cleanup
    rm -rf deployment cmsvs-deployment.tar.gz
}

# Run main function
main "$@"
