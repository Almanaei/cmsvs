#!/bin/bash
# Production testing and validation script for CMSVS Internal System
# Runs comprehensive tests to validate production readiness

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BASE_URL="${1:-http://localhost:8000}"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"

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

# Function to check prerequisites
check_prerequisites() {
    log "Checking test prerequisites..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required for testing"
        exit 1
    fi
    
    # Check if required Python packages are available
    python3 -c "import requests, psycopg2" 2>/dev/null || {
        warning "Installing required Python packages..."
        pip3 install requests psycopg2-binary
    }
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    success "Prerequisites check completed"
}

# Function to test application availability
test_application_availability() {
    log "Testing application availability..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$BASE_URL/health" >/dev/null 2>&1; then
            success "Application is available at $BASE_URL"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Application is not available at $BASE_URL after $max_attempts attempts"
            return 1
        fi
        
        log "Attempt $attempt/$max_attempts failed, retrying in 5 seconds..."
        sleep 5
        ((attempt++))
    done
}

# Function to run security tests
run_security_tests() {
    log "Running security tests..."
    
    local security_results="$TEST_RESULTS_DIR/security_test_results.txt"
    
    {
        echo "Security Test Results - $(date)"
        echo "=================================="
        echo ""
        
        # Test HTTPS redirect
        echo "Testing HTTPS redirect..."
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost" | grep -q "301\|302"; then
            echo "✅ HTTPS redirect working"
        else
            echo "❌ HTTPS redirect not working"
        fi
        
        # Test security headers
        echo ""
        echo "Testing security headers..."
        headers=$(curl -s -I "$BASE_URL/" || echo "Failed to get headers")
        
        if echo "$headers" | grep -q "X-Frame-Options"; then
            echo "✅ X-Frame-Options header present"
        else
            echo "❌ X-Frame-Options header missing"
        fi
        
        if echo "$headers" | grep -q "X-Content-Type-Options"; then
            echo "✅ X-Content-Type-Options header present"
        else
            echo "❌ X-Content-Type-Options header missing"
        fi
        
        if echo "$headers" | grep -q "Referrer-Policy"; then
            echo "✅ Referrer-Policy header present"
        else
            echo "❌ Referrer-Policy header missing"
        fi
        
        # Test rate limiting
        echo ""
        echo "Testing rate limiting..."
        rate_limit_test=0
        for i in {1..15}; do
            response_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
            if [ "$response_code" = "429" ]; then
                rate_limit_test=1
                break
            fi
            sleep 0.2
        done
        
        if [ $rate_limit_test -eq 1 ]; then
            echo "✅ Rate limiting is working"
        else
            echo "⚠️  Rate limiting may not be configured or threshold is high"
        fi
        
    } > "$security_results"
    
    cat "$security_results"
    success "Security tests completed - results saved to $security_results"
}

# Function to run performance tests
run_performance_tests() {
    log "Running performance tests..."
    
    local perf_results="$TEST_RESULTS_DIR/performance_test_results.txt"
    
    {
        echo "Performance Test Results - $(date)"
        echo "=================================="
        echo ""
        
        # Test response times
        echo "Testing response times..."
        for endpoint in "/health" "/login" "/"; do
            if [ "$endpoint" = "/" ]; then
                # Root endpoint might redirect, so follow redirects
                response_time=$(curl -s -o /dev/null -w "%{time_total}" -L "$BASE_URL$endpoint" 2>/dev/null || echo "failed")
            else
                response_time=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL$endpoint" 2>/dev/null || echo "failed")
            fi
            
            if [ "$response_time" != "failed" ]; then
                echo "✅ $endpoint: ${response_time}s"
            else
                echo "❌ $endpoint: Failed to get response time"
            fi
        done
        
        # Test concurrent requests
        echo ""
        echo "Testing concurrent requests (10 concurrent for 10 seconds)..."
        
        # Use Apache Bench if available
        if command -v ab &> /dev/null; then
            ab_result=$(ab -n 100 -c 10 -q "$BASE_URL/health" 2>/dev/null | grep -E "(Requests per second|Time per request)" || echo "AB test failed")
            echo "$ab_result"
        else
            echo "⚠️  Apache Bench (ab) not available, skipping concurrent test"
        fi
        
    } > "$perf_results"
    
    cat "$perf_results"
    success "Performance tests completed - results saved to $perf_results"
}

# Function to run database tests
run_database_tests() {
    log "Running database tests..."
    
    local db_results="$TEST_RESULTS_DIR/database_test_results.txt"
    
    {
        echo "Database Test Results - $(date)"
        echo "=================================="
        echo ""
        
        # Test database health endpoint
        echo "Testing database health endpoint..."
        db_health=$(curl -s "$BASE_URL/health/database" 2>/dev/null || echo "failed")
        
        if echo "$db_health" | grep -q '"status":"healthy"'; then
            echo "✅ Database health endpoint working"
        else
            echo "❌ Database health endpoint failed"
            echo "Response: $db_health"
        fi
        
        # Test database metrics (if available)
        echo ""
        echo "Testing database metrics..."
        db_metrics=$(curl -s "$BASE_URL/performance/database" 2>/dev/null || echo "failed")
        
        if [ "$db_metrics" != "failed" ] && [ "$db_metrics" != "404" ]; then
            echo "✅ Database metrics available"
        else
            echo "⚠️  Database metrics not available (may be disabled)"
        fi
        
    } > "$db_results"
    
    cat "$db_results"
    success "Database tests completed - results saved to $db_results"
}

