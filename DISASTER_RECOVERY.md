# CMSVS Internal System - Disaster Recovery Guide

This guide provides comprehensive procedures for disaster recovery, backup management, and business continuity for the CMSVS Internal System.

## 🚨 Emergency Response Procedures

### Immediate Response Checklist

1. **Assess the Situation**
   - [ ] Identify the type of failure (hardware, software, data corruption, security breach)
   - [ ] Determine the scope of impact (partial or complete system failure)
   - [ ] Document the incident with timestamps

2. **Notify Stakeholders**
   - [ ] Alert system administrators
   - [ ] Notify management
   - [ ] Inform affected users (if appropriate)

3. **Secure the Environment**
   - [ ] Isolate affected systems if security breach is suspected
   - [ ] Preserve evidence for investigation
   - [ ] Prevent further damage

## 📋 Recovery Procedures

### Database Recovery

#### Complete Database Loss
```bash
# 1. Stop the application
docker-compose -f docker-compose.production.yml down

# 2. List available database backups
python scripts/backup-manager.py list --type database

# 3. Restore from the most recent backup
python scripts/backup-manager.py restore-db --file db_backup_YYYYMMDD_HHMMSS.sql.gz

# 4. Verify database integrity
python scripts/db_manage.py check

# 5. Restart the application
docker-compose -f docker-compose.production.yml up -d
```

#### Partial Database Corruption
```bash
# 1. Create a backup of current state
python scripts/backup-manager.py backup-db --name "before_recovery_$(date +%Y%m%d_%H%M%S)"

# 2. Attempt database repair
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d cmsvs_db -c "REINDEX DATABASE cmsvs_db;"

# 3. If repair fails, restore from backup (see complete loss procedure)
```

### File System Recovery

#### Lost Upload Files
```bash
# 1. Stop the application
docker-compose -f docker-compose.production.yml down

# 2. List available file backups
python scripts/backup-manager.py list --type files

# 3. Extract files from backup
cd backups/files
tar -xzf files_backup_YYYYMMDD_HHMMSS.tar.gz

# 4. Restore files to correct location
cp -r uploads/* ../../uploads/
cp -r logs/* ../../logs/

# 5. Fix permissions
chown -R 1000:1000 ../../uploads ../../logs

# 6. Restart application
docker-compose -f docker-compose.production.yml up -d
```

### Complete System Recovery

#### Server Hardware Failure
```bash
# 1. Set up new server with same OS and Docker
# 2. Clone the repository
git clone <repository-url> cmsvs
cd cmsvs

# 3. Restore configuration files
python scripts/backup-manager.py list --type config
# Extract latest config backup to restore .env files, etc.

# 4. Set up secrets
./scripts/setup-secrets.sh

# 5. Restore database
python scripts/backup-manager.py restore-db --file <latest-db-backup>

# 6. Restore files
# Extract latest files backup

# 7. Deploy application
./scripts/deploy-production.sh

# 8. Verify system functionality
./scripts/health-check.sh
```

## 🔄 Backup Management

### Automated Backup Schedule

#### Daily Backups (Recommended Crontab)
```bash
# Add to crontab: crontab -e

# Daily database backup at 2 AM
0 2 * * * /path/to/cmsvs/scripts/backup.sh db

# Weekly full backup on Sundays at 1 AM
0 1 * * 0 /path/to/cmsvs/scripts/backup.sh full

# Monthly configuration backup on 1st of month at 3 AM
0 3 1 * * /path/to/cmsvs/scripts/backup.sh config

# Daily cleanup at 4 AM
0 4 * * * cd /path/to/cmsvs && python scripts/backup-manager.py cleanup --retention-days 30
```

#### Docker-based Backup Scheduling
```yaml
# Add to docker-compose.production.yml
backup-scheduler:
  image: alpine:latest
  container_name: cmsvs_backup_scheduler
  volumes:
    - ./scripts:/scripts
    - ./backups:/backups
    - /var/run/docker.sock:/var/run/docker.sock
  command: |
    sh -c "
    echo '0 2 * * * /scripts/backup.sh db' > /etc/crontabs/root &&
    echo '0 1 * * 0 /scripts/backup.sh full' >> /etc/crontabs/root &&
    crond -f
    "
  restart: unless-stopped
```

### Manual Backup Commands

```bash
# Create immediate full backup
./scripts/backup.sh full emergency_backup_$(date +%Y%m%d_%H%M%S)

# Create database-only backup
./scripts/backup.sh db

# Create files backup
./scripts/backup.sh files

# Create configuration backup
./scripts/backup.sh config

# List all backups
python scripts/backup-manager.py list

# Clean up old backups
python scripts/backup-manager.py cleanup --retention-days 30
```

