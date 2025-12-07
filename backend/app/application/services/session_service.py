"""
Session management service for application layer.

This service provides session-related utilities including:
- Session ID generation (UUID)
- Session validation and expiry checking
- Cache integration for session data
- Session metadata management
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.application.interfaces.cache import ICache
from app.domain.exceptions import ValidationException, BusinessRuleViolationException


class SessionService:
    """
    Service for session management.
    
    This service handles creation, validation, and lifecycle management
    of user sessions. It integrates with cache for session storage and
    supports TTL-based expiry.
    
    Use Cases:
    - Create new transcription sessions
    - Validate session existence and expiry
    - Store session metadata (user preferences, settings)
    - Clean up expired sessions
    
    Example:
        ```python
        # With cache
        service = SessionService(cache=redis_cache, default_ttl_minutes=30)
        
        # Create session
        session_id, metadata = await service.create_session(
            user_id="user123",
            metadata={"language": "vi", "model": "zipformer"}
        )
        
        # Validate session
        is_valid = await service.validate_session(session_id)
        if not is_valid:
            raise BusinessRuleViolationException(...)
        
        # Get session data
        data = await service.get_session_data(session_id)
        ```
    """
    
    # Default configuration
    DEFAULT_TTL_MINUTES = 30
    SESSION_KEY_PREFIX = "session:"
    
    def __init__(
        self,
        cache: Optional[ICache] = None,
        default_ttl_minutes: int = DEFAULT_TTL_MINUTES,
        require_validation: bool = False
    ):
        """
        Initialize session service.
        
        Args:
            cache: Optional cache for session storage
            default_ttl_minutes: Default session TTL in minutes
            require_validation: Whether to require validation before use
        """
        if default_ttl_minutes <= 0:
            raise ValidationException(
                field="default_ttl_minutes",
                value=default_ttl_minutes,
                constraint="must be positive"
            )
        
        self._cache = cache
        self._default_ttl_seconds = default_ttl_minutes * 60
        self._require_validation = require_validation
    
    def generate_session_id(self) -> str:
        """
        Generate a unique session ID using UUID4.
        
        Returns:
            UUID4 string as session ID
            
        Example:
            ```python
            session_id = service.generate_session_id()
            # "550e8400-e29b-41d4-a716-446655440000"
            ```
        """
        return str(uuid.uuid4())
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Create a new session with optional metadata.
        
        Generates a unique session ID and stores session data in cache
        (if available). Returns session ID and full session metadata.
        
        Args:
            user_id: Optional user identifier
            metadata: Optional session metadata
            ttl_seconds: Optional TTL override (uses default if None)
            
        Returns:
            Tuple of (session_id, session_data)
            
        Example:
            ```python
            session_id, data = await service.create_session(
                user_id="user123",
                metadata={"language": "vi", "model": "zipformer"}
            )
            # session_id: "550e8400-..."
            # data: {
            #     "session_id": "550e8400-...",
            #     "user_id": "user123",
            #     "created_at": "2025-12-07T...",
            #     "expires_at": "2025-12-07T...",
            #     "metadata": {"language": "vi", ...}
            # }
            ```
        """
        # Generate session ID
        session_id = self.generate_session_id()
        
        # Calculate expiry
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(seconds=ttl)
        
        # Build session data
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": metadata or {}
        }
        
        # Store in cache if available
        if self._cache is not None:
            cache_key = self._get_cache_key(session_id)
            await self._cache.set(cache_key, session_data, ttl=ttl)
        
        return session_id, session_data
    
    async def validate_session(self, session_id: str) -> bool:
        """
        Validate that session exists and is not expired.
        
        Returns True if session is valid (exists in cache and not expired),
        False otherwise. If cache is not configured, returns True (assumes valid).
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            bool: True if session is valid, False otherwise
            
        Example:
            ```python
            is_valid = await service.validate_session(session_id)
            if not is_valid:
                raise BusinessRuleViolationException(
                    rule="session_must_be_valid",
                    reason="Session expired or not found"
                )
            ```
        """
        # If no cache, assume valid (sessions not tracked)
        if self._cache is None:
            return True
        
        # Check cache for session
        cache_key = self._get_cache_key(session_id)
        session_data = await self._cache.get(cache_key)
        
        if session_data is None:
            return False
        
        # Check expiry
        expires_at_str = session_data.get("expires_at")
        if expires_at_str is None:
            return False
        
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.now(timezone.utc)
        
        return now < expires_at
    
    async def validate_session_or_raise(self, session_id: str) -> None:
        """
        Validate session and raise exception if invalid.
        
        Args:
            session_id: Session ID to validate
            
        Raises:
            BusinessRuleViolationException: If session is invalid
            
        Example:
            ```python
            try:
                await service.validate_session_or_raise(session_id)
                # Proceed with operation
            except BusinessRuleViolationException:
                # Handle invalid session
                pass
            ```
        """
        is_valid = await self.validate_session(session_id)
        if not is_valid:
            raise BusinessRuleViolationException(
                rule="session_must_be_valid",
                reason=f"Session {session_id} is expired or does not exist"
            )
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from cache.
        
        Returns session data if exists, None otherwise.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session data dictionary or None
            
        Example:
            ```python
            data = await service.get_session_data(session_id)
            if data:
                user_id = data.get("user_id")
                metadata = data.get("metadata", {})
            ```
        """
        if self._cache is None:
            return None
        
        cache_key = self._get_cache_key(session_id)
        return await self._cache.get(cache_key)
    
    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """
        Update session metadata in cache.
        
        Updates the metadata field of session data. Optionally extends
        the TTL to keep session alive.
        
        Args:
            session_id: Session ID to update
            metadata: New metadata (will be merged with existing)
            extend_ttl: Whether to extend TTL (default: True)
            
        Returns:
            bool: True if update successful, False otherwise
            
        Example:
            ```python
            success = await service.update_session_metadata(
                session_id,
                metadata={"transcription_count": 5},
                extend_ttl=True
            )
            ```
        """
        if self._cache is None:
            return False
        
        # Get current session data
        session_data = await self.get_session_data(session_id)
        if session_data is None:
            return False
        
        # Update metadata
        current_metadata = session_data.get("metadata", {})
        current_metadata.update(metadata)
        session_data["metadata"] = current_metadata
        
        # Store updated data
        cache_key = self._get_cache_key(session_id)
        ttl = self._default_ttl_seconds if extend_ttl else None
        await self._cache.set(cache_key, session_data, ttl=ttl)
        
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from cache.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
            
        Example:
            ```python
            deleted = await service.delete_session(session_id)
            if deleted:
                print("Session terminated")
            ```
        """
        if self._cache is None:
            return False
        
        cache_key = self._get_cache_key(session_id)
        return await self._cache.delete(cache_key)
    
    async def extend_session(
        self,
        session_id: str,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Extend session TTL.
        
        Resets the expiry time for a session, effectively extending its lifetime.
        
        Args:
            session_id: Session ID to extend
            ttl_seconds: New TTL in seconds (uses default if None)
            
        Returns:
            bool: True if extension successful, False otherwise
            
        Example:
            ```python
            # Extend by default TTL
            extended = await service.extend_session(session_id)
            
            # Extend by custom duration
            extended = await service.extend_session(session_id, ttl_seconds=1800)
            ```
        """
        if self._cache is None:
            return False
        
        # Get current session data
        session_data = await self.get_session_data(session_id)
        if session_data is None:
            return False
        
        # Update expiry
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        session_data["expires_at"] = new_expires_at.isoformat()
        
        # Store updated data with new TTL
        cache_key = self._get_cache_key(session_id)
        await self._cache.set(cache_key, session_data, ttl=ttl)
        
        return True
    
    def is_cache_enabled(self) -> bool:
        """
        Check if cache is configured.
        
        Returns:
            bool: True if cache is available, False otherwise
        """
        return self._cache is not None
    
    def get_default_ttl_seconds(self) -> int:
        """
        Get default session TTL in seconds.
        
        Returns:
            int: Default TTL in seconds
        """
        return self._default_ttl_seconds
    
    def _get_cache_key(self, session_id: str) -> str:
        """
        Build cache key for session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            str: Cache key with prefix
        """
        return f"{self.SESSION_KEY_PREFIX}{session_id}"
