"""
Infrastructure Cache Module

Redis cache implementation for production use.
"""

from app.infrastructure.cache.redis_cache import RedisCache, create_redis_cache

__all__ = [
    "RedisCache",
    "create_redis_cache",
]
