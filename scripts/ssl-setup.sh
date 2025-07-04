#!/bin/bash
# SSL Certificate Setup and Management Script for CMSVS Internal System
# Supports Let's Encrypt, self-signed certificates, and custom certificates

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="$PROJECT_ROOT/ssl"
NGINX_DIR="$PROJECT_ROOT/nginx"
DOMAIN="${1:-localhost}"
EMAIL="${2:-admin@example.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to show usage
show_usage() {
    echo "Usage: $0 <command> [domain] [email]"
    echo ""
    echo "Commands:"
    echo "  letsencrypt    Generate Let's Encrypt certificate"
    echo "  self-signed    Generate self-signed certificate"
    echo "  renew          Renew Let's Encrypt certificate"
    echo "  check          Check certificate validity"
    echo "  install        Install custom certificate"
    echo ""
    echo "Examples:"
    echo "  $0 letsencrypt example.com admin@example.com"
    echo "  $0 self-signed localhost"
    echo "  $0 renew"
    echo "  $0 check example.com"
}

# Function to create SSL directory structure
setup_ssl_directory() {
    log "Setting up SSL directory structure..."
    
    mkdir -p "$SSL_DIR"
    mkdir -p "$SSL_DIR/certs"
    mkdir -p "$SSL_DIR/private"
    mkdir -p "$SSL_DIR/csr"
    
    # Set proper permissions
    chmod 755 "$SSL_DIR"
    chmod 755 "$SSL_DIR/certs"
    chmod 700 "$SSL_DIR/private"
    chmod 755 "$SSL_DIR/csr"
    
    success "SSL directory structure created"
}

# Function to generate self-signed certificate
generate_self_signed() {
    local domain="$1"
    
    log "Generating self-signed certificate for $domain..."
    
    setup_ssl_directory
    
    # Generate private key
    openssl genrsa -out "$SSL_DIR/private/$domain.key" 2048
    chmod 600 "$SSL_DIR/private/$domain.key"
    
    # Generate certificate signing request
    openssl req -new -key "$SSL_DIR/private/$domain.key" \
        -out "$SSL_DIR/csr/$domain.csr" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$domain"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 \
        -in "$SSL_DIR/csr/$domain.csr" \
        -signkey "$SSL_DIR/private/$domain.key" \
        -out "$SSL_DIR/certs/$domain.crt"
    
    # Create combined certificate file
    cat "$SSL_DIR/certs/$domain.crt" > "$SSL_DIR/certs/server.crt"
    cp "$SSL_DIR/private/$domain.key" "$SSL_DIR/private/server.key"
    
    success "Self-signed certificate generated for $domain"
    log "Certificate: $SSL_DIR/certs/$domain.crt"
    log "Private key: $SSL_DIR/private/$domain.key"
    
    # Update Nginx configuration
    update_nginx_ssl_config "$domain"
}

# Function to generate Let's Encrypt certificate
generate_letsencrypt() {
    local domain="$1"
    local email="$2"
    
    log "Generating Let's Encrypt certificate for $domain..."
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        error "Certbot is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt install certbot"
        echo "  CentOS/RHEL: sudo yum install certbot"
        exit 1
    fi
    
    setup_ssl_directory
    
    # Stop Nginx if running to free port 80
    if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" ps nginx | grep -q "Up"; then
        log "Stopping Nginx temporarily..."
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" stop nginx
        NGINX_WAS_RUNNING=true
    fi
    
    # Generate certificate using standalone mode
    if certbot certonly --standalone \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        -d "$domain"; then
        
        # Copy certificates to our SSL directory
        cp "/etc/letsencrypt/live/$domain/fullchain.pem" "$SSL_DIR/certs/$domain.crt"
        cp "/etc/letsencrypt/live/$domain/privkey.pem" "$SSL_DIR/private/$domain.key"
        
        # Create server certificate links
        ln -sf "$SSL_DIR/certs/$domain.crt" "$SSL_DIR/certs/server.crt"
        ln -sf "$SSL_DIR/private/$domain.key" "$SSL_DIR/private/server.key"
        
        # Set proper permissions
        chmod 644 "$SSL_DIR/certs/$domain.crt"
        chmod 600 "$SSL_DIR/private/$domain.key"
        
        success "Let's Encrypt certificate generated for $domain"
        
        # Update Nginx configuration
        update_nginx_ssl_config "$domain"
        
        # Set up auto-renewal
        setup_auto_renewal "$domain" "$email"
        
    else
        error "Failed to generate Let's Encrypt certificate"
        exit 1
    fi
    
    # Restart Nginx if it was running
    if [ "$NGINX_WAS_RUNNING" = true ]; then
        log "Restarting Nginx..."
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" start nginx
    fi
}

