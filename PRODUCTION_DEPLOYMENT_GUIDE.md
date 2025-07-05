# 🚀 CMSVS Production Deployment Guide

## Server Information
- **Server IP**: 91.99.118.65
- **Operating System**: Ubuntu/Debian (recommended)
- **Required RAM**: Minimum 2GB, Recommended 4GB+
- **Required Storage**: Minimum 20GB free space

## Prerequisites

### 1. Server Access
Ensure you have SSH access to your server:
```bash
ssh root@91.99.118.65
# or
ssh your_username@91.99.118.65
```

### 2. Domain Setup (Optional but Recommended)
- Point your domain to IP `91.99.118.65`
- Example: `cmsvs.yourdomain.com` → `91.99.118.65`

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

#### Step 1: Run Deployment Script
```bash
# Make script executable
chmod +x deploy-production.sh

# Run deployment
./deploy-production.sh
```

The script will:
- ✅ Check server connectivity
- ✅ Prepare deployment files
- ✅ Transfer files to server
- ✅ Install Docker and Docker Compose
- ✅ Deploy the application
- ✅ Configure firewall

#### Step 2: Verify Deployment
After deployment, check if services are running:
```bash
ssh root@91.99.118.65 "cd /opt/cmsvs && docker-compose -f docker-compose.production.yml ps"
```

#### Step 3: Access Application
- **HTTP**: http://91.99.118.65
- **Admin Login**: admin / admin123

### Method 2: Manual Deployment

#### Step 1: Prepare Server
```bash
# Connect to server
ssh root@91.99.118.65

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/cmsvs
```

#### Step 2: Transfer Files
From your local machine:
```bash
# Create deployment package
tar -czf cmsvs-deployment.tar.gz app nginx docker-compose.production.yml .env.production Dockerfile requirements.txt init_db.py

# Transfer to server
scp cmsvs-deployment.tar.gz root@91.99.118.65:/opt/cmsvs/

# Extract on server
ssh root@91.99.118.65 "cd /opt/cmsvs && tar -xzf cmsvs-deployment.tar.gz"
```

#### Step 3: Deploy Application
```bash
# Connect to server
ssh root@91.99.118.65

# Navigate to application directory
cd /opt/cmsvs

# Build and start services
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Initialize database
docker-compose -f docker-compose.production.yml exec app python init_db.py

# Check status
docker-compose -f docker-compose.production.yml ps
```

#### Step 4: Configure Firewall
```bash
# Install and configure UFW
apt-get install -y ufw

# Configure rules
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Enable firewall
ufw --force enable
```

## SSL Certificate Setup

### Option 1: Automated SSL Setup
```bash
# Transfer SSL script to server
scp setup-ssl.sh root@91.99.118.65:/opt/cmsvs/

# Run SSL setup on server
ssh root@91.99.118.65 "cd /opt/cmsvs && chmod +x setup-ssl.sh && ./setup-ssl.sh"
```

### Option 2: Manual SSL Setup
```bash
# On server, install Certbot
snap install --classic certbot

# Stop nginx temporarily
cd /opt/cmsvs
docker-compose -f docker-compose.production.yml stop nginx

# Obtain certificate (replace with your domain)
certbot certonly --standalone -d your-domain.com

# Update nginx configuration for SSL
# (See setup-ssl.sh for complete configuration)

# Restart services
docker-compose -f docker-compose.production.yml up -d
```

## Post-Deployment Configuration

### 1. Update Admin Password
```bash
# Connect to server
ssh root@91.99.118.65

# Access application container
cd /opt/cmsvs
docker-compose -f docker-compose.production.yml exec app python -c "
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_password_hash

db = next(get_db())
admin = db.query(User).filter(User.username == 'admin').first()
admin.hashed_password = get_password_hash('your_new_secure_password')
db.commit()
print('Admin password updated')
"
```

### 2. Configure Backup
```bash
# Create backup script
cat > /opt/cmsvs/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/cmsvs/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
docker-compose -f /opt/cmsvs/docker-compose.production.yml exec -T db pg_dump -U cmsvs_user cmsvs_db > $BACKUP_DIR/db_backup_$DATE.sql

# Files backup
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz /opt/cmsvs/uploads

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/cmsvs/backup.sh

# Add to crontab (daily backup at 2 AM)
echo "0 2 * * * /opt/cmsvs/backup.sh" | crontab -
```

### 3. Monitor Services
```bash
# Check service status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs app
docker-compose -f docker-compose.production.yml logs nginx
docker-compose -f docker-compose.production.yml logs db

# Monitor resource usage
docker stats
```

## Troubleshooting

### Common Issues

#### 1. Services Not Starting
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Restart services
docker-compose -f docker-compose.production.yml restart
```

#### 2. Database Connection Issues
```bash
# Check database status
docker-compose -f docker-compose.production.yml exec db pg_isready -U cmsvs_user

# Reset database (WARNING: This will delete all data)
docker-compose -f docker-compose.production.yml down -v
docker-compose -f docker-compose.production.yml up -d
docker-compose -f docker-compose.production.yml exec app python init_db.py
```

#### 3. SSL Certificate Issues
```bash
# Check certificate status
certbot certificates

# Renew certificate manually
certbot renew

# Restart nginx after renewal
docker-compose -f docker-compose.production.yml restart nginx
```

#### 4. Firewall Issues
```bash
# Check firewall status
ufw status

# Allow specific IP (if needed)
ufw allow from YOUR_IP_ADDRESS

# Disable firewall temporarily (for debugging)
ufw disable
```

## Security Checklist

- [ ] Change default admin password
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Configure regular backups
- [ ] Update server packages regularly
- [ ] Monitor application logs
- [ ] Set up fail2ban for SSH protection
- [ ] Configure log rotation

## Maintenance Commands

```bash
# Update application
cd /opt/cmsvs
git pull  # if using git
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# View resource usage
docker system df
docker system prune  # Clean up unused resources

# Database maintenance
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "VACUUM ANALYZE;"
```

## Support

If you encounter issues during deployment:

1. Check the logs: `docker-compose logs`
2. Verify network connectivity
3. Ensure all required ports are open
4. Check disk space: `df -h`
5. Monitor system resources: `htop` or `top`

---

**Next Steps**: After successful deployment, proceed with SSL setup and domain configuration for production use.
