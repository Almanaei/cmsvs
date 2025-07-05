# CMSVS Production Security Guide

## 🔒 PostgreSQL Security Configuration

### 1. Database Connection Verification

Your current configuration uses:
```
DATABASE_URL=postgresql://cmsvs_user:admin@db:5432/cmsvs_db
```

**⚠️ CRITICAL SECURITY ISSUE**: The password `admin` is extremely insecure for production.

### 2. Secure Database Setup

#### A. Generate Secure Passwords
```bash
# Run the production setup script
chmod +x scripts/setup-production.sh
./scripts/setup-production.sh
```

This will generate:
- Secure database password (25 characters)
- Redis password
- Application secret key
- Admin password

#### B. Database User Permissions
The `cmsvs_user` has been configured with minimal required permissions:
- `CONNECT` on database
- `USAGE` and `CREATE` on public schema
- Connection limit of 50 concurrent connections
- No superuser privileges

#### C. Network Security
- Database only accepts connections from Docker network (172.20.0.0/16)
- No external database access allowed
- Application connects via internal Docker network

### 3. Authentication Security

#### Password Encryption
- Uses `scram-sha-256` (most secure method)
- Stronger than default `md5` encryption

#### Connection Authentication
```sql
# pg_hba.conf configuration
host    cmsvs_db    cmsvs_user    172.20.0.0/16    scram-sha-256
```

## 🐳 Docker Network Security

### 1. Container Isolation
- Custom bridge network `cmsvs_network`
- Containers communicate only within network
- No direct external access to database

### 2. Security Options
```yaml
security_opt:
  - no-new-privileges:true
```

### 3. Non-Root User
- Application runs as user `1000:1000`
- Database runs with restricted permissions

## ⚡ Performance & Connection Pooling

### 1. Production Pool Settings
Your `.env.production` is optimized:
```
DB_POOL_SIZE=30          # Increased for production
DB_MAX_OVERFLOW=50       # Higher overflow for peak times
DB_POOL_TIMEOUT=30       # Shorter timeout for production
DB_POOL_RECYCLE=1800     # 30 minutes recycle time
```

### 2. PostgreSQL Performance
- `shared_buffers=256MB`
- `effective_cache_size=1GB`
- `max_connections=100`
- Connection pooling prevents connection exhaustion

## 🔧 Production Deployment Steps

### 1. Initial Setup
```bash
# 1. Run production setup
./scripts/setup-production.sh

# 2. Update .env.production with your specific values
nano .env.production

# 3. Deploy services
docker-compose -f docker-compose.production.yml up -d

# 4. Test database connection
python scripts/test-db-connection.py

# 5. Initialize application database
docker-compose -f docker-compose.production.yml exec app python init_db.py
```

### 2. Security Verification
```bash
# Test database security
python scripts/test-db-connection.py

# Check container security
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "\du"

# Verify network isolation
docker network inspect cmsvs_cmsvs_network
```

## 🛡️ Security Hardening Checklist

### Database Security
- [x] Strong password authentication (scram-sha-256)
- [x] Network access restricted to application only
- [x] User permissions minimized (no superuser)
- [x] Connection limits enforced
- [x] Audit logging enabled
- [x] SSL disabled (internal Docker network)
- [x] Public schema permissions revoked from PUBLIC

### Application Security
- [ ] **CRITICAL**: Change SECRET_KEY in .env.production
- [ ] **CRITICAL**: Change ADMIN_PASSWORD in .env.production
- [ ] Update SMTP credentials if using email
- [x] HTTPS enforcement enabled
- [x] Secure cookies enabled
- [x] HSTS headers configured
- [x] Rate limiting enabled

### Infrastructure Security
- [ ] Firewall configured (only ports 80, 443 open)
- [ ] SSH key-based authentication
- [ ] Regular security updates
- [ ] Log monitoring setup
- [ ] Backup encryption
- [ ] SSL certificate from trusted CA

## 🚨 Critical Actions Required

### 1. Immediate (Before Deployment)
```bash
# Generate secure credentials
./scripts/setup-production.sh

# Update .env.production with generated values
# The script will show you the generated passwords
```

### 2. Post-Deployment
```bash
# Change admin password after first login
# Setup proper SSL certificate
# Configure firewall rules
# Setup log monitoring
```

## 📊 Monitoring & Maintenance

### 1. Database Monitoring
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Check slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- Check connection limits
SELECT rolname, rolconnlimit FROM pg_roles WHERE rolname = 'cmsvs_user';
```

### 2. Security Monitoring
- Monitor failed login attempts
- Check for unusual database activity
- Review connection logs regularly
- Monitor resource usage

### 3. Backup Strategy
```bash
# Database backup (automated via cron)
docker-compose -f docker-compose.production.yml exec db pg_dump -U cmsvs_user cmsvs_db > backup.sql

# Application data backup
docker-compose -f docker-compose.production.yml exec app tar -czf /app/backups/uploads-$(date +%Y%m%d).tar.gz /app/uploads
```

## 🔍 Testing Commands

### Database Connection Test
```bash
python scripts/test-db-connection.py
```

### Security Audit
```bash
# Check database permissions
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "\dp"

# Check user privileges
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "\du+"

# Test connection limits
# (Run multiple connections to test limit)
```

### Performance Test
```bash
# Test connection pool performance
python -c "
import asyncio
from scripts.test_db_connection import DatabaseTester
asyncio.run(DatabaseTester().test_connection_pool())
"
```

## 📞 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if database container is running
   - Verify network connectivity
   - Check firewall rules

2. **Authentication Failed**
   - Verify credentials in .env.production
   - Check pg_hba.conf configuration
   - Ensure password encryption matches

3. **Permission Denied**
   - Check user permissions in database
   - Verify schema access rights
   - Check file permissions on host

4. **Connection Pool Exhausted**
   - Monitor active connections
   - Adjust pool settings if needed
   - Check for connection leaks in application

### Emergency Procedures

1. **Database Access Lost**
   ```bash
   # Connect as postgres superuser
   docker-compose -f docker-compose.production.yml exec db psql -U postgres -d cmsvs_db
   ```

2. **Reset User Password**
   ```sql
   ALTER USER cmsvs_user WITH PASSWORD 'new_secure_password';
   ```

3. **Restore from Backup**
   ```bash
   docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db < backup.sql
   ```
