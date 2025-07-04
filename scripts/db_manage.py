#!/usr/bin/env python3
"""
Database management script for CMSVS Internal System
Provides database initialization, migration, and maintenance commands
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import create_tables, SessionLocal, engine
from app.config import settings
from app.services.user_service import UserService
from app.models.user import UserRole
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database management utilities"""
    
    def __init__(self):
        self.project_root = project_root
    
    def init_database(self, create_admin: bool = True) -> bool:
        """Initialize database with tables and default data"""
        try:
            logger.info("Creating database tables...")
            create_tables()
            logger.info("Database tables created successfully")
            
            if create_admin:
                self.create_admin_user()
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def create_admin_user(self) -> bool:
        """Create default admin user"""
        try:
            db = SessionLocal()
            try:
                # Check if admin user already exists
                admin_user = UserService.get_user_by_email(db, settings.admin_email)
                if admin_user:
                    logger.info(f"Admin user already exists: {admin_user.username}")
                    return True
                
                # Create admin user
                admin_user = UserService.create_user(
                    db=db,
                    username="admin",
                    email=settings.admin_email,
                    full_name="System Administrator",
                    password=settings.admin_password,
                    role=UserRole.ADMIN
                )
                
                logger.info(f"Admin user created successfully: {admin_user.username}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            return False
    
    def run_migrations(self, message: str = None) -> bool:
        """Run database migrations using Alembic"""
        try:
            # Generate migration if message provided
            if message:
                logger.info(f"Generating migration: {message}")
                cmd = [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message]
                result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Error generating migration: {result.stderr}")
                    return False
                
                logger.info("Migration generated successfully")
            
            # Apply migrations
            logger.info("Applying database migrations...")
            cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error applying migrations: {result.stderr}")
                return False
            
            logger.info("Migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            return False
    
    def check_database_connection(self) -> bool:
        """Check database connectivity"""
        try:
            db = SessionLocal()
            try:
                # Simple query to test connection
                db.execute("SELECT 1")
                logger.info("Database connection successful")
                return True
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_migration_status(self) -> bool:
        """Get current migration status"""
        try:
            cmd = [sys.executable, "-m", "alembic", "current"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error getting migration status: {result.stderr}")
                return False
            
            logger.info(f"Current migration: {result.stdout.strip()}")
            
            # Check for pending migrations
            cmd = [sys.executable, "-m", "alembic", "heads"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Latest migration: {result.stdout.strip()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
    
    def backup_database(self, backup_file: str = None) -> bool:
        """Create database backup"""
        try:
            if not backup_file:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"backup_{timestamp}.sql"
            
            backup_path = self.project_root / "backups" / backup_file
            backup_path.parent.mkdir(exist_ok=True)
            
            # Extract database connection details
            db_url = settings.database_url
            # Parse postgresql://user:password@host:port/database
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if not match:
                logger.error("Could not parse database URL")
                return False
            
            user, password, host, port, database = match.groups()
            
            # Set environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Run pg_dump
            cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "--clean",
                "--no-owner",
                "--no-privileges",
                "-f", str(backup_path)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error creating backup: {result.stderr}")
                return False
            
            logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return False
    
    def restore_database(self, backup_file: str) -> bool:
        """Restore database from backup"""
        try:
            backup_path = self.project_root / "backups" / backup_file
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Extract database connection details
            db_url = settings.database_url
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if not match:
                logger.error("Could not parse database URL")
                return False
            
            user, password, host, port, database = match.groups()
            
            # Set environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Run psql to restore
            cmd = [
                "psql",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "-f", str(backup_path)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error restoring backup: {result.stderr}")
                return False
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Database management for CMSVS")
    parser.add_argument("command", choices=[
        "init", "migrate", "status", "backup", "restore", "check", "create-admin"
    ], help="Command to execute")
    parser.add_argument("--message", "-m", help="Migration message")
    parser.add_argument("--file", "-f", help="Backup/restore file name")
    parser.add_argument("--no-admin", action="store_true", help="Skip admin user creation")
    
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    
    if args.command == "init":
        success = db_manager.init_database(create_admin=not args.no_admin)
        sys.exit(0 if success else 1)
    
    elif args.command == "migrate":
        success = db_manager.run_migrations(args.message)
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        success = db_manager.get_migration_status()
        sys.exit(0 if success else 1)
    
    elif args.command == "backup":
        success = db_manager.backup_database(args.file)
        sys.exit(0 if success else 1)
    
    elif args.command == "restore":
        if not args.file:
            logger.error("Backup file required for restore command")
            sys.exit(1)
        success = db_manager.restore_database(args.file)
        sys.exit(0 if success else 1)
    
    elif args.command == "check":
        success = db_manager.check_database_connection()
        sys.exit(0 if success else 1)
    
    elif args.command == "create-admin":
        success = db_manager.create_admin_user()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
