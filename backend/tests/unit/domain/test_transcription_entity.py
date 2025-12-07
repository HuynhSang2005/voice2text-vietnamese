"""Unit tests for Transcription domain entity."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.transcription import Transcription


class TestTranscriptionEntity:
    """Test suite for Transcription entity."""
    
    def test_create_new_transcription(self):
        """Test creating a new transcription with factory method."""
        content = "Xin chào"
        latency_ms = 150.5
        session_id = str(uuid4())
        model_id = "zipformer"
        
        transcription = Transcription.create_new(
            session_id=session_id,
            model_id=model_id,
            content=content,
            latency_ms=latency_ms,
        )
        
        assert transcription.content == content
        assert transcription.latency_ms == latency_ms
        assert transcription.session_id == session_id
        assert transcription.model_id == model_id
        assert transcription.id is None
        assert transcription.moderation_label is None
        assert isinstance(transcription.created_at, datetime)
        assert transcription.created_at.tzinfo is not None
    
    def test_is_offensive_returns_true_for_offensive_content(self):
        """Test is_offensive() returns True for OFFENSIVE or HATE labels."""
        offensive_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="offensive content",
            latency_ms=100.0,
            moderation_label="OFFENSIVE",
            moderation_confidence=0.85,
            created_at=datetime.now(timezone.utc),
        )
        
        assert offensive_transcription.is_offensive() is True
        
        hate_transcription = Transcription(
            id=2,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="hate speech",
            latency_ms=100.0,
            moderation_label="HATE",
            moderation_confidence=0.92,
            created_at=datetime.now(timezone.utc),
        )
        
        assert hate_transcription.is_offensive() is True
    
    def test_is_offensive_returns_false_for_clean_content(self):
        """Test is_offensive() returns False for CLEAN label."""
        clean_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="xin chào",
            latency_ms=100.0,
            moderation_label="CLEAN",
            moderation_confidence=0.99,
            created_at=datetime.now(timezone.utc),
        )
        
        assert clean_transcription.is_offensive() is False
    
    def test_is_clean_returns_true_for_clean_content(self):
        """Test is_clean() returns True for CLEAN label."""
        clean_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="xin chào",
            latency_ms=100.0,
            moderation_label="CLEAN",
            created_at=datetime.now(timezone.utc),
        )
        
        assert clean_transcription.is_clean() is True
    
    def test_is_clean_returns_false_for_offensive_content(self):
        """Test is_clean() returns False for non-CLEAN labels."""
        offensive_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="offensive",
            latency_ms=100.0,
            moderation_label="OFFENSIVE",
            created_at=datetime.now(timezone.utc),
        )
        
        assert offensive_transcription.is_clean() is False
    
    def test_has_high_confidence_moderation(self):
        """Test high confidence moderation detection."""
        high_conf_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="text",
            latency_ms=100.0,
            moderation_label="OFFENSIVE",
            moderation_confidence=0.85,
            created_at=datetime.now(timezone.utc),
        )
        
        assert high_conf_transcription.has_high_confidence_moderation(threshold=0.8) is True
        assert high_conf_transcription.has_high_confidence_moderation(threshold=0.9) is False
    
    def test_has_high_confidence_moderation_with_none(self):
        """Test high confidence moderation when confidence is None."""
        transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="text",
            latency_ms=100.0,
            moderation_label="CLEAN",
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        
        assert transcription.has_high_confidence_moderation(threshold=0.8) is False
    
    def test_get_severity_level_hate(self):
        """Test severity level for HATE content."""
        hate_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="hate speech",
            latency_ms=100.0,
            moderation_label="HATE",
            moderation_confidence=0.95,
            created_at=datetime.now(timezone.utc),
        )
        
        assert hate_transcription.get_severity_level() == "HIGH"
    
    def test_get_severity_level_offensive(self):
        """Test severity level for OFFENSIVE content."""
        offensive_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="offensive",
            latency_ms=100.0,
            moderation_label="OFFENSIVE",
            moderation_confidence=0.85,
            created_at=datetime.now(timezone.utc),
        )
        
        assert offensive_transcription.get_severity_level() == "LOW"
    
    def test_get_severity_level_clean(self):
        """Test severity level for CLEAN content."""
        clean_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="xin chào",
            latency_ms=100.0,
            moderation_label="CLEAN",
            created_at=datetime.now(timezone.utc),
        )
        
        assert clean_transcription.get_severity_level() == "NONE"
    
    def test_transcription_identity_by_id(self):
        """Test that transcriptions with same ID but different fields are different instances."""
        session_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        
        t1 = Transcription(
            id=1,
            session_id=session_id,
            model_id="zipformer",
            content="text",
            latency_ms=100.0,
            created_at=created_at,
        )
        
        t2 = Transcription(
            id=1,
            session_id=session_id,
            model_id="zipformer",
            content="different text",  # Different field
            latency_ms=200.0,
            created_at=created_at,
        )
        
        # Dataclasses compare all fields by default, so these are not equal
        assert t1 != t2
        
        # But they have the same ID
        assert t1.id == t2.id
    
    def test_transcription_with_optional_fields(self):
        """Test transcription creation with optional fields."""
        transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="text",
            latency_ms=100.0,
            created_at=datetime.now(timezone.utc),
            moderation_label="OFFENSIVE",
            moderation_confidence=0.95,
            is_flagged=True,
            detected_keywords=["test", "example"],
        )
        
        assert transcription.moderation_label == "OFFENSIVE"
        assert transcription.moderation_confidence == 0.95
        assert transcription.is_flagged is True
        assert transcription.detected_keywords == ["test", "example"]
    
    def test_transcription_moderation_confidence_validation(self):
        """Test that moderation_confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValueError, match="moderation_confidence must be between 0.0 and 1.0"):
            Transcription(
                id=1,
                session_id=str(uuid4()),
                model_id="zipformer",
                content="text",
                latency_ms=100.0,
                created_at=datetime.now(timezone.utc),
                moderation_confidence=1.5,  # Invalid: > 1.0
            )
    
    def test_transcription_is_flagged_offensive(self):
        """Test is_offensive() returns True when is_flagged is True."""
        flagged_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="flagged content",
            latency_ms=100.0,
            created_at=datetime.now(timezone.utc),
            is_flagged=True,
        )
        
        assert flagged_transcription.is_offensive() is True
    
    def test_transcription_to_dict(self):
        """Test to_dict() method returns correct dictionary."""
        transcription = Transcription.create_new(
            session_id=str(uuid4()),
            model_id="zipformer",
            content="test content",
            latency_ms=150.0,
            moderation_label="CLEAN",
            moderation_confidence=0.99,
        )
        
        result = transcription.to_dict()
        
        assert result["content"] == "test content"
        assert result["latency_ms"] == 150.0
        assert result["moderation_label"] == "CLEAN"
        assert result["is_offensive"] is False
        assert result["severity_level"] == "NONE"
    
    def test_get_severity_level_offensive_high_confidence(self):
        """Test severity level for OFFENSIVE content with high confidence (>0.9)."""
        offensive_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="offensive",
            latency_ms=100.0,
            moderation_label="OFFENSIVE",
            moderation_confidence=0.95,
            created_at=datetime.now(timezone.utc),
        )
        
        assert offensive_transcription.get_severity_level() == "MEDIUM"
    
    def test_get_severity_level_flagged_no_label(self):
        """Test severity level for flagged content without label."""
        flagged_transcription = Transcription(
            id=1,
            session_id=str(uuid4()),
            model_id="zipformer",
            content="flagged",
            latency_ms=100.0,
            created_at=datetime.now(timezone.utc),
            is_flagged=True,
        )
        
        assert flagged_transcription.get_severity_level() == "LOW"
