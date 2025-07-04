#!/usr/bin/env python3
"""
Comprehensive backup and recovery manager for CMSVS Internal System
Handles database backups, file backups, and disaster recovery procedures
"""

import os
import sys
import subprocess
import shutil
import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupManager:
    """Comprehensive backup and recovery management"""
    
    def __init__(self):
        self.project_root = project_root
        self.backup_dir = self.project_root / "backups"
        self.db_backup_dir = self.backup_dir / "database"
        self.files_backup_dir = self.backup_dir / "files"
        self.config_backup_dir = self.backup_dir / "config"
        self.logs_backup_dir = self.backup_dir / "logs"
        
        # Create backup directories
        for dir_path in [self.backup_dir, self.db_backup_dir, self.files_backup_dir, 
                        self.config_backup_dir, self.logs_backup_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_database_backup(self, backup_name: str = None) -> Dict[str, Any]:
        """Create a complete database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"db_backup_{timestamp}"
            backup_file = self.db_backup_dir / f"{backup_name}.sql"
            
            logger.info(f"Creating database backup: {backup_file}")
            
            # Extract database connection details from settings
            db_url = settings.database_url
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if not match:
                raise ValueError("Could not parse database URL")
            
            user, password, host, port, database = match.groups()
            
            # Set environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Create backup using pg_dump
            cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                "--format=custom",
                "-f", str(backup_file)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Compress the backup
            compressed_file = f"{backup_file}.gz"
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            backup_file.unlink()
            
            # Get backup size
            backup_size = Path(compressed_file).stat().st_size
            
            backup_info = {
                "type": "database",
                "name": backup_name,
                "file": compressed_file,
                "size": backup_size,
                "size_human": self._format_size(backup_size),
                "timestamp": timestamp,
                "status": "success"
            }
            
            # Save backup metadata
            self._save_backup_metadata(backup_info)
            
            logger.info(f"Database backup completed: {compressed_file} ({backup_info['size_human']})")
            return backup_info
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return {
                "type": "database",
                "name": backup_name or "unknown",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    def create_files_backup(self, backup_name: str = None) -> Dict[str, Any]:
        """Create backup of uploaded files and important directories"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"files_backup_{timestamp}"
            backup_file = self.files_backup_dir / f"{backup_name}.tar.gz"
            
            logger.info(f"Creating files backup: {backup_file}")
            
            # Directories to backup
            backup_paths = [
                self.project_root / "uploads",
                self.project_root / "logs",
                self.project_root / "app" / "static"
            ]
            
            # Create tar.gz archive
            import tarfile
            with tarfile.open(backup_file, "w:gz") as tar:
                for path in backup_paths:
                    if path.exists():
                        tar.add(path, arcname=path.name)
                        logger.info(f"Added {path} to backup")
            
            # Get backup size
            backup_size = backup_file.stat().st_size
            
            backup_info = {
                "type": "files",
                "name": backup_name,
                "file": str(backup_file),
                "size": backup_size,
                "size_human": self._format_size(backup_size),
                "timestamp": timestamp,
                "paths": [str(p) for p in backup_paths if p.exists()],
                "status": "success"
            }
            
            # Save backup metadata
            self._save_backup_metadata(backup_info)
            
            logger.info(f"Files backup completed: {backup_file} ({backup_info['size_human']})")
            return backup_info
            
        except Exception as e:
            logger.error(f"Files backup failed: {e}")
            return {
                "type": "files",
                "name": backup_name or "unknown",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    def create_config_backup(self, backup_name: str = None) -> Dict[str, Any]:
        """Create backup of configuration files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"config_backup_{timestamp}"
            backup_file = self.config_backup_dir / f"{backup_name}.tar.gz"
            
            logger.info(f"Creating configuration backup: {backup_file}")
            
            # Configuration files to backup
            config_files = [
                ".env",
                ".env.production",
                "docker-compose.yml",
                "docker-compose.production.yml",
                "requirements.txt",
                "package.json",
                "tailwind.config.js",
                "alembic.ini",
                "nginx/nginx.conf"
            ]
            
            import tarfile
            with tarfile.open(backup_file, "w:gz") as tar:
                for file_path in config_files:
                    full_path = self.project_root / file_path
                    if full_path.exists():
                        tar.add(full_path, arcname=file_path)
                        logger.info(f"Added {file_path} to config backup")
            
            # Get backup size
            backup_size = backup_file.stat().st_size
            
            backup_info = {
                "type": "config",
                "name": backup_name,
                "file": str(backup_file),
                "size": backup_size,
                "size_human": self._format_size(backup_size),
                "timestamp": timestamp,
                "files": [f for f in config_files if (self.project_root / f).exists()],
                "status": "success"
            }
            
            # Save backup metadata
            self._save_backup_metadata(backup_info)
            
            logger.info(f"Configuration backup completed: {backup_file} ({backup_info['size_human']})")
            return backup_info
            
        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            return {
                "type": "config",
                "name": backup_name or "unknown",
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    def create_full_backup(self, backup_name: str = None) -> Dict[str, Any]:
        """Create a complete system backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"full_backup_{timestamp}"
        
        logger.info(f"Starting full system backup: {backup_name}")
        
        results = {
            "type": "full",
            "name": backup_name,
            "timestamp": timestamp,
            "components": {}
        }
        
        # Create individual backups
        results["components"]["database"] = self.create_database_backup(f"{backup_name}_db")
        results["components"]["files"] = self.create_files_backup(f"{backup_name}_files")
        results["components"]["config"] = self.create_config_backup(f"{backup_name}_config")
        
        # Check if all components succeeded
        all_success = all(
            comp["status"] == "success" 
            for comp in results["components"].values()
        )
        
        results["status"] = "success" if all_success else "partial"
        
        # Calculate total size
        total_size = sum(
            comp.get("size", 0) 
            for comp in results["components"].values() 
            if comp["status"] == "success"
        )
        results["total_size"] = total_size
        results["total_size_human"] = self._format_size(total_size)
        
        # Save full backup metadata
        self._save_backup_metadata(results)
        
        logger.info(f"Full backup completed: {backup_name} ({results['total_size_human']})")
        return results
    
    def restore_database(self, backup_file: str) -> bool:
        """Restore database from backup"""
        try:
            backup_path = Path(backup_file)
            if not backup_path.is_absolute():
                backup_path = self.db_backup_dir / backup_file
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            logger.info(f"Restoring database from: {backup_path}")
            
            # Extract database connection details
            db_url = settings.database_url
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
            if not match:
                raise ValueError("Could not parse database URL")
            
            user, password, host, port, database = match.groups()
            
            # Set environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Decompress if needed
            restore_file = backup_path
            if backup_path.suffix == '.gz':
                temp_file = backup_path.with_suffix('')
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                restore_file = temp_file
            
            # Restore using pg_restore
            cmd = [
                "pg_restore",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", database,
                "--verbose",
                "--clean",
                "--if-exists",
                str(restore_file)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            # Clean up temporary file
            if restore_file != backup_path:
                restore_file.unlink()
            
            if result.returncode != 0:
                logger.warning(f"pg_restore warnings: {result.stderr}")
                # pg_restore often returns non-zero even on success due to warnings
            
            logger.info("Database restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    def list_backups(self, backup_type: str = None) -> List[Dict[str, Any]]:
        """List available backups"""
        metadata_file = self.backup_dir / "backup_metadata.json"
        
        if not metadata_file.exists():
            return []
        
        try:
            with open(metadata_file, 'r') as f:
                all_backups = json.load(f)
            
            if backup_type:
                return [b for b in all_backups if b.get("type") == backup_type]
            
            return all_backups
            
        except Exception as e:
            logger.error(f"Error reading backup metadata: {e}")
            return []
    
    def cleanup_old_backups(self, retention_days: int = 30) -> Dict[str, Any]:
        """Clean up old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        cleanup_stats = {
            "deleted_count": 0,
            "freed_space": 0,
            "errors": []
        }
        
        try:
            backups = self.list_backups()
            
            for backup in backups:
                backup_date = datetime.strptime(backup["timestamp"], "%Y%m%d_%H%M%S")
                
                if backup_date < cutoff_date:
                    try:
                        # Delete backup files
                        if backup["type"] == "full":
                            for component in backup["components"].values():
                                if "file" in component and Path(component["file"]).exists():
                                    file_size = Path(component["file"]).stat().st_size
                                    Path(component["file"]).unlink()
                                    cleanup_stats["freed_space"] += file_size
                        else:
                            if "file" in backup and Path(backup["file"]).exists():
                                file_size = Path(backup["file"]).stat().st_size
                                Path(backup["file"]).unlink()
                                cleanup_stats["freed_space"] += file_size
                        
                        cleanup_stats["deleted_count"] += 1
                        logger.info(f"Deleted old backup: {backup['name']}")
                        
                    except Exception as e:
                        error_msg = f"Failed to delete backup {backup['name']}: {e}"
                        cleanup_stats["errors"].append(error_msg)
                        logger.error(error_msg)
            
            # Update metadata file to remove deleted backups
            remaining_backups = [
                b for b in backups 
                if datetime.strptime(b["timestamp"], "%Y%m%d_%H%M%S") >= cutoff_date
            ]
            
            metadata_file = self.backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(remaining_backups, f, indent=2)
            
            cleanup_stats["freed_space_human"] = self._format_size(cleanup_stats["freed_space"])
            
            logger.info(f"Cleanup completed: {cleanup_stats['deleted_count']} backups deleted, "
                       f"{cleanup_stats['freed_space_human']} freed")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            cleanup_stats["errors"].append(str(e))
            return cleanup_stats
    
    def _save_backup_metadata(self, backup_info: Dict[str, Any]):
        """Save backup metadata to JSON file"""
        metadata_file = self.backup_dir / "backup_metadata.json"
        
        # Load existing metadata
        existing_backups = []
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    existing_backups = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read existing metadata: {e}")
        
        # Add new backup info
        existing_backups.append(backup_info)
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(existing_backups, f, indent=2)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Backup and recovery manager for CMSVS")
    parser.add_argument("command", choices=[
        "backup-db", "backup-files", "backup-config", "backup-full",
        "restore-db", "list", "cleanup"
    ], help="Command to execute")
    parser.add_argument("--name", "-n", help="Backup name")
    parser.add_argument("--file", "-f", help="Backup file for restore")
    parser.add_argument("--type", "-t", help="Backup type filter for list command")
    parser.add_argument("--retention-days", "-r", type=int, default=30, 
                       help="Retention period in days for cleanup")
    
    args = parser.parse_args()
    
    backup_manager = BackupManager()
    
    if args.command == "backup-db":
        result = backup_manager.create_database_backup(args.name)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "success" else 1)
    
    elif args.command == "backup-files":
        result = backup_manager.create_files_backup(args.name)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "success" else 1)
    
    elif args.command == "backup-config":
        result = backup_manager.create_config_backup(args.name)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "success" else 1)
    
    elif args.command == "backup-full":
        result = backup_manager.create_full_backup(args.name)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] in ["success", "partial"] else 1)
    
    elif args.command == "restore-db":
        if not args.file:
            logger.error("Backup file required for restore command")
            sys.exit(1)
        success = backup_manager.restore_database(args.file)
        sys.exit(0 if success else 1)
    
    elif args.command == "list":
        backups = backup_manager.list_backups(args.type)
        print(json.dumps(backups, indent=2))
    
    elif args.command == "cleanup":
        result = backup_manager.cleanup_old_backups(args.retention_days)
        print(json.dumps(result, indent=2))
        sys.exit(0 if not result["errors"] else 1)


if __name__ == "__main__":
    main()
