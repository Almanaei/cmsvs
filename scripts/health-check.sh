#!/bin/bash
# Health check script for CMSVS Internal System
# This script performs comprehensive health checks on the production system

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/health-check.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
ALERT_THRESHOLD_DISK=85

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check Docker services
check_docker_services() {
    log "Checking Docker services..."
    
    local services=("app" "db" "nginx" "redis")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" ps "$service" | grep -q "Up"; then
            success "$service is running"
        else
            error "$service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        error "Failed services: ${failed_services[*]}"
        return 1
    fi
    
    return 0
}

# Function to check application health endpoint
check_application_health() {
    log "Checking application health endpoint..."
    
    local url="http://localhost/health"
    local response
    
    if response=$(curl -s -w "%{http_code}" "$url" 2>/dev/null); then
        local http_code="${response: -3}"
        local body="${response%???}"
        
        if [ "$http_code" = "200" ]; then
            success "Application health endpoint is responding (HTTP $http_code)"
            return 0
        else
            error "Application health endpoint returned HTTP $http_code"
            return 1
        fi
    else
        error "Failed to connect to application health endpoint"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    log "Checking database connectivity..."
    
    if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" exec -T db pg_isready -U cmsvs_user >/dev/null 2>&1; then
        success "Database is accepting connections"
        
        # Check database health from application
        if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" exec -T app python -c "
from app.database import SessionLocal
from sqlalchemy import text
import sys

db = SessionLocal()
try:
    result = db.execute(text('SELECT COUNT(*) FROM users'))
    user_count = result.scalar()
    print(f'Database query successful - {user_count} users')
except Exception as e:
    print(f'Database query failed: {e}')
    sys.exit(1)
finally:
    db.close()
" 2>/dev/null; then
            success "Database queries are working"
            return 0
        else
            error "Database queries are failing"
            return 1
        fi
    else
        error "Database is not accepting connections"
        return 1
    fi
}

# Function to check system resources
check_system_resources() {
    log "Checking system resources..."
    
    local issues=0
    
    # Check CPU usage
    local cpu_usage
    if command -v top >/dev/null 2>&1; then
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
        if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
            warning "High CPU usage: ${cpu_usage}%"
            ((issues++))
        else
            success "CPU usage is normal: ${cpu_usage}%"
        fi
    fi
    
    # Check memory usage
    local memory_usage
    if command -v free >/dev/null 2>&1; then
        memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
        if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
            warning "High memory usage: ${memory_usage}%"
            ((issues++))
        else
            success "Memory usage is normal: ${memory_usage}%"
        fi
    fi
    
    # Check disk usage
    local disk_usage
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt "$ALERT_THRESHOLD_DISK" ]; then
        warning "High disk usage: ${disk_usage}%"
        ((issues++))
    else
        success "Disk usage is normal: ${disk_usage}%"
    fi
    
    return $issues
}

# Function to check SSL certificate
check_ssl_certificate() {
    log "Checking SSL certificate..."
    
    local domain="localhost"  # Replace with your actual domain
    
    if command -v openssl >/dev/null 2>&1; then
        local cert_info
        if cert_info=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null); then
            local expiry_date
            expiry_date=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
            
            if [ -n "$expiry_date" ]; then
                local expiry_timestamp
                expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null)
                local current_timestamp
                current_timestamp=$(date +%s)
                local days_until_expiry
                days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
                
                if [ "$days_until_expiry" -lt 30 ]; then
                    warning "SSL certificate expires in $days_until_expiry days"
                    return 1
                else
                    success "SSL certificate is valid (expires in $days_until_expiry days)"
                    return 0
                fi
            else
                warning "Could not parse SSL certificate expiry date"
                return 1
            fi
        else
            warning "Could not retrieve SSL certificate information"
            return 1
        fi
    else
        warning "OpenSSL not available, skipping SSL certificate check"
        return 0
    fi
}

# Function to check log files for errors
check_logs() {
    log "Checking recent log files for errors..."
    
    local log_files=(
        "$PROJECT_ROOT/logs/app.log"
        "/var/log/nginx/error.log"
    )
    
    local error_count=0
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            local recent_errors
            recent_errors=$(tail -n 100 "$log_file" | grep -i "error\|critical\|fatal" | wc -l)
            
            if [ "$recent_errors" -gt 0 ]; then
                warning "Found $recent_errors recent errors in $log_file"
                ((error_count++))
            else
                success "No recent errors in $log_file"
            fi
        else
            warning "Log file not found: $log_file"
        fi
    done
    
    return $error_count
}

# Function to check backup status
check_backups() {
    log "Checking backup status..."
    
    local backup_dir="$PROJECT_ROOT/backups/db"
    
    if [ -d "$backup_dir" ]; then
        local latest_backup
        latest_backup=$(find "$backup_dir" -name "*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [ -n "$latest_backup" ]; then
            local backup_age
            backup_age=$(( ($(date +%s) - $(stat -c %Y "$latest_backup")) / 86400 ))
            
            if [ "$backup_age" -gt 1 ]; then
                warning "Latest backup is $backup_age days old"
                return 1
            else
                success "Latest backup is recent (${backup_age} days old)"
                return 0
            fi
        else
            error "No backups found in $backup_dir"
            return 1
        fi
    else
        error "Backup directory not found: $backup_dir"
        return 1
    fi
}

# Function to generate health report
generate_report() {
    local total_checks=$1
    local failed_checks=$2
    local warnings=$3
    
    echo ""
    echo "=================================="
    echo "   HEALTH CHECK REPORT"
    echo "=================================="
    echo "Date: $(date)"
    echo "Total Checks: $total_checks"
    echo "Failed Checks: $failed_checks"
    echo "Warnings: $warnings"
    echo ""
    
    if [ "$failed_checks" -eq 0 ] && [ "$warnings" -eq 0 ]; then
        echo "🟢 System Status: HEALTHY"
    elif [ "$failed_checks" -eq 0 ]; then
        echo "🟡 System Status: WARNING"
    else
        echo "🔴 System Status: CRITICAL"
    fi
    
    echo "=================================="
    echo ""
    echo "📝 Full log: $LOG_FILE"
}

# Function to send alerts (placeholder)
send_alert() {
    local severity=$1
    local message=$2
    
    log "ALERT [$severity]: $message"
    
    # Add your alerting logic here (email, Slack, PagerDuty, etc.)
    # Example:
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"🚨 CMSVS Alert [$severity]: $message\"}" \
    #   "$SLACK_WEBHOOK_URL"
}

# Main health check function
main() {
    log "Starting comprehensive health check..."
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    local total_checks=0
    local failed_checks=0
    local warnings=0
    
    # Run health checks
    checks=(
        "check_docker_services"
        "check_application_health"
        "check_database"
        "check_system_resources"
        "check_ssl_certificate"
        "check_logs"
        "check_backups"
    )
    
    for check in "${checks[@]}"; do
        ((total_checks++))
        
        if ! $check; then
            ((failed_checks++))
        fi
        
        # Count warnings from system resources check
        if [ "$check" = "check_system_resources" ]; then
            local resource_issues=$?
            ((warnings += resource_issues))
        fi
    done
    
    # Generate report
    generate_report $total_checks $failed_checks $warnings
    
    # Send alerts if necessary
    if [ "$failed_checks" -gt 0 ]; then
        send_alert "CRITICAL" "$failed_checks critical issues detected"
    elif [ "$warnings" -gt 0 ]; then
        send_alert "WARNING" "$warnings warnings detected"
    fi
    
    # Exit with appropriate code
    if [ "$failed_checks" -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Parse command line arguments
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --verbose, -v   Enable verbose output"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
