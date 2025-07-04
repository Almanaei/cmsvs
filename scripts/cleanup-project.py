#!/usr/bin/env python3
"""
Project cleanup script for CMSVS Internal System
Removes temporary files, test files, and unnecessary documentation
while preserving essential production files
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Set
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ProjectCleaner:
    """Clean up project directory for production deployment"""
    
    def __init__(self, project_root: Path, dry_run: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.removed_files = []
        self.removed_dirs = []
        self.preserved_files = []
        
    def get_files_to_remove(self) -> List[Path]:
        """Get list of files that should be removed"""
        files_to_remove = []
        
        # Temporary and test files patterns
        temp_patterns = [
            # Version files
            "=2.0.0", "=3.1.0",
            
            # Development documentation (keep only essential ones)
            "ADD_FILES_FUNCTIONALITY_COMPLETE.md",
            "DROPDOWN_SCROLL_PREVENTION_FIX.md", 
            "EDIT_REQUEST_DROPDOWN_IMPLEMENTATION.md",
            "FILE_AUTO_NAMING_FIX.md",
            "FILE_UPLOAD_CLICK_FIX.md",
            "FILE_UPLOAD_FIX_DOCUMENTATION.md",
            "FILE_UPLOAD_IMPROVEMENTS.md",
            "JAVASCRIPT_SYNTAX_FIX.md",
            "PRODUCTION_FILE_NAMING_SYSTEM.md",
            "TAILWIND_SETUP.md",
            "UI_FILENAME_DISPLAY_FIX.md",
            
            # Temporary HTML files
            "bento_origin.html",
            "feed_origin.html", 
            "stats_origin.html",
            "user_table_new.html",
            "user_table_origin.html",
            
            # Temporary Python files
            "add_avatar_column.py",
            "migrate_avatar.py",
            "setup_achievements.py",
            "initialize_achievements.py",
            
            # Log files
            "production_file_naming_test.log",
            
            # Temporary files
            "cookies.txt",
        ]
        
        # Add files that match patterns
        for pattern in temp_patterns:
            file_path = self.project_root / pattern
            if file_path.exists():
                files_to_remove.append(file_path)
        
        return files_to_remove
    
    def get_directories_to_remove(self) -> List[Path]:
        """Get list of directories that should be removed"""
        dirs_to_remove = []
        
        # Directories to remove
        temp_dirs = [
            "docs",  # Development documentation
            "tests", # Test files (keep production test in scripts)
            "logs",  # Log files (will be recreated)
        ]
        
        for dir_name in temp_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                dirs_to_remove.append(dir_path)
        
        return dirs_to_remove
    
    def get_cache_directories_to_remove(self) -> List[Path]:
        """Get cache directories to remove"""
        cache_dirs = []
        
        # Python cache directories
        for root, dirs, files in os.walk(self.project_root):
            for dir_name in dirs:
                if dir_name in ['__pycache__', '.pytest_cache', '.mypy_cache']:
                    cache_dirs.append(Path(root) / dir_name)
        
        return cache_dirs
    
    def should_preserve_file(self, file_path: Path) -> bool:
        """Check if a file should be preserved"""
        
        # Essential production files to always keep
        essential_files = {
            # Core application
            "README.md",
            "INSTALLATION.md", 
            "SYSTEM_OVERVIEW.md",
            "PRODUCTION_DEPLOYMENT.md",
            "DISASTER_RECOVERY.md",
            "PRODUCTION_READY_SUMMARY.md",
            
            # Configuration
            ".env",
            ".env.example", 
            ".env.production",
            "requirements.txt",
            "package.json",
            "package-lock.json",
            "tailwind.config.js",
            "alembic.ini",
            
            # Docker
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.production.yml",
            
            # Scripts
            "run.py",
            "deploy.py",
            "health_check.py",
            "init_db.py",
        }
        
        # Essential directories to preserve
        essential_dirs = {
            "app", "scripts", "nginx", "alembic", "uploads", "src", "node_modules"
        }
        
        # Check if it's an essential file
        if file_path.name in essential_files:
            return True
            
        # Check if it's in an essential directory
        try:
            relative_path = file_path.relative_to(self.project_root)
            if relative_path.parts[0] in essential_dirs:
                return True
        except ValueError:
            pass
            
        return False
    
    def clean_node_modules(self):
        """Clean up node_modules if needed"""
        node_modules = self.project_root / "node_modules"
        
        if node_modules.exists():
            logger.info("Node modules directory found")
            
            # In production, we might want to keep node_modules for CSS building
            # But remove development-only packages if needed
            dev_packages = [
                "stats.html",  # This seems to be a stray file
            ]
            
            for package in dev_packages:
                package_path = node_modules / package
                if package_path.exists():
                    if self.dry_run:
                        logger.info(f"Would remove: {package_path}")
                    else:
                        if package_path.is_file():
                            package_path.unlink()
                        else:
                            shutil.rmtree(package_path)
                        logger.info(f"Removed: {package_path}")
                        self.removed_files.append(package_path)
    
    def clean_uploads_directory(self):
        """Clean up uploads directory - remove test uploads but keep structure"""
        uploads_dir = self.project_root / "uploads"
        
        if uploads_dir.exists():
            # Keep avatars directory but clean test request directories
            for item in uploads_dir.iterdir():
                if item.is_dir() and item.name.startswith("request_"):
                    # These are test uploads, remove them
                    if self.dry_run:
                        logger.info(f"Would remove test upload directory: {item}")
                    else:
                        shutil.rmtree(item)
                        logger.info(f"Removed test upload directory: {item}")
                        self.removed_dirs.append(item)
    
    def create_production_gitignore(self):
        """Create or update .gitignore for production"""
        gitignore_path = self.project_root / ".gitignore"
        
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Environment files
.env.local
.env.development
.env.test

# Secrets
secrets/
*.key
*.crt
*.pem

# Backups
backups/
*.sql
*.sql.gz

# Uploads (in production, you might want to backup these separately)
uploads/request_*/

# Node modules (uncomment if you want to exclude)
# node_modules/

# Build outputs
app/static/css/output.css

# Test results
test-results/
coverage/
.coverage
htmlcov/

# Temporary files
*.tmp
*.temp
*.bak
"""
        
        if self.dry_run:
            logger.info(f"Would create/update: {gitignore_path}")
        else:
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            logger.info(f"Created/updated: {gitignore_path}")
    
    def cleanup(self):
        """Perform the cleanup"""
        logger.info(f"Starting cleanup of {self.project_root}")
        logger.info(f"Dry run: {self.dry_run}")
        
        # Remove individual files
        files_to_remove = self.get_files_to_remove()
        for file_path in files_to_remove:
            if self.dry_run:
                logger.info(f"Would remove file: {file_path}")
            else:
                file_path.unlink()
                logger.info(f"Removed file: {file_path}")
                self.removed_files.append(file_path)
        
        # Remove directories
        dirs_to_remove = self.get_directories_to_remove()
        for dir_path in dirs_to_remove:
            if self.dry_run:
                logger.info(f"Would remove directory: {dir_path}")
            else:
                shutil.rmtree(dir_path)
                logger.info(f"Removed directory: {dir_path}")
                self.removed_dirs.append(dir_path)
        
        # Remove cache directories
        cache_dirs = self.get_cache_directories_to_remove()
        for cache_dir in cache_dirs:
            if self.dry_run:
                logger.info(f"Would remove cache directory: {cache_dir}")
            else:
                shutil.rmtree(cache_dir)
                logger.info(f"Removed cache directory: {cache_dir}")
                self.removed_dirs.append(cache_dir)
        
        # Clean node_modules
        self.clean_node_modules()
        
        # Clean uploads directory
        self.clean_uploads_directory()
        
        # Create production .gitignore
        self.create_production_gitignore()
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*50)
        logger.info(f"Files removed: {len(self.removed_files)}")
        logger.info(f"Directories removed: {len(self.removed_dirs)}")
        
        if self.dry_run:
            logger.info("\nThis was a dry run. No files were actually removed.")
            logger.info("Run without --dry-run to perform actual cleanup.")
        else:
            logger.info("\nCleanup completed successfully!")
            logger.info("Your project is now clean and ready for production.")
        
        # Show what's left
        logger.info("\nRemaining important files:")
        important_files = [
            "README.md", "PRODUCTION_DEPLOYMENT.md", "DISASTER_RECOVERY.md",
            "requirements.txt", "Dockerfile", "docker-compose.production.yml",
            "deploy.py", "run.py"
        ]
        
        for file_name in important_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                logger.info(f"  ✅ {file_name}")
            else:
                logger.warning(f"  ❌ {file_name} (missing)")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Clean up CMSVS project for production")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be removed without actually removing")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="Project root directory (default: current directory)")
    
    args = parser.parse_args()
    
    # Confirm if not dry run
    if not args.dry_run:
        response = input("This will permanently remove files. Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cleanup cancelled.")
            return
    
    # Perform cleanup
    cleaner = ProjectCleaner(args.project_root, args.dry_run)
    cleaner.cleanup()


if __name__ == "__main__":
    main()
