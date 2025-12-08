"""
Redis Cache Implementation - Infrastructure Layer

Production-ready Redis cache with:
- Async connection pooling
- Automatic serialization (pickle/JSON)
- TTL support with configurable defaults
- Batch operations (get_many, set_many, delete_many)
- Connection health checks
- Graceful error handling

Dependencies:
- redis[asyncio] >= 5.0.0 (provides redis.asyncio module)
"""

import pickle
import json
import logging
from typing import Optional, Any, List

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from app.application.interfaces.cache import (
    CacheException,
    CacheConnectionError,
    CacheSerializationError,
)


logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based cache implementation with async support.

    Features:
    - Async/await interface for FastAPI integration
    - Connection pooling for efficiency
    - Automatic serialization (pickle for complex objects, JSON for simple types)
    - TTL support with default and per-key expiration
    - Batch operations for performance
    - Health checks via ping()
    - Graceful error handling with detailed logging

    Configuration:
    - url: Redis connection URL (redis://localhost:6379/0)
    - pool_size: Max connections in pool (default: 10)
    - default_ttl: Default expiration in seconds (None = no expiration)
    - serializer: "pickle" or "json" (default: "pickle" for flexibility)
    - decode_responses: False for binary safety

    Example:
        >>> cache = RedisCache(
        ...     url="redis://localhost:6379/0",
        ...     pool_size=20,
        ...     default_ttl=3600  # 1 hour
        ... )
        >>> await cache.set("user:1000", {"name": "Alice"})
        >>> user = await cache.get("user:1000")
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        pool_size: int = 10,
        default_ttl: Optional[int] = None,
        serializer: str = "pickle",
        decode_responses: bool = False,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
    ):
        """
        Initialize Redis cache with connection pool.

        Args:
            url: Redis connection URL (redis://host:port/db)
            pool_size: Maximum connections in pool
            default_ttl: Default expiration in seconds (None = permanent)
            serializer: Serialization method ("pickle" or "json")
            decode_responses: Decode bytes to strings (False for binary safety)
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Retry on timeout errors
            health_check_interval: Seconds between health checks

        Raises:
            ValueError: If serializer is not "pickle" or "json"
        """
        if serializer not in ("pickle", "json"):
            raise ValueError(
                f"Serializer must be 'pickle' or 'json', got: {serializer}"
            )

        self._url = url
        self._pool_size = pool_size
        self._default_ttl = default_ttl
        self._serializer = serializer
        self._decode_responses = decode_responses

        # Create connection pool
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
        self._is_connected = False

        # Connection config
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._retry_on_timeout = retry_on_timeout
        self._health_check_interval = health_check_interval

        logger.info(
            f"RedisCache initialized: url={url}, pool_size={pool_size}, "
            f"default_ttl={default_ttl}, serializer={serializer}"
        )

    async def connect(self) -> None:
        """
        Establish connection pool to Redis.

        This should be called during app startup (lifespan).
        Creates connection pool and validates connection with ping.

        Raises:
            CacheConnectionError: If connection fails

        Example:
            >>> cache = RedisCache()
            >>> await cache.connect()  # Call in lifespan startup
        """
        if self._is_connected:
            logger.warning("RedisCache already connected")
            return

        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                self._url,
                max_connections=self._pool_size,
                decode_responses=self._decode_responses,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                retry_on_timeout=self._retry_on_timeout,
                health_check_interval=self._health_check_interval,
            )

            # Create Redis client from pool
            self._redis = aioredis.Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()
            self._is_connected = True

            logger.info(f"RedisCache connected successfully: {self._url}")

        except RedisConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheConnectionError(f"Redis connection failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            raise CacheConnectionError(f"Redis connection error: {e}") from e

    async def disconnect(self) -> None:
        """
        Close Redis connection pool.

        This should be called during app shutdown (lifespan).
        Closes all connections and cleans up resources.

        Example:
            >>> await cache.disconnect()  # Call in lifespan shutdown
        """
        if not self._is_connected:
            logger.warning("RedisCache not connected, nothing to disconnect")
            return

        try:
            if self._redis:
                await self._redis.aclose()
            if self._pool:
                await self._pool.aclose()

            self._is_connected = False
            logger.info("RedisCache disconnected successfully")

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")
            raise CacheException(f"Redis disconnect error: {e}") from e

    def _serialize(self, value: Any) -> bytes:
        """
        Serialize value to bytes.

        Args:
            value: Python object to serialize

        Returns:
            bytes: Serialized value

        Raises:
            CacheSerializationError: If serialization fails
        """
        try:
            if self._serializer == "pickle":
                return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            else:  # json
                # JSON requires encoding to bytes
                return json.dumps(value).encode("utf-8")
        except (pickle.PicklingError, TypeError, ValueError) as e:
            logger.error(f"Serialization failed for value type {type(value)}: {e}")
            raise CacheSerializationError(f"Failed to serialize value: {e}") from e

    def _deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes to Python object.

        Args:
            data: Serialized bytes

        Returns:
            Any: Deserialized Python object

        Raises:
            CacheSerializationError: If deserialization fails
        """
        try:
            if self._serializer == "pickle":
                return pickle.loads(data)
            else:  # json
                return json.loads(data.decode("utf-8"))
        except (pickle.UnpicklingError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Deserialization failed: {e}")
            raise CacheSerializationError(f"Failed to deserialize data: {e}") from e

    def _ensure_connected(self) -> None:
        """
        Ensure Redis connection is active.

        Raises:
            CacheConnectionError: If not connected
        """
        if not self._is_connected or self._redis is None:
            raise CacheConnectionError(
                "RedisCache not connected. Call connect() first."
            )

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None otherwise

        Raises:
            CacheConnectionError: If not connected
            CacheSerializationError: If deserialization fails

        Example:
            >>> user = await cache.get("user:1000")
            >>> if user is None:
            ...     user = await db.fetch_user(1000)
            ...     await cache.set("user:1000", user, ttl=300)
        """
        self._ensure_connected()

        try:
            data = await self._redis.get(key)  # type: ignore
            if data is None:
                return None
            return self._deserialize(data)

        except RedisError as e:
            logger.error(f"Redis error getting key '{key}': {e}")
            raise CacheException(f"Failed to get key '{key}': {e}") from e

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Expiration in seconds (None = use default_ttl)

        Returns:
            True if set successfully

        Raises:
            CacheConnectionError: If not connected
            CacheSerializationError: If serialization fails

        Example:
            >>> await cache.set("session:abc", {"user_id": 1000}, ttl=3600)
            >>> await cache.set("config:app", {"debug": False})  # Permanent
        """
        self._ensure_connected()

        try:
            serialized = self._serialize(value)

            # Use provided TTL, fallback to default, or no expiration
            expiration = ttl if ttl is not None else self._default_ttl

            if expiration:
                await self._redis.setex(key, expiration, serialized)  # type: ignore
            else:
                await self._redis.set(key, serialized)  # type: ignore

            return True

        except RedisError as e:
            logger.error(f"Redis error setting key '{key}': {e}")
            raise CacheException(f"Failed to set key '{key}': {e}") from e

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key existed and was deleted, False otherwise

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> deleted = await cache.delete("session:abc123")
            >>> if deleted:
            ...     print("Session invalidated")
        """
        self._ensure_connected()

        try:
            result = await self._redis.delete(key)  # type: ignore
            return result > 0  # Redis returns count of deleted keys

        except RedisError as e:
            logger.error(f"Redis error deleting key '{key}': {e}")
            raise CacheException(f"Failed to delete key '{key}': {e}") from e

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> if await cache.exists("lock:resource"):
            ...     print("Resource is locked")
        """
        self._ensure_connected()

        try:
            result = await self._redis.exists(key)  # type: ignore
            return result > 0

        except RedisError as e:
            logger.error(f"Redis error checking existence of key '{key}': {e}")
            raise CacheException(f"Failed to check key '{key}': {e}") from e

    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Key pattern (Redis glob: *, ?, [abc])
                    None = clear all keys (FLUSHDB)

        Returns:
            Number of keys deleted

        Raises:
            CacheConnectionError: If not connected

        Warning:
            Expensive operation for large datasets. Use with caution.

        Example:
            >>> await cache.clear("session:*")  # Clear all sessions
            >>> await cache.clear()  # Clear entire database
        """
        self._ensure_connected()

        try:
            if pattern is None:
                # Clear entire database
                await self._redis.flushdb()  # type: ignore
                logger.warning("RedisCache: FLUSHDB executed (entire cache cleared)")
                return -1  # Unknown count

            # Find keys matching pattern
            keys = []
            async for key in self._redis.scan_iter(match=pattern):  # type: ignore
                keys.append(key)

            if not keys:
                return 0

            # Delete matched keys
            count = await self._redis.delete(*keys)  # type: ignore
            logger.info(
                f"RedisCache: Cleared {count} keys matching pattern '{pattern}'"
            )
            return count

        except RedisError as e:
            logger.error(f"Redis error clearing pattern '{pattern}': {e}")
            raise CacheException(f"Failed to clear pattern '{pattern}': {e}") from e

    async def get_many(self, keys: List[str]) -> List[Optional[Any]]:
        """
        Retrieve multiple values in a single operation.

        Args:
            keys: List of cache keys

        Returns:
            List of values in same order (None for missing keys)

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> keys = ["user:1000", "user:1001", "user:1002"]
            >>> users = await cache.get_many(keys)
            >>> for key, user in zip(keys, users):
            ...     if user:
            ...         print(f"{key}: {user['name']}")
        """
        self._ensure_connected()

        if not keys:
            return []

        try:
            # MGET returns list of values (None for missing keys)
            values = await self._redis.mget(keys)  # type: ignore

            # Deserialize non-None values
            results = []
            for value in values:
                if value is None:
                    results.append(None)
                else:
                    try:
                        results.append(self._deserialize(value))
                    except CacheSerializationError:
                        results.append(None)  # Treat deserialization errors as missing

            return results

        except RedisError as e:
            logger.error(f"Redis error getting multiple keys: {e}")
            raise CacheException(f"Failed to get multiple keys: {e}") from e

    async def set_many(
        self, mapping: dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        Store multiple key-value pairs in a single operation.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Expiration in seconds (applied to all keys)

        Returns:
            True if all keys set successfully

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> users = {
            ...     "user:1000": {"name": "Alice"},
            ...     "user:1001": {"name": "Bob"},
            ... }
            >>> await cache.set_many(users, ttl=3600)
        """
        self._ensure_connected()

        if not mapping:
            return True

        try:
            # Serialize all values
            serialized_mapping = {
                key: self._serialize(value) for key, value in mapping.items()
            }

            # Use pipeline for efficiency
            async with self._redis.pipeline(transaction=True) as pipe:  # type: ignore
                # MSET for all keys
                await pipe.mset(serialized_mapping)

                # Set TTL for each key if specified
                expiration = ttl if ttl is not None else self._default_ttl
                if expiration:
                    for key in serialized_mapping.keys():
                        await pipe.expire(key, expiration)

                await pipe.execute()

            return True

        except RedisError as e:
            logger.error(f"Redis error setting multiple keys: {e}")
            raise CacheException(f"Failed to set multiple keys: {e}") from e

    async def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys in a single operation.

        Args:
            keys: List of cache keys to delete

        Returns:
            Number of keys that were deleted

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> keys = ["session:abc", "session:def", "session:ghi"]
            >>> count = await cache.delete_many(keys)
            >>> print(f"Deleted {count} sessions")
        """
        self._ensure_connected()

        if not keys:
            return 0

        try:
            count = await self._redis.delete(*keys)  # type: ignore
            return count

        except RedisError as e:
            logger.error(f"Redis error deleting multiple keys: {e}")
            raise CacheException(f"Failed to delete multiple keys: {e}") from e

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment numeric value atomically.

        Args:
            key: Cache key (must be integer)
            amount: Amount to increment (can be negative)

        Returns:
            New value after increment

        Raises:
            CacheConnectionError: If not connected
            ValueError: If key exists but value is not an integer

        Example:
            >>> await cache.set("counter:requests", 0)
            >>> await cache.increment("counter:requests")  # Returns 1
            >>> await cache.increment("counter:requests", 10)  # Returns 11
        """
        self._ensure_connected()

        try:
            if amount == 1:
                result = await self._redis.incr(key)  # type: ignore
            else:
                result = await self._redis.incrby(key, amount)  # type: ignore
            return result

        except RedisError as e:
            logger.error(f"Redis error incrementing key '{key}': {e}")
            raise CacheException(f"Failed to increment key '{key}': {e}") from e

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, None if key doesn't exist,
            -1 if key exists but has no expiration

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> ttl = await cache.get_ttl("session:abc123")
            >>> if ttl and ttl < 300:
            ...     await cache.expire("session:abc123", 3600)  # Extend
        """
        self._ensure_connected()

        try:
            ttl = await self._redis.ttl(key)  # type: ignore
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but no expiration
                return -1
            else:
                return ttl

        except RedisError as e:
            logger.error(f"Redis error getting TTL for key '{key}': {e}")
            raise CacheException(f"Failed to get TTL for key '{key}': {e}") from e

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if expiration was set, False if key doesn't exist

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> await cache.set("lock:resource", "locked")
            >>> await cache.expire("lock:resource", 30)  # Expire in 30s
        """
        self._ensure_connected()

        try:
            result = await self._redis.expire(key, ttl)  # type: ignore
            return bool(result)

        except RedisError as e:
            logger.error(f"Redis error setting expiration for key '{key}': {e}")
            raise CacheException(
                f"Failed to set expiration for key '{key}': {e}"
            ) from e

    async def persist(self, key: str) -> bool:
        """
        Remove expiration from key (make permanent).

        Args:
            key: Cache key

        Returns:
            True if expiration removed, False if key doesn't exist
            or has no expiration

        Raises:
            CacheConnectionError: If not connected

        Example:
            >>> await cache.set("temp:data", value, ttl=300)
            >>> await cache.persist("temp:data")  # Remove expiration
        """
        self._ensure_connected()

        try:
            result = await self._redis.persist(key)  # type: ignore
            return bool(result)

        except RedisError as e:
            logger.error(f"Redis error persisting key '{key}': {e}")
            raise CacheException(f"Failed to persist key '{key}': {e}") from e

    async def ping(self) -> bool:
        """
        Check if Redis is responsive.

        Returns:
            True if Redis is healthy, False otherwise

        Example:
            >>> if not await cache.ping():
            ...     logger.error("Cache health check failed!")
        """
        if not self._is_connected or self._redis is None:
            return False

        try:
            await self._redis.ping()  # type: ignore
            return True
        except RedisError:
            return False


# Convenience factory function
def create_redis_cache(
    url: str = "redis://localhost:6379/0",
    pool_size: int = 10,
    default_ttl: Optional[int] = None,
    serializer: str = "pickle",
) -> RedisCache:
    """
    Factory function to create RedisCache instance.

    Args:
        url: Redis connection URL
        pool_size: Maximum connections in pool
        default_ttl: Default expiration in seconds
        serializer: "pickle" or "json"

    Returns:
        RedisCache instance (not connected yet)

    Example:
        >>> cache = create_redis_cache(
        ...     url="redis://localhost:6379/0",
        ...     pool_size=20,
        ...     default_ttl=3600
        ... )
        >>> await cache.connect()
    """
    return RedisCache(
        url=url,
        pool_size=pool_size,
        default_ttl=default_ttl,
        serializer=serializer,
    )