# Function to renew Let's Encrypt certificate
renew_letsencrypt() {
    log "Renewing Let's Encrypt certificates..."
    
    if ! command -v certbot &> /dev/null; then
        error "Certbot is not installed"
        exit 1
    fi
    
    # Renew certificates
    if certbot renew --quiet; then
        success "Certificates renewed successfully"
        
        # Copy renewed certificates
        for cert_dir in /etc/letsencrypt/live/*/; do
            if [ -d "$cert_dir" ]; then
                domain=$(basename "$cert_dir")
                if [ -f "$cert_dir/fullchain.pem" ]; then
                    cp "$cert_dir/fullchain.pem" "$SSL_DIR/certs/$domain.crt"
                    cp "$cert_dir/privkey.pem" "$SSL_DIR/private/$domain.key"
                    log "Updated certificate for $domain"
                fi
            fi
        done
        
        # Reload Nginx
        if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" ps nginx | grep -q "Up"; then
            docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" exec nginx nginx -s reload
            log "Nginx configuration reloaded"
        fi
        
    else
        warning "Certificate renewal had issues, check certbot logs"
    fi
}

# Function to check certificate validity
check_certificate() {
    local domain="$1"
    
    log "Checking certificate for $domain..."
    
    if [ -f "$SSL_DIR/certs/$domain.crt" ]; then
        # Check local certificate
        local expiry_date=$(openssl x509 -in "$SSL_DIR/certs/$domain.crt" -noout -enddate | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ $days_until_expiry -gt 0 ]; then
            if [ $days_until_expiry -lt 30 ]; then
                warning "Certificate expires in $days_until_expiry days"
            else
                success "Certificate is valid for $days_until_expiry days"
            fi
        else
            error "Certificate has expired"
        fi
        
        # Show certificate details
        echo ""
        echo "Certificate Details:"
        openssl x509 -in "$SSL_DIR/certs/$domain.crt" -noout -subject -issuer -dates
        
    else
        error "Certificate file not found: $SSL_DIR/certs/$domain.crt"
    fi
    
    # Check remote certificate if domain is not localhost
    if [ "$domain" != "localhost" ] && command -v openssl &> /dev/null; then
        echo ""
        log "Checking remote certificate..."
        if timeout 10 openssl s_client -servername "$domain" -connect "$domain:443" </dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
            success "Remote certificate is accessible"
        else
            warning "Could not connect to remote certificate"
        fi
    fi
}

# Function to update Nginx SSL configuration
update_nginx_ssl_config() {
    local domain="$1"
    
    log "Updating Nginx SSL configuration for $domain..."
    
    # Update server_name in nginx.conf
    if [ -f "$NGINX_DIR/nginx.conf" ]; then
        sed -i.bak "s/server_name localhost;/server_name $domain;/" "$NGINX_DIR/nginx.conf"
        sed -i.bak "s|ssl_certificate /etc/ssl/certs/server.crt;|ssl_certificate /etc/ssl/certs/$domain.crt;|" "$NGINX_DIR/nginx.conf"
        sed -i.bak "s|ssl_certificate_key /etc/ssl/private/server.key;|ssl_certificate_key /etc/ssl/private/$domain.key;|" "$NGINX_DIR/nginx.conf"
        
        success "Nginx configuration updated"
    else
        warning "Nginx configuration file not found"
    fi
}

# Function to setup auto-renewal for Let's Encrypt
setup_auto_renewal() {
    local domain="$1"
    local email="$2"
    
    log "Setting up auto-renewal for Let's Encrypt certificates..."
    
    # Create renewal script
    cat > "$SCRIPT_DIR/ssl-renew.sh" << EOF
#!/bin/bash
# Auto-renewal script for Let's Encrypt certificates
cd "$PROJECT_ROOT"
"$SCRIPT_DIR/ssl-setup.sh" renew
EOF
    
    chmod +x "$SCRIPT_DIR/ssl-renew.sh"
    
    # Add to crontab (run twice daily)
    (crontab -l 2>/dev/null; echo "0 12,0 * * * $SCRIPT_DIR/ssl-renew.sh") | crontab -
    
    success "Auto-renewal configured (runs twice daily)"
}

# Function to install custom certificate
install_custom_certificate() {
    log "Installing custom certificate..."
    
    echo "Please provide the following files:"
    echo "1. Certificate file (.crt or .pem)"
    echo "2. Private key file (.key)"
    echo "3. (Optional) Certificate chain file"
    
    read -p "Certificate file path: " cert_file
    read -p "Private key file path: " key_file
    read -p "Certificate chain file path (optional): " chain_file
    read -p "Domain name: " domain
    
    if [ ! -f "$cert_file" ]; then
        error "Certificate file not found: $cert_file"
        exit 1
    fi
    
    if [ ! -f "$key_file" ]; then
        error "Private key file not found: $key_file"
        exit 1
    fi
    
    setup_ssl_directory
    
    # Copy certificate and key
    cp "$cert_file" "$SSL_DIR/certs/$domain.crt"
    cp "$key_file" "$SSL_DIR/private/$domain.key"
    
    # If chain file provided, append to certificate
    if [ -n "$chain_file" ] && [ -f "$chain_file" ]; then
        cat "$chain_file" >> "$SSL_DIR/certs/$domain.crt"
    fi
    
    # Create server certificate links
    ln -sf "$SSL_DIR/certs/$domain.crt" "$SSL_DIR/certs/server.crt"
    ln -sf "$SSL_DIR/private/$domain.key" "$SSL_DIR/private/server.key"
    
    # Set proper permissions
    chmod 644 "$SSL_DIR/certs/$domain.crt"
    chmod 600 "$SSL_DIR/private/$domain.key"
    
    success "Custom certificate installed for $domain"
    
    # Update Nginx configuration
    update_nginx_ssl_config "$domain"
}

# Main function
main() {
    local command="$1"
    
    case "$command" in
        "letsencrypt")
            if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
                error "Domain and email are required for Let's Encrypt"
                show_usage
                exit 1
            fi
            generate_letsencrypt "$DOMAIN" "$EMAIL"
            ;;
        "self-signed")
            generate_self_signed "$DOMAIN"
            ;;
        "renew")
            renew_letsencrypt
            ;;
        "check")
            check_certificate "$DOMAIN"
            ;;
        "install")
            install_custom_certificate
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Run main function
main "$@"
