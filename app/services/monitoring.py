"""
Monitoring and metrics service for CMSVS Internal System
Provides application metrics, health checks, and performance monitoring
"""

import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.config import settings
from app.models.user import User
from app.models.request import Request

logger = logging.getLogger(__name__)


class SystemMetrics:
    """System-level metrics collection"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get basic system information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                    "used": psutil.virtual_memory().used
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                },
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """Get current process information"""
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms,
                    "percent": process.memory_percent()
                },
                "num_threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "status": process.status()
            }
        except Exception as e:
            logger.error(f"Error collecting process metrics: {e}")
            return {"error": str(e)}


class DatabaseMetrics:
    """Database-level metrics collection"""
    
    @staticmethod
    def get_connection_info() -> Dict[str, Any]:
        """Get database connection pool information"""
        try:
            pool = engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
        except Exception as e:
            logger.error(f"Error collecting database connection metrics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_database_stats(db: Session) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = {}
            
            # Table row counts
            stats["tables"] = {
                "users": db.query(User).count(),
                "requests": db.query(Request).count()
            }
            
            # Database size
            try:
                result = db.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                           pg_database_size(current_database()) as size_bytes
                """)).fetchone()
                if result:
                    stats["database_size"] = {
                        "formatted": result[0],
                        "bytes": result[1]
                    }
            except Exception as e:
                logger.warning(f"Could not get database size: {e}")
            
            # Active connections
            try:
                result = db.execute(text("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)).fetchone()
                if result:
                    stats["active_connections"] = result[0]
            except Exception as e:
                logger.warning(f"Could not get active connections: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error collecting database stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def check_database_health(db: Session) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            
            # Simple query to test connectivity
            db.execute(text("SELECT 1"))
            
            query_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": round(query_time * 1000, 2),  # milliseconds
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class ApplicationMetrics:
    """Application-level metrics collection"""
    
    @staticmethod
    def get_application_stats(db: Session) -> Dict[str, Any]:
        """Get application-specific statistics"""
        try:
            now = datetime.utcnow()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            stats = {
                "users": {
                    "total": db.query(User).count(),
                    "active": db.query(User).filter(User.is_active == True).count(),
                    "admins": db.query(User).filter(User.role == "admin").count()
                },
                "requests": {
                    "total": db.query(Request).count(),
                    "today": db.query(Request).filter(
                        Request.created_at >= today
                    ).count(),
                    "this_week": db.query(Request).filter(
                        Request.created_at >= week_ago
                    ).count(),
                    "this_month": db.query(Request).filter(
                        Request.created_at >= month_ago
                    ).count()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error collecting application stats: {e}")
            return {"error": str(e)}


class HealthChecker:
    """Comprehensive health checking service"""
    
    def __init__(self):
        self.checks = {
            "database": self._check_database,
            "disk_space": self._check_disk_space,
            "memory": self._check_memory,
            "cpu": self._check_cpu
        }
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        db = SessionLocal()
        try:
            result = DatabaseMetrics.check_database_health(db)
            return {
                "status": "pass" if result["status"] == "healthy" else "fail",
                "details": result
            }
        finally:
            db.close()
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space availability"""
        try:
            disk_usage = psutil.disk_usage('/')
            percent_used = (disk_usage.used / disk_usage.total) * 100
            
            if percent_used > 90:
                status = "fail"
                message = f"Disk usage critical: {percent_used:.1f}%"
            elif percent_used > 80:
                status = "warn"
                message = f"Disk usage high: {percent_used:.1f}%"
            else:
                status = "pass"
                message = f"Disk usage normal: {percent_used:.1f}%"
            
            return {
                "status": status,
                "details": {
                    "percent_used": round(percent_used, 1),
                    "free_bytes": disk_usage.free,
                    "total_bytes": disk_usage.total,
                    "message": message
                }
            }
        except Exception as e:
            return {
                "status": "fail",
                "details": {"error": str(e)}
            }
    
    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            if percent_used > 90:
                status = "fail"
                message = f"Memory usage critical: {percent_used:.1f}%"
            elif percent_used > 80:
                status = "warn"
                message = f"Memory usage high: {percent_used:.1f}%"
            else:
                status = "pass"
                message = f"Memory usage normal: {percent_used:.1f}%"
            
            return {
                "status": status,
                "details": {
                    "percent_used": percent_used,
                    "available_bytes": memory.available,
                    "total_bytes": memory.total,
                    "message": message
                }
            }
        except Exception as e:
            return {
                "status": "fail",
                "details": {"error": str(e)}
            }
    
    def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = "fail"
                message = f"CPU usage critical: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = "warn"
                message = f"CPU usage high: {cpu_percent:.1f}%"
            else:
                status = "pass"
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return {
                "status": status,
                "details": {
                    "percent_used": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "message": message
                }
            }
        except Exception as e:
            return {
                "status": "fail",
                "details": {"error": str(e)}
            }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = "pass"
        
        for check_name, check_func in self.checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                # Update overall status
                if result["status"] == "fail":
                    overall_status = "fail"
                elif result["status"] == "warn" and overall_status == "pass":
                    overall_status = "warn"
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results[check_name] = {
                    "status": "fail",
                    "details": {"error": str(e)}
                }
                overall_status = "fail"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }


# Global instances
health_checker = HealthChecker()


def get_comprehensive_metrics() -> Dict[str, Any]:
    """Get all metrics in one call"""
    db = SessionLocal()
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": SystemMetrics.get_system_info(),
            "process": SystemMetrics.get_process_info(),
            "database": {
                "connections": DatabaseMetrics.get_connection_info(),
                "stats": DatabaseMetrics.get_database_stats(db),
                "health": DatabaseMetrics.check_database_health(db)
            },
            "application": ApplicationMetrics.get_application_stats(db),
            "health": health_checker.run_all_checks()
        }
    finally:
        db.close()
