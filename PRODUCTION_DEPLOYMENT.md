# CMSVS Internal System - Production Deployment Guide

This guide provides comprehensive instructions for deploying the CMSVS Internal System to production.

## 🚀 Quick Start

For a quick production deployment, run:

```bash
# Make deployment script executable
chmod +x deploy.py

# Run automated deployment
python deploy.py --domain yourdomain.com --admin-email admin@yourdomain.com
```

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 20GB free space
- **CPU**: 2+ cores recommended

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Git
- OpenSSL (for SSL certificates)

### Installation Commands (Ubuntu)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
```

## 🔧 Manual Production Setup

### Step 1: Clone and Prepare Repository
```bash
# Clone repository
git clone <your-repository-url>
cd cmsvs

# Make scripts executable
chmod +x scripts/*.sh
chmod +x deploy.py
```

### Step 2: Configure Environment
```bash
# Copy production environment template
cp .env.production .env.production.local

# Edit production configuration
nano .env.production.local
```

**Critical settings to update:**
- `SECRET_KEY`: Generate a strong secret key
- `DATABASE_URL`: Update with production database credentials
- `ADMIN_EMAIL`: Set your admin email
- `ADMIN_PASSWORD`: Set a strong admin password
- `ALLOWED_HOSTS`: Set your domain name
- `CORS_ORIGINS`: Set your domain URLs

### Step 3: Generate Secrets
```bash
# Generate secure secrets for Docker
./scripts/setup-secrets.sh
```

### Step 4: SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/yourdomain.com.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/yourdomain.com.key
sudo chown -R $USER:$USER ssl/
```

#### Option B: Self-Signed Certificate (Development)
```bash
# Generate self-signed certificate
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/yourdomain.com.key \
    -out ssl/yourdomain.com.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### Step 5: Configure Nginx
```bash
# Create Nginx configuration directory
mkdir -p nginx/conf.d

# The deploy.py script will generate nginx.conf
# Or manually create it based on the template in nginx/nginx.conf
```

### Step 6: Deploy Application
```bash
# Build and start services
docker-compose -f docker-compose.production.yml up -d

# Check service status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### Step 7: Initialize Database
```bash
# Run database migrations
docker-compose -f docker-compose.production.yml exec app python -c "
from app.database import create_tables
create_tables()
print('Database initialized successfully')
"

# Verify admin user creation
docker-compose -f docker-compose.production.yml exec app python -c "
from app.database import SessionLocal
from app.services.user_service import UserService
from app.config import settings
db = SessionLocal()
admin = UserService.get_user_by_email(db, settings.admin_email)
print(f'Admin user: {admin.username if admin else \"Not found\"}')
db.close()
"
```

## 🔒 Security Configuration

### Firewall Setup
```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Block direct database access
sudo ufw deny 8000/tcp  # Block direct app access
```

### SSL Certificate Auto-Renewal
```bash
# Add crontab entry for certificate renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Security Headers Verification
```bash
# Test security headers
curl -I https://yourdomain.com
```

## 📊 Monitoring and Maintenance

### Health Checks
```bash
# Check application health
curl https://yourdomain.com/health

# Check database health
curl https://yourdomain.com/health/database

# Check all services
docker-compose -f docker-compose.production.yml ps
```

### Log Management
```bash
# View application logs
docker-compose -f docker-compose.production.yml logs app

# View Nginx logs
docker-compose -f docker-compose.production.yml logs nginx

# View database logs
docker-compose -f docker-compose.production.yml logs db
```

### Backup Management
```bash
# Manual backup
docker-compose -f docker-compose.production.yml exec backup /backup.sh

# List backups
ls -la backups/db/

# Restore from backup
docker-compose -f docker-compose.production.yml exec backup /restore.sh cmsvs_backup_YYYYMMDD_HHMMSS.sql.gz
```

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Database Migrations
```bash
# Run migrations
docker-compose -f docker-compose.production.yml exec app alembic upgrade head
```

### System Maintenance
```bash
# Clean up Docker resources
docker system prune -f

# Update system packages
sudo apt update && sudo apt upgrade -y

# Restart services if needed
docker-compose -f docker-compose.production.yml restart
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs [service-name]

# Check configuration
docker-compose -f docker-compose.production.yml config
```

#### Database Connection Issues
```bash
# Check database status
docker-compose -f docker-compose.production.yml exec db pg_isready -U cmsvs_user

# Check database logs
docker-compose -f docker-compose.production.yml logs db
```

#### SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in ssl/yourdomain.com.crt -text -noout

# Test SSL connection
openssl s_client -connect yourdomain.com:443
```

### Performance Optimization

#### Database Optimization
```bash
# Connect to database
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db

# Run VACUUM and ANALYZE
VACUUM ANALYZE;
```

#### Resource Monitoring
```bash
# Monitor resource usage
docker stats

# Check disk usage
df -h
du -sh uploads/ logs/ backups/
```

## 📞 Support

For production support:
1. Check logs first: `docker-compose -f docker-compose.production.yml logs`
2. Verify configuration: `python deploy.py --check-only`
3. Run health checks: `curl https://yourdomain.com/health`

## 🔐 Security Checklist

- [ ] Strong passwords generated for all accounts
- [ ] SSL certificates installed and configured
- [ ] Firewall configured to block unnecessary ports
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] Regular backups scheduled
- [ ] Log monitoring set up
- [ ] System updates automated
- [ ] Access logs reviewed regularly
- [ ] Database access restricted

## 📈 Performance Checklist

- [ ] Database connection pooling configured
- [ ] Static file caching enabled
- [ ] Gzip compression enabled
- [ ] Resource limits set for containers
- [ ] Health checks configured
- [ ] Monitoring and alerting set up
- [ ] Backup and recovery tested
- [ ] Load testing performed
