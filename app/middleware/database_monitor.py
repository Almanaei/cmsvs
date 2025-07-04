"""
Database Connection Pool Monitoring Middleware
Monitors database connection pool health and prevents timeout issues
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import get_pool_status, engine

logger = logging.getLogger(__name__)


class DatabaseMonitorMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor database connection pool"""
    
    def __init__(self, app, log_interval: int = 100):
        super().__init__(app)
        self.request_count = 0
        self.log_interval = log_interval
        self.warning_threshold = 0.8  # Warn when 80% of connections are used
        self.critical_threshold = 0.9  # Critical when 90% of connections are used
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor database connections for each request"""
        start_time = time.time()

        # Get pool status before request (with error handling)
        try:
            pool_status_before = get_pool_status()
        except Exception as e:
            logger.error(f"Failed to get pool status before request: {e}")
            pool_status_before = {"error": str(e)}

        # Log pool status periodically
        self.request_count += 1
        if self.request_count % self.log_interval == 0:
            self._log_pool_status(pool_status_before, "periodic")

        # Check for potential issues (only if we have valid status)
        if "error" not in pool_status_before:
            self._check_pool_health(pool_status_before)
        
        try:
            # Process the request
            response = await call_next(request)

            # Get pool status after request (with error handling)
            try:
                pool_status_after = get_pool_status()
            except Exception as e:
                logger.error(f"Failed to get pool status after request: {e}")
                pool_status_after = {"error": str(e)}

            # Log if there's a significant change (only if both statuses are valid)
            if ("error" not in pool_status_before and
                "error" not in pool_status_after and
                self._significant_change(pool_status_before, pool_status_after)):
                self._log_pool_status(pool_status_after, "after_request")

            # Add pool status to response headers (for debugging)
            if hasattr(response, 'headers') and "error" not in pool_status_after:
                response.headers["X-DB-Pool-Available"] = str(pool_status_after.get("available_connections", 0))
                response.headers["X-DB-Pool-Total"] = str(pool_status_after.get("total_connections", 0))

            return response
            
        except Exception as e:
            # Log pool status on error
            pool_status_error = get_pool_status()
            self._log_pool_status(pool_status_error, "error")
            logger.error(f"Request failed with database error: {e}")
            raise
        
        finally:
            # Log slow requests that might indicate connection issues
            duration = time.time() - start_time
            if duration > 5.0:  # Requests taking more than 5 seconds
                pool_status_final = get_pool_status()
                logger.warning(
                    f"Slow request detected: {duration:.2f}s, "
                    f"Pool status: {pool_status_final}"
                )
    
    def _log_pool_status(self, pool_status: dict, context: str):
        """Log current pool status"""
        logger.info(
            f"DB Pool Status ({context}): "
            f"Available: {pool_status['available_connections']}, "
            f"Total: {pool_status['total_connections']}, "
            f"Checked out: {pool_status['checked_out']}, "
            f"Overflow: {pool_status['overflow']}"
        )
    
    def _check_pool_health(self, pool_status: dict):
        """Check pool health and log warnings"""
        try:
            # Skip if we have an error status
            if "error" in pool_status:
                logger.error(f"Cannot check pool health due to error: {pool_status['error']}")
                return

            pool_size = pool_status.get("pool_size", 0)
            overflow = pool_status.get("overflow", 0)
            max_overflow = pool_status.get("max_overflow", 0)

            # Use max_overflow if overflow is 0 but max_overflow is set
            if overflow == 0 and max_overflow > 0:
                total_capacity = pool_size + max_overflow
            else:
                total_capacity = pool_size + overflow

            total_connections = pool_status.get("total_connections", 0)
            available_connections = pool_status.get("available_connections", 0)

            usage_ratio = total_connections / total_capacity if total_capacity > 0 else 0

            if usage_ratio >= self.critical_threshold:
                logger.critical(
                    f"CRITICAL: Database pool usage at {usage_ratio:.1%}! "
                    f"Available: {available_connections}, "
                    f"Total capacity: {total_capacity}"
                )
            elif usage_ratio >= self.warning_threshold:
                logger.warning(
                    f"WARNING: Database pool usage at {usage_ratio:.1%}. "
                    f"Available: {available_connections}, "
                    f"Total capacity: {total_capacity}"
                )
        except Exception as e:
            logger.error(f"Error checking pool health: {e}")
    
    def _significant_change(self, before: dict, after: dict) -> bool:
        """Check if there's a significant change in pool status"""
        try:
            # Skip if either status has an error
            if "error" in before or "error" in after:
                return False

            before_available = before.get("available_connections", 0)
            after_available = after.get("available_connections", 0)

            # Consider it significant if available connections changed by more than 2
            return abs(before_available - after_available) > 2
        except Exception as e:
            logger.error(f"Error checking significant change: {e}")
            return False


