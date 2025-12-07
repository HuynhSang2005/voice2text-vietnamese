"""Unit tests for Session domain entity."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.domain.entities.session import Session


class TestSessionEntity:
    """Test suite for Session entity."""
    
    def test_create_new_session(self):
        """Test creating a new session with factory method."""
        model_id = "zipformer"
        ttl_hours = 24
        
        session = Session.create_new(
            model_id=model_id,
            ttl_hours=ttl_hours,
        )
        
        assert session.model_id == model_id
        assert session.is_active is True
        assert session.transcription_count == 0
        assert isinstance(session.id, str)
        assert isinstance(session.created_at, datetime)
        assert session.created_at.tzinfo is not None
        assert isinstance(session.expires_at, datetime)
        assert session.expires_at > session.created_at
    
    def test_is_expired_returns_false_for_valid_session(self):
        """Test is_expired() returns False for non-expired session."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,  # 1 hour
        )
        
        assert session.is_expired() is False
    
    def test_is_expired_returns_true_for_expired_session(self):
        """Test is_expired() returns True for expired session."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        session = Session(
            id=str(uuid4()),
            model_id="zipformer",
            is_active=True,
            transcription_count=0,
            created_at=past_time,
            expires_at=past_time + timedelta(hours=1),  # Expired 1 hour ago
        )
        
        assert session.is_expired() is True
    
    def test_is_valid_returns_true_for_active_non_expired(self):
        """Test is_valid() returns True for active and non-expired session."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        assert session.is_valid() is True
    
    def test_is_valid_returns_false_for_inactive_session(self):
        """Test is_valid() returns False for inactive session."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        # Deactivate the session (mutates in place)
        session.deactivate()
        
        assert session.is_valid() is False
    
    def test_is_valid_returns_false_for_expired_session(self):
        """Test is_valid() returns False for expired session."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        session = Session(
            id=str(uuid4()),
            model_id="zipformer",
            is_active=True,
            transcription_count=0,
            created_at=past_time,
            expires_at=past_time + timedelta(hours=1),
        )
        
        assert session.is_valid() is False
    
    def test_extend_expiration(self):
        """Test extending session expiration time."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        original_expires_at = session.expires_at
        
        # Extend by 24 hours (default) - sets expires_at to NOW + hours
        session.extend_expiration(hours=24)
        
        # New expiration should be significantly later than original (roughly 23 hours more)
        assert session.expires_at > original_expires_at
        time_diff = (session.expires_at - original_expires_at).total_seconds()
        assert time_diff >= 23 * 3600  # At least 23 hours more (accounting for time passage)
    
    def test_deactivate(self):
        """Test deactivating a session."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        assert session.is_active is True
        
        # Deactivate mutates in place
        session.deactivate()
        
        assert session.is_active is False
    
    def test_increment_transcription_count(self):
        """Test incrementing transcription count."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        assert session.transcription_count == 0
        
        # Increment mutates in place
        session.increment_transcription_count()
        
        assert session.transcription_count == 1
        
        # Increment again
        session.increment_transcription_count()
        
        assert session.transcription_count == 2
    
    def test_get_remaining_time_returns_positive_for_valid_session(self):
        """Test get_remaining_time() returns positive timedelta for valid session."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
        )
        
        remaining = session.get_remaining_time()
        
        assert isinstance(remaining, timedelta)
        assert remaining.total_seconds() > 0
        assert remaining.total_seconds() <= 3600
    
    def test_get_remaining_time_returns_zero_for_expired_session(self):
        """Test get_remaining_time() returns zero timedelta for expired session."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        session = Session(
            id=str(uuid4()),
            model_id="zipformer",
            is_active=True,
            transcription_count=0,
            created_at=past_time,
            expires_at=past_time + timedelta(hours=1),
        )
        
        remaining = session.get_remaining_time()
        
        assert isinstance(remaining, timedelta)
        assert remaining.total_seconds() == 0
    
    def test_session_identity_by_id(self):
        """Test that sessions with same ID but different fields are different instances."""
        session_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=1)
        
        s1 = Session(
            id=session_id,
            model_id="zipformer",
            is_active=True,
            transcription_count=0,
            created_at=created_at,
            expires_at=expires_at,
        )
        
        s2 = Session(
            id=session_id,
            model_id="different_model",  # Different field
            is_active=False,
            transcription_count=10,
            created_at=created_at,
            expires_at=expires_at,
        )
        
        # Dataclasses compare all fields by default, so these are not equal
        assert s1 != s2
        
        # But they have the same ID
        assert s1.id == s2.id
    
    def test_session_to_dict(self):
        """Test to_dict() method returns correct dictionary."""
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=24,
        )
        
        result = session.to_dict()
        
        assert result["id"] == session.id
        assert result["model_id"] == "zipformer"
        assert result["is_active"] is True
        assert result["is_expired"] is False
        assert result["is_valid"] is True
        assert result["transcription_count"] == 0
        assert "remaining_seconds" in result
    
    def test_session_default_ttl(self):
        """Test session creation with default TTL (24 hours)."""
        session = Session.create_new(model_id="zipformer")
        
        time_diff = (session.expires_at - session.created_at).total_seconds()
        
        assert time_diff == pytest.approx(24 * 3600, rel=1)
    
    def test_session_with_custom_id(self):
        """Test session creation with custom session ID."""
        custom_id = "custom-session-123"
        
        session = Session.create_new(
            model_id="zipformer",
            ttl_hours=1,
            session_id=custom_id,
        )
        
        assert session.id == custom_id
