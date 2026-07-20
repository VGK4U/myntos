"""
Redis Configuration and Utilities
High-performance caching for Reference System binary tree and income calculations
"""

import json
import redis.asyncio as redis
from typing import Any, Optional, Union
from functools import wraps
import hashlib
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize Redis connection pool"""
    global redis_pool, redis_client
    
    import os
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        logger.info("Redis not configured (REDIS_URL not set). Caching disabled - app will work normally.")
        redis_client = None
        return
    
    try:
        # Create connection pool
        redis_pool = redis.ConnectionPool(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connection
        await redis_client.ping()
        logger.info("✅ Redis caching enabled")
        
    except Exception as e:
        logger.info(f"Redis unavailable - caching disabled (app continues normally)")
        redis_client = None

async def close_redis():
    """Close Redis connections"""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()

def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client instance"""
    return redis_client

class RedisCache:
    """Redis caching utilities for Reference System operations"""
    
    def __init__(self):
        self.default_ttl = 300  # 5 minutes default TTL
        self.prefix = "reference:"
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        # Create a deterministic key from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        return f"{self.prefix}{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not redis_client:
            return None
        
        try:
            value = await redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not redis_client:
            return False
        
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        if not redis_client:
            return 0
        
        try:
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE PATTERN error: {e}")
            return 0
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user"""
        patterns = [
            f"{self.prefix}team_tree:{user_id}:*",
            f"{self.prefix}team_counts:{user_id}:*", 
            f"{self.prefix}income:{user_id}:*",
            f"{self.prefix}dashboard:{user_id}:*"
        ]
        
        for pattern in patterns:
            await self.delete_pattern(pattern)

# Global cache instance
cache = RedisCache()

def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache MISS for {cache_key}")
            result = await func(*args, **kwargs) if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else func(*args, **kwargs)
            
            # Cache the result
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def cached_sync(prefix: str, ttl: Optional[int] = None):
    """
    Decorator for caching synchronous function results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # For sync functions, we need to handle caching differently
            # Generate cache key
            cache_key = cache._generate_cache_key(prefix, *args, **kwargs)
            
            # Execute function (sync functions don't support async caching in this simple implementation)
            # For now, just execute the function - we can enhance this later with background caching
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Cache key generators for common MLM operations
class CacheKeys:
    """Standardized cache keys for Reference System operations"""
    
    @staticmethod
    def team_tree(user_id: str, levels: int) -> str:
        return f"mlm:team_tree:{user_id}:{levels}"
    
    @staticmethod
    def team_counts(user_id: str) -> str:
        return f"mlm:team_counts:{user_id}"
    
    @staticmethod
    def income_summary(user_id: str, month: str) -> str:
        return f"mlm:income:{user_id}:{month}"
    
    @staticmethod
    def user_dashboard(user_id: str) -> str:
        return f"mlm:dashboard:{user_id}"
    
    @staticmethod
    def placement_path(user_id: str) -> str:
        return f"mlm:placement:{user_id}"
    
    @staticmethod
    def award_progress(user_id: str) -> str:
        return f"mlm:awards:{user_id}"

# Cache TTL configurations (in seconds)
class CacheTTL:
    TEAM_TREE = 600       # 10 minutes - moderate changes
    TEAM_COUNTS = 300     # 5 minutes - changes frequently 
    INCOME_SUMMARY = 1800 # 30 minutes - stable within a day
    USER_DASHBOARD = 300  # 5 minutes - mixed data
    PLACEMENT_PATH = 3600 # 1 hour - rarely changes
    AWARD_PROGRESS = 600  # 10 minutes - moderate changes