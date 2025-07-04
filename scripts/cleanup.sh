#!/bin/bash
# Quick cleanup script for CMSVS Internal System
# Removes temporary files and prepares project for production

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run    Show what would be removed without actually removing"
    echo "  --help       Show this help message"
    echo ""
    echo "This script will clean up temporary files, test files, and development"
    echo "documentation while preserving essential production files."
}

# Function to run Python cleanup
run_python_cleanup() {
    local dry_run_flag="$1"
    
    log "Running Python cleanup script..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$dry_run_flag" = "--dry-run" ]; then
        python3 "$SCRIPT_DIR/cleanup-project.py" --dry-run
    else
        python3 "$SCRIPT_DIR/cleanup-project.py"
    fi
}

# Function to clean up additional files
additional_cleanup() {
    local dry_run="$1"
    
    log "Performing additional cleanup..."
    
    # Files to remove that might not be caught by Python script
    additional_files=(
        "$PROJECT_ROOT/.coverage"
        "$PROJECT_ROOT/coverage.xml"
        "$PROJECT_ROOT/.pytest_cache"
        "$PROJECT_ROOT/.mypy_cache"
        "$PROJECT_ROOT/htmlcov"
    )
    
    for file_path in "${additional_files[@]}"; do
        if [ -e "$file_path" ]; then
            if [ "$dry_run" = "true" ]; then
                log "Would remove: $file_path"
            else
                rm -rf "$file_path"
                log "Removed: $file_path"
            fi
        fi
    done
    
    # Clean up any .pyc files that might be missed
    if [ "$dry_run" = "true" ]; then
        log "Would remove any remaining .pyc files"
    else
        find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
        find "$PROJECT_ROOT" -name "*.pyo" -delete 2>/dev/null || true
        log "Removed any remaining .pyc/.pyo files"
    fi
}

# Function to optimize remaining files
optimize_files() {
    local dry_run="$1"
    
    log "Optimizing remaining files..."
    
    # Remove trailing whitespace from Python files (if not dry run)
    if [ "$dry_run" != "true" ]; then
        find "$PROJECT_ROOT/app" -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \; 2>/dev/null || true
        log "Cleaned trailing whitespace from Python files"
    else
        log "Would clean trailing whitespace from Python files"
    fi
    
    # Ensure scripts are executable
    if [ "$dry_run" != "true" ]; then
        chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
        chmod +x "$SCRIPT_DIR"/*.py 2>/dev/null || true
        chmod +x "$PROJECT_ROOT/deploy.py" 2>/dev/null || true
        log "Made scripts executable"
    else
        log "Would make scripts executable"
    fi
}

# Function to show final summary
show_summary() {
    log "Cleanup completed!"
    echo ""
    echo "📁 Essential files preserved:"
    echo "  ✅ Application code (app/)"
    echo "  ✅ Production scripts (scripts/)"
    echo "  ✅ Docker configuration"
    echo "  ✅ Production documentation"
    echo "  ✅ Requirements and dependencies"
    echo ""
    echo "🗑️  Removed:"
    echo "  ❌ Temporary development files"
    echo "  ❌ Test files and logs"
    echo "  ❌ Development documentation"
    echo "  ❌ Cache directories"
    echo ""
    echo "🚀 Your project is now clean and production-ready!"
    echo ""
    echo "Next steps:"
    echo "1. Review the remaining files"
    echo "2. Test the application: python run.py"
    echo "3. Deploy to production: python deploy.py"
}

# Main function
main() {
    local dry_run_flag=""
    local dry_run_bool="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run_flag="--dry-run"
                dry_run_bool="true"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "🧹 CMSVS Project Cleanup"
    echo "========================"
    
    if [ "$dry_run_bool" = "true" ]; then
        warning "DRY RUN MODE - No files will be actually removed"
    else
        echo "This will permanently remove temporary and development files."
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Cleanup cancelled."
            exit 0
        fi
    fi
    
    echo ""
    
    # Check if Python cleanup script exists
    if [ ! -f "$SCRIPT_DIR/cleanup-project.py" ]; then
        error "Python cleanup script not found: $SCRIPT_DIR/cleanup-project.py"
        exit 1
    fi
    
    # Run cleanup steps
    run_python_cleanup "$dry_run_flag"
    additional_cleanup "$dry_run_bool"
    optimize_files "$dry_run_bool"
    
    echo ""
    show_summary
}

# Run main function
main "$@"
