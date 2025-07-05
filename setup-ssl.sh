#!/bin/bash

# SSL Certificate Setup Script for CMSVS
# This script sets up SSL certificates using Let's Encrypt

set -e

echo "🔒 CMSVS SSL Certificate Setup"
echo "=============================="

# Configuration
DOMAIN=""
EMAIL=""
DEPLOY_PATH="/opt/cmsvs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Get domain and email from user
get_ssl_info() {
    echo
    print_status "SSL Certificate Configuration"
    echo
    
    read -p "Enter your domain name (e.g., cmsvs.yourdomain.com): " DOMAIN
    read -p "Enter your email address for Let's Encrypt: " EMAIL
    
    if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
        print_error "Domain and email are required"
        exit 1
    fi
    
    print_status "Domain: $DOMAIN"
    print_status "Email: $EMAIL"
}

# Install Certbot
install_certbot() {
    print_status "Installing Certbot..."
    
    # Update package list
    apt-get update
    
    # Install snapd if not present
    if ! command -v snap &> /dev/null; then
        apt-get install -y snapd
        systemctl enable snapd
        systemctl start snapd
    fi
    
    # Install certbot via snap
    snap install core; snap refresh core
    snap install --classic certbot
    
    # Create symlink
    ln -sf /snap/bin/certbot /usr/bin/certbot
    
    print_success "Certbot installed"
}

# Stop nginx temporarily
stop_nginx() {
    print_status "Stopping Nginx temporarily..."
    cd $DEPLOY_PATH
    docker-compose -f docker-compose.production.yml stop nginx
}

# Obtain SSL certificate
obtain_certificate() {
    print_status "Obtaining SSL certificate..."
    
    # Use certbot standalone mode
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email $EMAIL \
        -d $DOMAIN
    
    print_success "SSL certificate obtained"
}

# Create SSL-enabled Nginx configuration
create_ssl_config() {
    print_status "Creating SSL-enabled Nginx configuration..."
    
    # Create SSL directory in nginx config
    mkdir -p $DEPLOY_PATH/nginx/ssl
    
    # Copy certificates to nginx directory
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $DEPLOY_PATH/nginx/ssl/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $DEPLOY_PATH/nginx/ssl/
    
    # Create SSL-enabled nginx config
    cat > $DEPLOY_PATH/nginx/conf.d/app.conf << EOF
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client max body size for file uploads
    client_max_body_size 50M;

    # Timeout settings
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # Serve static files directly
    location /static/ {
        proxy_pass http://app:8000/static/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        expires 1h;
        add_header Cache-Control "public";
        access_log off;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://app:8000/health;
        access_log off;
    }

    # Main application
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
}
EOF
    
    print_success "SSL configuration created"
}

# Update environment for HTTPS
update_environment() {
    print_status "Updating environment for HTTPS..."
    
    # Update .env.production file
    sed -i 's/FORCE_HTTPS=True/FORCE_HTTPS=True/' $DEPLOY_PATH/.env.production
    sed -i 's/SECURE_COOKIES=False/SECURE_COOKIES=True/' $DEPLOY_PATH/.env.production
    sed -i "s/ALLOWED_HOSTS=91.99.118.65/ALLOWED_HOSTS=91.99.118.65,$DOMAIN/" $DEPLOY_PATH/.env.production
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN|" $DEPLOY_PATH/.env.production
    
    print_success "Environment updated for HTTPS"
}

# Restart services with SSL
restart_with_ssl() {
    print_status "Restarting services with SSL..."
    
    cd $DEPLOY_PATH
    
    # Rebuild nginx with new config
    docker-compose -f docker-compose.production.yml build nginx
    
    # Restart all services
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services
    sleep 30
    
    # Check status
    docker-compose -f docker-compose.production.yml ps
    
    print_success "Services restarted with SSL"
}

# Setup certificate renewal
setup_renewal() {
    print_status "Setting up certificate auto-renewal..."
    
    # Create renewal script
    cat > /etc/cron.d/certbot-renewal << EOF
# Renew Let's Encrypt certificates
0 12 * * * root certbot renew --quiet --deploy-hook "cd $DEPLOY_PATH && docker-compose -f docker-compose.production.yml restart nginx"
EOF
    
    print_success "Auto-renewal configured"
}

# Main function
main() {
    echo
    print_warning "This script will set up SSL certificates for your CMSVS application"
    print_warning "Make sure your domain is pointing to this server's IP address"
    echo
    
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        get_ssl_info
        install_certbot
        stop_nginx
        obtain_certificate
        create_ssl_config
        update_environment
        restart_with_ssl
        setup_renewal
        
        echo
        print_success "🎉 SSL setup completed successfully!"
        print_success "Your application is now accessible at:"
        print_success "  HTTPS: https://$DOMAIN"
        echo
        print_warning "Certificate will auto-renew every 12 hours"
        echo
    else
        print_warning "SSL setup cancelled"
    fi
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Run main function
main "$@"
