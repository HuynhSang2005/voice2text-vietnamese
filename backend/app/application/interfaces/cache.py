"""
Application Layer - Cache Interface

This module defines the Protocol interface for caching abstractions.
Implementations can use Redis, Memcached, or in-memory caching.

Following Clean Architecture:
- Application defines WHAT cache should do (interface)
- Infrastructure defines HOW cache works (Redis, in-memory, etc.)
"""

from typing import Protocol, Optional, Any
from datetime import timedelta


class ICache(Protocol):
    """
    Interface for caching operations.
    
    Implementations provide key-value storage with TTL support,
    used for session management, query caching, and temporary data.
    
    Example:
        ```python
        class RedisCache(ICache):
            async def set(
                self, key: str, value: Any, ttl: Optional[timedelta] = None
            ) -> bool:
                serialized = pickle.dumps(value)
                if ttl:
                    await self._redis.setex(key, ttl.total_seconds(), serialized)
                else:
                    await self._redis.set(key, serialized)
                return True
        ```
    """

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache by key.
        
        Args:
            key: Cache key to retrieve
        
        Returns:
            Optional[Any]: Cached value if exists and not expired,
                          None otherwise
        
        Example:
            ```python
            session_data = await cache.get("session:abc123")
            if session_data:
                print(f"Found session: {session_data}")
            else:
                print("Session expired or not found")
            ```
        """
        ...

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Store value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to store (will be serialized)
            ttl: Time-to-live duration (None = no expiration)
        
        Returns:
            bool: True if successfully stored, False otherwise
        
        Raises:
            CacheException: If storage fails
        
        Example:
            ```python
            # Store session for 24 hours
            await cache.set(
                "session:abc123",
                {"user_id": 1, "created_at": datetime.utcnow()},
                ttl=timedelta(hours=24)
            )
            
            # Store permanently
            await cache.set("config:app", {"version": "2.0.0"})
            ```
        """
        ...

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
        
        Returns:
            bool: True if key existed and was deleted, False if not found
        
        Example:
            ```python
            await cache.delete("session:abc123")
            ```
        """
        ...

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
        
        Returns:
            bool: True if key exists and not expired, False otherwise
        
        Example:
            ```python
            if await cache.exists("session:abc123"):
                print("Session is active")
            else:
                print("Session expired")
            ```
        """
        ...

    async def expire(self, key: str, ttl: timedelta) -> bool:
        """
        Set or update TTL for existing key.
        
        Args:
            key: Cache key
            ttl: New time-to-live duration
        
        Returns:
            bool: True if TTL updated, False if key doesn't exist
        
        Example:
            ```python
            # Extend session by 1 hour
            await cache.expire("session:abc123", timedelta(hours=1))
            ```
        """
        ...

    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching pattern.
        
        Args:
            pattern: Key pattern to match (e.g., "session:*")
                    If None, clears entire cache
        
        Returns:
            int: Number of keys deleted
        
        Raises:
            CacheException: If clear operation fails
        
        Example:
            ```python
            # Clear all sessions
            count = await cache.clear("session:*")
            print(f"Cleared {count} sessions")
            
            # Clear entire cache (use with caution!)
            await cache.clear()
            ```
        """
        ...

    async def get_ttl(self, key: str) -> Optional[timedelta]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
        
        Returns:
            Optional[timedelta]: Remaining TTL, or None if key doesn't exist
                                or has no expiration
        
        Example:
            ```python
            ttl = await cache.get_ttl("session:abc123")
            if ttl:
                print(f"Session expires in {ttl.total_seconds()} seconds")
            ```
        """
        ...

    async def ping(self) -> bool:
        """
        Check if cache is responsive.
        
        Returns:
            bool: True if cache is healthy, False otherwise
        
        Example:
            ```python
            if not await cache.ping():
                logger.error("Cache health check failed!")
            ```
        """
        ...


class ICacheFactory(Protocol):
    """
    Factory interface for creating cache instances.
    
    This allows different cache implementations based on configuration,
    useful for testing (in-memory) vs production (Redis).
    
    Example:
        ```python
        class CacheFactory(ICacheFactory):
            def create(self, cache_type: str) -> ICache:
                if cache_type == "redis":
                    return RedisCache(url=settings.REDIS_URL)
                elif cache_type == "memory":
                    return InMemoryCache()
                else:
                    raise ValueError(f"Unknown cache type: {cache_type}")
        ```
    """

    def create(self, **kwargs: Any) -> ICache:
        """
        Create a cache instance.
        
        Args:
            **kwargs: Configuration parameters for the cache
        
        Returns:
            ICache: Cache implementation instance
        
        Example:
            ```python
            factory = CacheFactory()
            cache = factory.create(
                url="redis://localhost:6379/0",
                pool_size=10
            )
            ```
        """
        ...