## 🔍 Backup Verification

### Regular Backup Testing
```bash
# Test database backup integrity (monthly)
#!/bin/bash
LATEST_BACKUP=$(python scripts/backup-manager.py list --type database | jq -r '.[0].file')
echo "Testing backup: $LATEST_BACKUP"

# Create test database
docker-compose -f docker-compose.production.yml exec db createdb -U cmsvs_user test_restore

# Restore to test database
python scripts/backup-manager.py restore-db --file $LATEST_BACKUP --database test_restore

# Verify data integrity
docker-compose -f docker-compose.production.yml exec db psql -U cmsvs_user -d test_restore -c "SELECT COUNT(*) FROM users;"

# Clean up test database
docker-compose -f docker-compose.production.yml exec db dropdb -U cmsvs_user test_restore

echo "Backup test completed"
```

## 📊 Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO)

### Target Objectives
- **RTO (Recovery Time Objective)**: 4 hours maximum
- **RPO (Recovery Point Objective)**: 24 hours maximum (daily backups)

### Recovery Time Estimates
- **Database restore**: 30 minutes - 2 hours (depending on size)
- **File restore**: 15 minutes - 1 hour
- **Complete system rebuild**: 2 - 4 hours
- **Configuration restore**: 15 minutes

## 🔐 Security Considerations

### Backup Security
- All backups are encrypted at rest
- Database backups exclude sensitive authentication tokens
- Access to backup files is restricted to authorized personnel
- Backup integrity is verified using checksums

### Incident Response
1. **Security Breach**: Immediately isolate systems and preserve evidence
2. **Data Corruption**: Stop all write operations and assess damage
3. **Unauthorized Access**: Change all passwords and review access logs

## 📞 Emergency Contacts

### Technical Contacts
- **System Administrator**: [Contact Information]
- **Database Administrator**: [Contact Information]
- **Security Team**: [Contact Information]

### Business Contacts
- **IT Manager**: [Contact Information]
- **Business Continuity Manager**: [Contact Information]
- **Executive Sponsor**: [Contact Information]

## 📝 Recovery Documentation

### Post-Recovery Checklist
- [ ] Verify all services are running
- [ ] Test user authentication
- [ ] Verify data integrity
- [ ] Check file uploads functionality
- [ ] Review system logs for errors
- [ ] Update stakeholders on recovery status
- [ ] Document lessons learned
- [ ] Update recovery procedures if needed

### Recovery Log Template
```
Incident Date: ___________
Incident Type: ___________
Impact Assessment: ___________
Recovery Start Time: ___________
Recovery End Time: ___________
Backup Used: ___________
Data Loss: ___________
Lessons Learned: ___________
Procedure Updates Needed: ___________
```

## 🧪 Testing and Validation

### Monthly Recovery Tests
1. **Backup Restoration Test**
   - Restore database to test environment
   - Verify data integrity
   - Test application functionality

2. **Disaster Recovery Simulation**
   - Simulate complete system failure
   - Execute recovery procedures
   - Measure recovery time
   - Document issues and improvements

### Annual DR Exercises
- Full-scale disaster recovery exercise
- Business continuity testing
- Communication plan testing
- Recovery procedure updates

## 📈 Monitoring and Alerting

### Backup Monitoring
- Daily backup success/failure alerts
- Backup size trend monitoring
- Storage capacity alerts
- Backup age alerts (if backups are too old)

### System Health Monitoring
- Database connectivity monitoring
- File system space monitoring
- Application health checks
- Performance degradation alerts

## 🔧 Tools and Scripts

### Available Recovery Tools
- `scripts/backup-manager.py` - Comprehensive backup management
- `scripts/backup.sh` - Automated backup execution
- `scripts/restore.sh` - Database restoration
- `scripts/health-check.sh` - System health verification
- `scripts/deploy-production.sh` - Complete system deployment

### External Dependencies
- PostgreSQL client tools (pg_dump, pg_restore)
- Docker and Docker Compose
- Git for code repository access
- Network connectivity for external backups (if configured)

## 📚 Additional Resources

- [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)
- [System Administration Guide](README.md)
- [Security Best Practices](SECURITY.md)
- [Monitoring and Alerting Setup](MONITORING.md)

---

**Remember**: Regular testing of disaster recovery procedures is crucial. Schedule monthly tests and annual full-scale exercises to ensure procedures remain effective and up-to-date.
