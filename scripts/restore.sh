#!/bin/bash
# Database restore script for CMSVS Internal System
# This script restores the PostgreSQL database from a backup

set -e

# Configuration
DB_HOST="db"
DB_PORT="5432"
DB_NAME="cmsvs_db"
DB_USER="cmsvs_user"
BACKUP_DIR="/backups"

# Function to show usage
show_usage() {
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 cmsvs_backup_20240101_120000.sql.gz"
    echo ""
    echo "Available backups:"
    ls -la "${BACKUP_DIR}"/cmsvs_backup_*.sql.gz 2>/dev/null || echo "No backups found"
}

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "ERROR: No backup file specified"
    show_usage
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup file exists
if [ ! -f "${BACKUP_PATH}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_PATH}"
    show_usage
    exit 1
fi

echo "Starting database restore at $(date)"
echo "Backup file: ${BACKUP_PATH}"

# Confirm restore operation
echo "WARNING: This will replace all data in the database!"
echo "Database: ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore operation cancelled"
    exit 0
fi

# Create a backup of current database before restore
CURRENT_BACKUP="cmsvs_backup_before_restore_$(date +"%Y%m%d_%H%M%S").sql"
echo "Creating backup of current database: ${CURRENT_BACKUP}"

if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
   --clean --no-owner --no-privileges > "${BACKUP_DIR}/${CURRENT_BACKUP}"; then
    gzip "${BACKUP_DIR}/${CURRENT_BACKUP}"
    echo "Current database backed up successfully"
else
    echo "WARNING: Failed to backup current database"
    read -p "Continue with restore anyway? (yes/no): " FORCE_CONTINUE
    if [ "${FORCE_CONTINUE}" != "yes" ]; then
        echo "Restore operation cancelled"
        exit 1
    fi
fi

# Decompress backup if it's gzipped
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo "Decompressing backup file..."
    TEMP_SQL_FILE="/tmp/restore_temp.sql"
    gunzip -c "${BACKUP_PATH}" > "${TEMP_SQL_FILE}"
    RESTORE_FILE="${TEMP_SQL_FILE}"
else
    RESTORE_FILE="${BACKUP_PATH}"
fi

# Restore database
echo "Restoring database from backup..."
if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" < "${RESTORE_FILE}"; then
    echo "Database restore completed successfully"
    
    # Log restore success
    echo "$(date): Restore successful - ${BACKUP_FILE}" >> "${BACKUP_DIR}/restore.log"
    
    # Clean up temporary file
    if [ -f "${TEMP_SQL_FILE}" ]; then
        rm "${TEMP_SQL_FILE}"
    fi
    
    echo "Restore process completed at $(date)"
    echo "----------------------------------------"
    
else
    echo "ERROR: Database restore failed"
    echo "$(date): Restore failed - ${BACKUP_FILE}" >> "${BACKUP_DIR}/restore.log"
    
    # Clean up temporary file
    if [ -f "${TEMP_SQL_FILE}" ]; then
        rm "${TEMP_SQL_FILE}"
    fi
    
    exit 1
fi
