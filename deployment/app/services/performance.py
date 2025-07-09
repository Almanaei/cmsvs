"""
Performance monitoring and optimization service for CMSVS Internal System
Provides request timing, database query optimization, and performance metrics
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict, deque
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from app.config import settings
from app.services.cache import cache, cache_stats

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Performance metrics collection and analysis"""
    
    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
        self.slow_queries = deque(maxlen=100)    # Keep last 100 slow queries
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'avg_time': 0
        })
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0
        })
    
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int):
        """Record request performance metrics"""
        timestamp = datetime.utcnow()
        
        # Record in request times
        self.request_times.append({
            'timestamp': timestamp,
            'endpoint': endpoint,
            'method': method,
            'duration': duration,
            'status_code': status_code
        })
        
        # Update endpoint statistics
        key = f"{method} {endpoint}"
        stats = self.endpoint_stats[key]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
        stats['avg_time'] = stats['total_time'] / stats['count']
        
        # Log slow requests
        if duration > 2.0:  # Requests taking more than 2 seconds
            logger.warning(f"Slow request: {method} {endpoint} took {duration:.2f}s")
    
    def record_query(self, query: str, duration: float):
        """Record database query performance"""
        # Normalize query for statistics (remove specific values)
        normalized_query = self._normalize_query(query)
        
        stats = self.query_stats[normalized_query]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['avg_time'] = stats['total_time'] / stats['count']
        
        # Record slow queries
        if duration > 1.0:  # Queries taking more than 1 second
            self.slow_queries.append({
                'timestamp': datetime.utcnow(),
                'query': query,
                'duration': duration
            })
            logger.warning(f"Slow query: {duration:.2f}s - {query[:100]}...")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize SQL query for statistics"""
        # Simple normalization - replace numbers and strings with placeholders
        import re
        normalized = re.sub(r'\d+', '?', query)
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)
        return normalized[:200]  # Limit length
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_minute = now - timedelta(minutes=1)
        
        # Filter recent requests
        recent_requests = [r for r in self.request_times if r['timestamp'] > last_hour]
        last_minute_requests = [r for r in self.request_times if r['timestamp'] > last_minute]
        
        # Calculate statistics
        total_requests = len(self.request_times)
        recent_count = len(recent_requests)
        
        avg_response_time = 0
        if recent_requests:
            avg_response_time = sum(r['duration'] for r in recent_requests) / len(recent_requests)
        
        # Request rate (requests per minute)
        request_rate = len(last_minute_requests)
        
        # Top slow endpoints
        slow_endpoints = sorted(
            [(k, v) for k, v in self.endpoint_stats.items()],
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:5]
        
        # Top slow queries
        slow_queries = sorted(
            [(k, v) for k, v in self.query_stats.items()],
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:5]
        
        return {
            'timestamp': now.isoformat(),
            'requests': {
                'total': total_requests,
                'last_hour': recent_count,
                'rate_per_minute': request_rate,
                'avg_response_time': round(avg_response_time, 3)
            },
            'slow_endpoints': [
                {
                    'endpoint': endpoint,
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 3),
                    'max_time': round(stats['max_time'], 3)
                }
                for endpoint, stats in slow_endpoints
            ],
            'slow_queries': [
                {
                    'query': query[:100] + '...' if len(query) > 100 else query,
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 3)
                }
                for query, stats in slow_queries
            ],
            'cache': cache_stats.get_stats()
        }


# Global performance metrics instance
performance_metrics = PerformanceMetrics()


def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} took {duration:.3f}s")
    return wrapper


def monitor_async_performance(func):
    """Decorator to monitor async function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} took {duration:.3f}s")
    return wrapper


@contextmanager
def performance_timer(operation_name: str):
    """Context manager for timing operations"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.3f}s")


class DatabaseQueryMonitor:
    """Monitor database query performance"""
    
    def __init__(self):
        self.enabled = settings.is_production or settings.debug
        self.slow_query_threshold = 1.0  # seconds
        
    def setup_query_monitoring(self, engine: Engine):
        """Set up SQLAlchemy event listeners for query monitoring"""
        if not self.enabled:
            return
        
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                performance_metrics.record_query(statement, duration)
                
                if duration > self.slow_query_threshold:
                    logger.warning(f"Slow query detected: {duration:.3f}s")
                    logger.debug(f"Query: {statement}")
                    logger.debug(f"Parameters: {parameters}")


# Global database query monitor
db_query_monitor = DatabaseQueryMonitor()


class RequestPerformanceMiddleware:
    """Middleware to monitor request performance"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Wrap send to capture response status
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time
            
            # Record performance metrics
            endpoint = scope.get("path", "unknown")
            method = scope.get("method", "unknown")
            
            performance_metrics.record_request(endpoint, method, duration, status_code)


class PerformanceOptimizer:
    """Performance optimization utilities"""
    
    @staticmethod
    def optimize_database_queries(db: Session):
        """Run database optimization queries"""
        try:
            # Analyze tables for query optimization
            db.execute(text("ANALYZE;"))
            
            # Update table statistics
            db.execute(text("VACUUM ANALYZE;"))
            
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    @staticmethod
    def get_database_performance_stats(db: Session) -> Dict[str, Any]:
        """Get database performance statistics"""
        try:
            # Get slow queries
            slow_queries_result = db.execute(text("""
                SELECT query, calls, total_time, mean_time
                FROM pg_stat_statements
                WHERE mean_time > 1000  -- queries taking more than 1 second on average
                ORDER BY mean_time DESC
                LIMIT 10;
            """)).fetchall()
            
            # Get table sizes
            table_sizes_result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)).fetchall()
            
            # Get index usage
            index_usage_result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC;
            """)).fetchall()
            
            return {
                'slow_queries': [
                    {
                        'query': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                        'calls': row[1],
                        'total_time': row[2],
                        'mean_time': row[3]
                    }
                    for row in slow_queries_result
                ],
                'table_sizes': [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'size': row[2],
                        'size_bytes': row[3]
                    }
                    for row in table_sizes_result
                ],
                'index_usage': [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5]
                    }
                    for row in index_usage_result
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get database performance stats: {e}")
            return {
                'error': str(e),
                'slow_queries': [],
                'table_sizes': [],
                'index_usage': []
            }


# Global performance optimizer
performance_optimizer = PerformanceOptimizer()