class DatabaseHealthChecker:
    """Utility class for database health checks"""
    
    @staticmethod
    def get_health_status() -> dict:
        """Get comprehensive database health status"""
        try:
            pool_status = get_pool_status()

            # Check if we have an error in pool status
            if "error" in pool_status:
                return {
                    "status": "error",
                    "error": pool_status["error"],
                    "recommendations": ["Check database connectivity", "Restart application if needed"]
                }

            # Calculate health metrics
            pool_size = pool_status.get("pool_size", 0)
            overflow = pool_status.get("overflow", 0)
            max_overflow = pool_status.get("max_overflow", 0)
            total_connections = pool_status.get("total_connections", 0)

            # Use max_overflow if overflow is 0 but max_overflow is set
            if overflow == 0 and max_overflow > 0:
                total_capacity = pool_size + max_overflow
            else:
                total_capacity = pool_size + overflow

            usage_ratio = total_connections / total_capacity if total_capacity > 0 else 0
            
            # Determine health status
            if usage_ratio >= 0.9:
                health = "critical"
            elif usage_ratio >= 0.8:
                health = "warning"
            elif usage_ratio >= 0.6:
                health = "caution"
            else:
                health = "healthy"
            
            return {
                "status": health,
                "usage_ratio": round(usage_ratio, 2),
                "available_connections": pool_status.get("available_connections", 0),
                "total_connections": pool_status.get("total_connections", 0),
                "total_capacity": total_capacity,
                "pool_details": pool_status,
                "recommendations": DatabaseHealthChecker._get_recommendations(health, pool_status)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "recommendations": ["Check database connectivity", "Restart application if needed"]
            }
    
    @staticmethod
    def _get_recommendations(health: str, pool_status: dict) -> list:
        """Get recommendations based on health status"""
        recommendations = []
        
        if health == "critical":
            recommendations.extend([
                "Immediate action required: Database pool exhausted",
                "Check for long-running queries or transactions",
                "Consider increasing pool_size and max_overflow",
                "Review application for connection leaks"
            ])
        elif health == "warning":
            recommendations.extend([
                "Monitor closely: High database pool usage",
                "Check for slow queries",
                "Consider optimizing database operations"
            ])
        elif health == "caution":
            recommendations.extend([
                "Moderate usage: Monitor trends",
                "Ensure proper connection cleanup"
            ])
        else:
            recommendations.append("Database pool is healthy")
        
        # Check for specific issues
        overflow = pool_status.get("overflow", 0)
        if overflow > 0:
            recommendations.append("Overflow connections in use - consider increasing base pool_size")

        # Note: removed invalid check as QueuePool doesn't have invalid() method
        
        return recommendations


# Utility functions for manual monitoring
def log_current_pool_status():
    """Manually log current pool status"""
    try:
        status = get_pool_status()
        logger.info(f"Manual pool check: {status}")
        return status
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        return None


def force_pool_cleanup():
    """Force cleanup of database connections"""
    try:
        logger.info("Forcing database pool cleanup...")
        engine.dispose()
        logger.info("Database pool cleanup completed")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup pool: {e}")
        return False


# Health check endpoint helper
async def database_health_endpoint():
    """Health check endpoint for database"""
    health_checker = DatabaseHealthChecker()
    health_status = health_checker.get_health_status()
    
    # Return appropriate HTTP status based on health
    if health_status["status"] == "error":
        status_code = 503  # Service Unavailable
    elif health_status["status"] == "critical":
        status_code = 503  # Service Unavailable
    elif health_status["status"] == "warning":
        status_code = 200  # OK but with warnings
    else:
        status_code = 200  # OK
    
    return health_status, status_code
