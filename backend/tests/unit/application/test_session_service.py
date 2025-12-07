"""
Unit tests for SessionService.

Tests cover:
- Constructor validation
- Session ID generation
- Session creation with/without cache
- Session validation
- Session data retrieval
- Metadata updates
- Session deletion and extension
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

from app.application.services.session_service import SessionService
from app.domain.exceptions import ValidationException, BusinessRuleViolationException


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cache():
    """Create mock cache."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def session_service_no_cache():
    """Create session service without cache."""
    return SessionService()


@pytest.fixture
def session_service_with_cache(mock_cache):
    """Create session service with cache."""
    return SessionService(cache=mock_cache, default_ttl_minutes=30)


# ============================================================================
# Constructor Tests
# ============================================================================

class TestSessionServiceConstructor:
    """Test SessionService constructor validation."""
    
    def test_constructor_with_defaults(self):
        """Should create service with default values."""
        service = SessionService()
        assert service.get_default_ttl_seconds() == 1800  # 30 minutes
        assert service.is_cache_enabled() is False
    
    def test_constructor_with_cache(self, mock_cache):
        """Should create service with cache."""
        service = SessionService(cache=mock_cache, default_ttl_minutes=60)
        assert service.get_default_ttl_seconds() == 3600  # 60 minutes
        assert service.is_cache_enabled() is True
    
    def test_constructor_with_invalid_ttl(self):
        """Should raise ValidationException for invalid TTL."""
        with pytest.raises(ValidationException) as exc_info:
            SessionService(default_ttl_minutes=-1)
        
        assert exc_info.value.field == "default_ttl_minutes"
        assert "must be positive" in exc_info.value.constraint


# ============================================================================
# Session ID Generation Tests
# ============================================================================

class TestSessionIdGeneration:
    """Test session ID generation."""
    
    def test_generate_session_id(self, session_service_no_cache):
        """Should generate valid UUID4."""
        session_id = session_service_no_cache.generate_session_id()
        
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID4 format: "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
        assert session_id.count('-') == 4
    
    def test_generate_unique_session_ids(self, session_service_no_cache):
        """Should generate unique IDs."""
        id1 = session_service_no_cache.generate_session_id()
        id2 = session_service_no_cache.generate_session_id()
        
        assert id1 != id2


# ============================================================================
# Session Creation Tests
# ============================================================================