# Function to run backup tests
run_backup_tests() {
    log "Running backup system tests..."
    
    local backup_results="$TEST_RESULTS_DIR/backup_test_results.txt"
    
    {
        echo "Backup System Test Results - $(date)"
        echo "=================================="
        echo ""
        
        # Test backup script availability
        echo "Testing backup script availability..."
        if [ -f "$SCRIPT_DIR/backup-manager.py" ]; then
            echo "✅ Backup manager script found"
            
            # Test backup listing
            echo ""
            echo "Testing backup listing..."
            if python3 "$SCRIPT_DIR/backup-manager.py" list >/dev/null 2>&1; then
                echo "✅ Backup listing works"
            else
                echo "❌ Backup listing failed"
            fi
            
        else
            echo "❌ Backup manager script not found"
        fi
        
        # Check backup directory
        echo ""
        echo "Checking backup directory..."
        if [ -d "$PROJECT_ROOT/backups" ]; then
            echo "✅ Backup directory exists"
            backup_count=$(find "$PROJECT_ROOT/backups" -name "*.gz" -type f | wc -l)
            echo "📊 Found $backup_count backup files"
        else
            echo "⚠️  Backup directory not found"
        fi
        
    } > "$backup_results"
    
    cat "$backup_results"
    success "Backup tests completed - results saved to $backup_results"
}

# Function to run comprehensive Python tests
run_python_validation() {
    log "Running comprehensive Python validation..."
    
    local python_results="$TEST_RESULTS_DIR/python_validation_results.json"
    
    # Get database URL from environment or use default
    local database_url=""
    if [ -f "$PROJECT_ROOT/.env.production" ]; then
        database_url=$(grep "DATABASE_URL" "$PROJECT_ROOT/.env.production" | cut -d'=' -f2- | tr -d '"')
    elif [ -f "$PROJECT_ROOT/.env" ]; then
        database_url=$(grep "DATABASE_URL" "$PROJECT_ROOT/.env" | cut -d'=' -f2- | tr -d '"')
    fi
    
    # Run Python validation
    cd "$PROJECT_ROOT"
    if python3 tests/test_production.py --url "$BASE_URL" --database-url "$database_url" --output "$python_results"; then
        success "Python validation completed successfully"
    else
        warning "Python validation completed with issues"
    fi
}

# Function to generate test report
generate_test_report() {
    log "Generating comprehensive test report..."
    
    local report_file="$TEST_RESULTS_DIR/production_test_report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>CMSVS Production Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .pass { color: green; }
        .fail { color: red; }
        .warning { color: orange; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>CMSVS Production Test Report</h1>
        <p>Generated on: $(date)</p>
        <p>Base URL: $BASE_URL</p>
    </div>
EOF
    
    # Add each test section
    for result_file in "$TEST_RESULTS_DIR"/*.txt; do
        if [ -f "$result_file" ]; then
            section_name=$(basename "$result_file" .txt | sed 's/_/ /g' | sed 's/\b\w/\U&/g')
            echo "    <div class=\"section\">" >> "$report_file"
            echo "        <h2>$section_name</h2>" >> "$report_file"
            echo "        <pre>" >> "$report_file"
            cat "$result_file" >> "$report_file"
            echo "        </pre>" >> "$report_file"
            echo "    </div>" >> "$report_file"
        fi
    done
    
    # Add Python validation results if available
    if [ -f "$TEST_RESULTS_DIR/python_validation_results.json" ]; then
        echo "    <div class=\"section\">" >> "$report_file"
        echo "        <h2>Python Validation Results</h2>" >> "$report_file"
        echo "        <pre>" >> "$report_file"
        python3 -m json.tool "$TEST_RESULTS_DIR/python_validation_results.json" >> "$report_file" 2>/dev/null || echo "Failed to format JSON" >> "$report_file"
        echo "        </pre>" >> "$report_file"
        echo "    </div>" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF
</body>
</html>
EOF
    
    success "Test report generated: $report_file"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [base_url]"
    echo ""
    echo "Examples:"
    echo "  $0                           # Test localhost:8000"
    echo "  $0 https://yourdomain.com    # Test production domain"
    echo ""
    echo "Test results will be saved to: $TEST_RESULTS_DIR"
}

# Main function
main() {
    echo "🧪 CMSVS Production Testing Suite"
    echo "=================================="
    echo "Base URL: $BASE_URL"
    echo "Results Directory: $TEST_RESULTS_DIR"
    echo ""
    
    # Run all tests
    check_prerequisites
    test_application_availability
    run_security_tests
    run_performance_tests
    run_database_tests
    run_backup_tests
    run_python_validation
    generate_test_report
    
    echo ""
    echo "🎉 Production testing completed!"
    echo "📊 View detailed results in: $TEST_RESULTS_DIR"
    echo "📋 HTML report: $TEST_RESULTS_DIR/production_test_report.html"
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        show_usage
        exit 0
        ;;
    *)
        main
        ;;
esac
