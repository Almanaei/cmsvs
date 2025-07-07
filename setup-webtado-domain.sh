#!/bin/bash

# Setup script for www.webtado.live domain
# This script configures the server to host CMSVS on the new domain

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="www.webtado.live"
ALT_DOMAIN="webtado.live"
EMAIL="almananei90@gmail.com"  # For Let's Encrypt
SERVER_IP="91.99.118.65"

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

# Check if domain resolves to our server
check_dns() {
    print_status "Checking DNS resolution for $DOMAIN..."
    
    # Check if domain resolves to our IP
    resolved_ip=$(dig +short $DOMAIN | tail -n1)
    
    if [ "$resolved_ip" = "$SERVER_IP" ]; then
        print_success "✅ $DOMAIN resolves to $SERVER_IP"
        return 0
    else
        print_warning "⚠️  $DOMAIN resolves to: $resolved_ip (expected: $SERVER_IP)"
        print_warning "DNS may still be propagating. You can continue, but SSL setup might fail."
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Please update your DNS records and try again."
            exit 1
        fi
    fi
}

# Install Certbot if not present
install_certbot() {
    print_status "Installing Certbot for SSL certificates..."
    
    # Update package list
    apt-get update
    
    # Install Certbot and Nginx plugin
    apt-get install -y certbot python3-certbot-nginx
    
    print_success "Certbot installed successfully"
}

# Setup SSL certificate
setup_ssl() {
    print_status "Setting up SSL certificate for $DOMAIN..."
    
    # Stop nginx temporarily
    systemctl stop nginx || docker-compose -f docker-compose.production.yml stop nginx
    
    # Get SSL certificate
    certbot certonly \
        --standalone \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        --domains $DOMAIN,$ALT_DOMAIN
    
    if [ $? -eq 0 ]; then
        print_success "✅ SSL certificate obtained successfully"
    else
        print_error "❌ Failed to obtain SSL certificate"
        print_status "This might be due to DNS not being fully propagated yet."
        print_status "You can try again later with: certbot certonly --standalone -d $DOMAIN -d $ALT_DOMAIN"
        return 1
    fi
}

# Update Nginx configuration
update_nginx_config() {
    print_status "Updating Nginx configuration..."
    
    # Copy the new configuration
    cp nginx/conf.d/webtado.conf /opt/cmsvs/nginx/conf.d/
    
    # Create temporary config without SSL for initial setup
    cat > /opt/cmsvs/nginx/conf.d/webtado-temp.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name webtado.live www.webtado.live;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    
    print_success "Nginx configuration updated"
}

# Update application configuration
update_app_config() {
    print_status "Updating application configuration..."
    
    # Backup current .env.production
    cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
    
    # Update domain settings in .env.production
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=localhost,127.0.0.1,91.99.118.65,webtado.live,www.webtado.live|g" .env.production
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://www.webtado.live,https://webtado.live|g" .env.production
    sed -i "s|APP_NAME=.*|APP_NAME=CMSVS - www.webtado.live|g" .env.production
    
    # Ensure HTTPS is forced
    sed -i "s|FORCE_HTTPS=.*|FORCE_HTTPS=True|g" .env.production
    sed -i "s|SECURE_COOKIES=.*|SECURE_COOKIES=True|g" .env.production
    
    print_success "Application configuration updated"
}

# Deploy with new configuration
deploy_application() {
    print_status "Deploying application with new domain configuration..."
    
    # Stop current services
    docker-compose -f docker-compose.production.yml down
    
    # Rebuild with new configuration
    docker-compose -f docker-compose.production.yml build --no-cache nginx
    
    # Start services
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services to be ready
    sleep 30
    
    print_success "Application deployed successfully"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test HTTP access
    http_status=$(curl -s -o /dev/null -w '%{http_code}' http://$DOMAIN/ || echo "000")
    
    if [ "$http_status" = "200" ] || [ "$http_status" = "301" ] || [ "$http_status" = "302" ]; then
        print_success "✅ HTTP access working (Status: $http_status)"
    else
        print_warning "⚠️  HTTP access issue (Status: $http_status)"
    fi
    
    # Test HTTPS access (if SSL is set up)
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        https_status=$(curl -s -o /dev/null -w '%{http_code}' https://$DOMAIN/ || echo "000")
        
        if [ "$https_status" = "200" ]; then
            print_success "✅ HTTPS access working (Status: $https_status)"
        else
            print_warning "⚠️  HTTPS access issue (Status: $https_status)"
        fi
    fi
}

# Main setup process
main() {
    echo "🌐 Setting up www.webtado.live for CMSVS"
    echo "======================================"
    
    print_status "This script will:"
    echo "  1. Check DNS configuration"
    echo "  2. Install SSL certificate tools"
    echo "  3. Set up SSL certificate"
    echo "  4. Update Nginx configuration"
    echo "  5. Update application settings"
    echo "  6. Deploy the application"
    echo "  7. Test the deployment"
    echo ""
    
    read -p "Continue with setup? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setup cancelled"
        exit 0
    fi
    
    # Run setup steps
    check_dns
    install_certbot
    update_nginx_config
    update_app_config
    deploy_application
    
    # Try to set up SSL (may fail if DNS not ready)
    if setup_ssl; then
        # If SSL setup succeeded, update to full config
        cp nginx/conf.d/webtado.conf /opt/cmsvs/nginx/conf.d/
        docker-compose -f docker-compose.production.yml restart nginx
        sleep 10
    fi
    
    test_deployment
    
    echo ""
    print_success "🎉 Domain setup completed!"
    echo ""
    print_status "Your website should now be accessible at:"
    echo "  🌐 http://www.webtado.live"
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        echo "  🔒 https://www.webtado.live"
    fi
    echo ""
    print_status "Next steps:"
    echo "  1. Test your website in a browser"
    echo "  2. If SSL setup failed, run: certbot certonly --standalone -d $DOMAIN -d $ALT_DOMAIN"
    echo "  3. Update any hardcoded URLs in your application"
    echo ""
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Run main function
main "$@"
