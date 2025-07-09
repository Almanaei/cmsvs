"""
Caching service for CMSVS Internal System
Provides Redis-based caching with fallback to in-memory caching
"""

import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires_at'] > datetime.utcnow():
                return entry['value']
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds"""
        try:
            # Remove oldest entries if cache is full
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k]['created_at'])
                del self._cache[oldest_key]
            
            self._cache[key] = {
                'value': value,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        self._cache.clear()
        return True
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


class RedisCache:
    """Redis-based cache implementation"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            if REDIS_AVAILABLE:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                self._client.ping()
                logger.info("Connected to Redis cache")
            else:
                logger.warning("Redis not available, falling back to in-memory cache")
                self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._client:
            return None
        
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in Redis cache with TTL in seconds"""
        if not self._client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            return self._client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self._client:
            return False
        
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        if not self._client:
            return False
        
        try:
            return self._client.flushdb()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def size(self) -> int:
        """Get current cache size"""
        if not self._client:
            return 0
        
        try:
            return self._client.dbsize()
        except Exception as e:
            logger.error(f"Error getting cache size: {e}")
            return 0


class CacheManager:
    """Main cache manager with fallback support"""
    
    def __init__(self):
        self.redis_cache = None
        self.memory_cache = InMemoryCache()
        
        # Try to initialize Redis cache
        if settings.is_production:
            try:
                redis_url = getattr(settings, 'redis_url', 'redis://redis:6379/0')
                self.redis_cache = RedisCache(redis_url)
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
    
    def _get_cache(self):
        """Get the appropriate cache backend"""
        return self.redis_cache if self.redis_cache else self.memory_cache
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        return self._get_cache().get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache"""
        return self._get_cache().set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return self._get_cache().delete(key)
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        return self._get_cache().clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return self._get_cache().size()
    
    def generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()


# Global cache instance
cache = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{cache.generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        
        # Add cache management methods to the wrapped function
        wrapper.cache_clear = lambda: cache.delete(f"{key_prefix}:{func.__name__}:*")
        wrapper.cache_info = lambda: {"cache_size": cache.size()}
        
        return wrapper
    return decorator


def cached_async(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching async function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{cache.generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        
        # Add cache management methods to the wrapped function
        wrapper.cache_clear = lambda: cache.delete(f"{key_prefix}:{func.__name__}:*")
        wrapper.cache_info = lambda: {"cache_size": cache.size()}
        
        return wrapper
    return decorator


class QueryCache:
    """Database query result caching"""
    
    @staticmethod
    def cache_query_result(query_key: str, result: Any, ttl: int = 300):
        """Cache database query result"""
        cache.set(f"query:{query_key}", result, ttl)
    
    @staticmethod
    def get_cached_query_result(query_key: str) -> Optional[Any]:
        """Get cached database query result"""
        return cache.get(f"query:{query_key}")
    
    @staticmethod
    def invalidate_query_cache(pattern: str):
        """Invalidate cached queries matching pattern"""
        # This would need to be implemented based on the cache backend
        # For now, we'll just clear all query cache
        cache.delete("query:*")


# Cache statistics and monitoring
class CacheStats:
    """Cache statistics collection"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def record_set(self):
        self.sets += 1
    
    def record_delete(self):
        self.deletes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "cache_size": cache.size()
        }
    
    def reset(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0


# Global cache statistics
cache_stats = CacheStats()
