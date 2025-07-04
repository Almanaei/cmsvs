#!/bin/bash
# Enhanced backup script for CMSVS Internal System
# This script creates comprehensive backups using the backup manager

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_TYPE="${1:-full}"  # Default to full backup
BACKUP_NAME="${2:-}"      # Optional backup name

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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

# Function to run backup using Python backup manager
run_backup() {
    local backup_type="$1"
    local backup_name="$2"

    log "Starting $backup_type backup..."

    # Build command
    local cmd="python $SCRIPT_DIR/backup-manager.py backup-$backup_type"
    if [ -n "$backup_name" ]; then
        cmd="$cmd --name $backup_name"
    fi

    # Run backup
    if result=$(cd "$PROJECT_ROOT" && $cmd 2>&1); then
        success "$backup_type backup completed successfully"
        echo "$result" | jq '.' 2>/dev/null || echo "$result"
        return 0
    else
        error "$backup_type backup failed"
        echo "$result"
        return 1
    fi
}

# Function to send notification (if configured)
send_notification() {
    local status="$1"
    local message="$2"

    # Add your notification logic here
    # Example: Send to Slack, email, etc.
    log "Backup $status: $message"
}

# Main backup execution
main() {
    log "CMSVS Backup Script Started"
    log "Backup type: $BACKUP_TYPE"

    case "$BACKUP_TYPE" in
        "db"|"database")
            if run_backup "db" "$BACKUP_NAME"; then
                send_notification "SUCCESS" "Database backup completed"
                exit 0
            else
                send_notification "FAILED" "Database backup failed"
                exit 1
            fi
            ;;
        "files")
            if run_backup "files" "$BACKUP_NAME"; then
                send_notification "SUCCESS" "Files backup completed"
                exit 0
            else
                send_notification "FAILED" "Files backup failed"
                exit 1
            fi
            ;;
        "config")
            if run_backup "config" "$BACKUP_NAME"; then
                send_notification "SUCCESS" "Configuration backup completed"
                exit 0
            else
                send_notification "FAILED" "Configuration backup failed"
                exit 1
            fi
            ;;
        "full")
            if run_backup "full" "$BACKUP_NAME"; then
                send_notification "SUCCESS" "Full system backup completed"

                # Run cleanup after successful full backup
                log "Running backup cleanup..."
                if cd "$PROJECT_ROOT" && python "$SCRIPT_DIR/backup-manager.py" cleanup; then
                    success "Backup cleanup completed"
                else
                    warning "Backup cleanup had issues"
                fi

                exit 0
            else
                send_notification "FAILED" "Full system backup failed"
                exit 1
            fi
            ;;
        *)
            error "Unknown backup type: $BACKUP_TYPE"
            echo "Usage: $0 [db|files|config|full] [backup_name]"
            exit 1
            ;;
    esac
}

# Check if Python backup manager exists
if [ ! -f "$SCRIPT_DIR/backup-manager.py" ]; then
    error "Backup manager not found: $SCRIPT_DIR/backup-manager.py"
    exit 1
fi

# Run main function
main