class TestSessionCreation:
    """Test session creation."""
    
    @pytest.mark.asyncio
    async def test_create_session_basic(self, session_service_no_cache):
        """Should create session with generated ID."""
        session_id, data = await session_service_no_cache.create_session()
        
        assert isinstance(session_id, str)
        assert data["session_id"] == session_id
        assert data["user_id"] is None
        assert "created_at" in data
        assert "expires_at" in data
        assert data["metadata"] == {}
    
    @pytest.mark.asyncio
    async def test_create_session_with_user_id(self, session_service_no_cache):
        """Should create session with user ID."""
        session_id, data = await session_service_no_cache.create_session(
            user_id="user123"
        )
        
        assert data["user_id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, session_service_no_cache):
        """Should create session with metadata."""
        metadata = {"language": "vi", "model": "zipformer"}
        session_id, data = await session_service_no_cache.create_session(
            metadata=metadata
        )
        
        assert data["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_create_session_with_custom_ttl(self, session_service_no_cache):
        """Should create session with custom TTL."""
        session_id, data = await session_service_no_cache.create_session(
            ttl_seconds=3600
        )
        
        created_at = datetime.fromisoformat(data["created_at"])
        expires_at = datetime.fromisoformat(data["expires_at"])
        
        diff = (expires_at - created_at).total_seconds()
        assert 3599 <= diff <= 3601  # ~3600 seconds
    
    @pytest.mark.asyncio
    async def test_create_session_stores_in_cache(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should store session in cache."""
        session_id, data = await session_service_with_cache.create_session(
            user_id="user123"
        )
        
        # Verify cache.set was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        
        assert call_args[0][0] == f"session:{session_id}"  # cache key
        assert call_args[0][1]["session_id"] == session_id  # session data
        assert call_args[1]["ttl"] == 1800  # default TTL


# ============================================================================
# Session Validation Tests
# ============================================================================

class TestSessionValidation:
    """Test session validation."""
    
    @pytest.mark.asyncio
    async def test_validate_session_without_cache(self, session_service_no_cache):
        """Should return True when no cache (sessions not tracked)."""
        is_valid = await session_service_no_cache.validate_session("any-id")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_existing_valid_session(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return True for existing valid session."""
        # Mock cache to return valid session data
        future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_cache.get.return_value = {
            "session_id": "test-id",
            "expires_at": future_time.isoformat()
        }
        
        is_valid = await session_service_with_cache.validate_session("test-id")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_session(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return False for nonexistent session."""
        mock_cache.get.return_value = None
        
        is_valid = await session_service_with_cache.validate_session("nonexistent")
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_expired_session(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return False for expired session."""
        # Mock cache to return expired session
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_cache.get.return_value = {
            "session_id": "expired-id",
            "expires_at": past_time.isoformat()
        }
        
        is_valid = await session_service_with_cache.validate_session("expired-id")
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_session_or_raise_with_valid(
        self,
        session_service_no_cache
    ):
        """Should not raise for valid session."""
        # Should not raise (no cache = always valid)
        await session_service_no_cache.validate_session_or_raise("any-id")
    
    @pytest.mark.asyncio
    async def test_validate_session_or_raise_with_invalid(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should raise BusinessRuleViolationException for invalid session."""
        mock_cache.get.return_value = None
        
        with pytest.raises(BusinessRuleViolationException) as exc_info:
            await session_service_with_cache.validate_session_or_raise("invalid")
        
        assert exc_info.value.rule == "session_must_be_valid"


# ============================================================================
# Session Data Retrieval Tests
# ============================================================================

class TestSessionDataRetrieval:
    """Test getting session data."""
    
    @pytest.mark.asyncio
    async def test_get_session_data_without_cache(self, session_service_no_cache):
        """Should return None when no cache."""
        data = await session_service_no_cache.get_session_data("any-id")
        assert data is None
    
    @pytest.mark.asyncio
    async def test_get_session_data_existing(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return session data from cache."""
        expected_data = {
            "session_id": "test-id",
            "user_id": "user123",
            "metadata": {"key": "value"}
        }
        mock_cache.get.return_value = expected_data
        
        data = await session_service_with_cache.get_session_data("test-id")
        assert data == expected_data
    
    @pytest.mark.asyncio
    async def test_get_session_data_nonexistent(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return None for nonexistent session."""
        mock_cache.get.return_value = None
        
        data = await session_service_with_cache.get_session_data("nonexistent")
        assert data is None


# ============================================================================
# Session Update Tests
# ============================================================================

class TestSessionUpdate:
    """Test updating session metadata."""
    
    @pytest.mark.asyncio
    async def test_update_session_metadata(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should update session metadata in cache."""
        # Mock existing session
        mock_cache.get.return_value = {
            "session_id": "test-id",
            "metadata": {"count": 1}
        }
        
        success = await session_service_with_cache.update_session_metadata(
            "test-id",
            metadata={"count": 2, "new_key": "value"}
        )
        
        assert success is True
        mock_cache.set.assert_called_once()
        
        # Verify merged metadata
        call_args = mock_cache.set.call_args
        updated_data = call_args[0][1]
        assert updated_data["metadata"]["count"] == 2
        assert updated_data["metadata"]["new_key"] == "value"
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_session(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return False when updating nonexistent session."""
        mock_cache.get.return_value = None
        
        success = await session_service_with_cache.update_session_metadata(
            "nonexistent",
            metadata={"key": "value"}
        )
        
        assert success is False


# ============================================================================
# Session Deletion Tests
# ============================================================================

class TestSessionDeletion:
    """Test session deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_service_with_cache, mock_cache):
        """Should delete session from cache."""
        mock_cache.delete.return_value = True
        
        deleted = await session_service_with_cache.delete_session("test-id")
        
        assert deleted is True
        mock_cache.delete.assert_called_once_with("session:test-id")
    
    @pytest.mark.asyncio
    async def test_delete_session_without_cache(self, session_service_no_cache):
        """Should return False when no cache."""
        deleted = await session_service_no_cache.delete_session("any-id")
        assert deleted is False


# ============================================================================
# Session Extension Tests
# ============================================================================

class TestSessionExtension:
    """Test session TTL extension."""
    
    @pytest.mark.asyncio
    async def test_extend_session_default_ttl(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should extend session with default TTL."""
        mock_cache.get.return_value = {
            "session_id": "test-id",
            "expires_at": "2025-12-07T10:00:00+00:00"
        }
        
        extended = await session_service_with_cache.extend_session("test-id")
        
        assert extended is True
        mock_cache.set.assert_called_once()
        
        # Verify TTL was set
        call_args = mock_cache.set.call_args
        assert call_args[1]["ttl"] == 1800  # default TTL
    
    @pytest.mark.asyncio
    async def test_extend_session_custom_ttl(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should extend session with custom TTL."""
        mock_cache.get.return_value = {
            "session_id": "test-id",
            "expires_at": "2025-12-07T10:00:00+00:00"
        }
        
        extended = await session_service_with_cache.extend_session(
            "test-id",
            ttl_seconds=3600
        )
        
        assert extended is True
        
        # Verify custom TTL
        call_args = mock_cache.set.call_args
        assert call_args[1]["ttl"] == 3600
    
    @pytest.mark.asyncio
    async def test_extend_nonexistent_session(
        self,
        session_service_with_cache,
        mock_cache
    ):
        """Should return False when extending nonexistent session."""
        mock_cache.get.return_value = None
        
        extended = await session_service_with_cache.extend_session("nonexistent")
        assert extended is False


# ============================================================================
# Configuration Tests
# ============================================================================

class TestSessionServiceConfiguration:
    """Test configuration methods."""
    
    def test_is_cache_enabled_without_cache(self, session_service_no_cache):
        """Should return False when no cache."""
        assert session_service_no_cache.is_cache_enabled() is False
    
    def test_is_cache_enabled_with_cache(self, session_service_with_cache):
        """Should return True when cache configured."""
        assert session_service_with_cache.is_cache_enabled() is True
    
    def test_get_default_ttl_seconds(self, session_service_with_cache):
        """Should return default TTL in seconds."""
        ttl = session_service_with_cache.get_default_ttl_seconds()
        assert ttl == 1800  # 30 minutes
