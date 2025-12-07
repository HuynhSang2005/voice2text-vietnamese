"""
Tests for Request DTOs.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime

from app.application.dtos.requests import (
    TranscriptionRequest,
    HistoryQueryRequest,
    ModelSwitchRequest,
    ModerationToggleRequest,
    StandaloneModerateRequest,
    WebSocketConfigMessage,
)


class TestTranscriptionRequest:
    """Tests for TranscriptionRequest DTO."""
    
    def test_default_values(self):
        """Test DTO with default values."""
        request = TranscriptionRequest()
        
        assert request.model == "zipformer"
        assert request.sample_rate == 16000
        assert request.enable_moderation is True
        assert request.session_id is None
        assert request.language == "vi"
    
    def test_custom_values(self):
        """Test DTO with custom values."""
        request = TranscriptionRequest(
            model="whisper",
            sample_rate=48000,
            enable_moderation=False,
            session_id="test-123",
            language="en"
        )
        
        assert request.model == "whisper"
        assert request.sample_rate == 48000
        assert request.enable_moderation is False
        assert request.session_id == "test-123"
        assert request.language == "en"
    
    def test_invalid_sample_rate(self):
        """Test validation fails for non-standard sample rate."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionRequest(sample_rate=12000)
        
        assert "Sample rate must be one of" in str(exc_info.value)
    
    def test_invalid_language(self):
        """Test validation fails for unsupported language."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionRequest(language="fr")
        
        assert "Language must be one of" in str(exc_info.value)
    
    def test_sample_rate_too_low(self):
        """Test validation fails for sample rate below minimum."""
        with pytest.raises(ValidationError):
            TranscriptionRequest(sample_rate=7000)
    
    def test_sample_rate_too_high(self):
        """Test validation fails for sample rate above maximum."""
        with pytest.raises(ValidationError):
            TranscriptionRequest(sample_rate=50000)


class TestHistoryQueryRequest:
    """Tests for HistoryQueryRequest DTO."""
    
    def test_default_values(self):
        """Test DTO with default values."""
        request = HistoryQueryRequest()
        
        assert request.skip == 0
        assert request.limit == 50
        assert request.search is None
        assert request.model_filter is None
        assert request.session_id is None
        assert request.start_date is None
        assert request.end_date is None
        assert request.order_by == "created_at"
        assert request.order_direction == "desc"
    
    def test_custom_values(self):
        """Test DTO with custom values."""
        now = datetime.now()
        request = HistoryQueryRequest(
            skip=10,
            limit=20,
            search="hello",
            model_filter="zipformer",
            session_id="session-123",
            start_date=now,
            order_by="confidence",
            order_direction="asc"
        )
        
        assert request.skip == 10
        assert request.limit == 20
        assert request.search == "hello"
        assert request.model_filter == "zipformer"
        assert request.session_id == "session-123"
        assert request.start_date == now
        assert request.order_by == "confidence"
        assert request.order_direction == "asc"
    
    def test_negative_skip(self):
        """Test validation fails for negative skip."""
        with pytest.raises(ValidationError):
            HistoryQueryRequest(skip=-1)
    
    def test_zero_limit(self):
        """Test validation fails for zero limit."""
        with pytest.raises(ValidationError):
            HistoryQueryRequest(limit=0)
    
    def test_limit_too_high(self):
        """Test validation fails for limit exceeding maximum."""
        with pytest.raises(ValidationError):
            HistoryQueryRequest(limit=101)
    
    def test_invalid_order_by(self):
        """Test validation fails for invalid order_by field."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryQueryRequest(order_by="invalid_field")
        
        assert "order_by must be one of" in str(exc_info.value)
    
    def test_search_too_long(self):
        """Test validation fails for search query too long."""
        with pytest.raises(ValidationError):
            HistoryQueryRequest(search="x" * 201)


class TestModelSwitchRequest:
    """Tests for ModelSwitchRequest DTO."""
    
    def test_valid_request(self):
        """Test DTO with valid values."""
        request = ModelSwitchRequest(model_id="zipformer")
        
        assert request.model_id == "zipformer"
        assert request.force is False
    
    def test_with_force(self):
        """Test DTO with force flag."""
        request = ModelSwitchRequest(model_id="whisper", force=True)
        
        assert request.model_id == "whisper"
        assert request.force is True
    
    def test_model_id_normalized(self):
        """Test model_id is normalized (trimmed and lowercased)."""
        request = ModelSwitchRequest(model_id="  ZIPFORMER  ")
        
        assert request.model_id == "zipformer"
    
    def test_empty_model_id(self):
        """Test validation fails for empty model_id."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSwitchRequest(model_id="")
        
        # Pydantic v2 uses min_length constraint which gives "String should have at least 1 character" error
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_whitespace_model_id(self):
        """Test validation fails for whitespace-only model_id."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSwitchRequest(model_id="   ")
        
        assert "model_id cannot be empty" in str(exc_info.value)
    
    def test_model_id_required(self):
        """Test validation fails when model_id is missing."""
        with pytest.raises(ValidationError):
            ModelSwitchRequest()


class TestModerationToggleRequest:
    """Tests for ModerationToggleRequest DTO."""
    
    def test_enable_moderation(self):
        """Test enabling moderation."""
        request = ModerationToggleRequest(enabled=True)
        assert request.enabled is True
    
    def test_disable_moderation(self):
        """Test disabling moderation."""
        request = ModerationToggleRequest(enabled=False)
        assert request.enabled is False
    
    def test_enabled_required(self):
        """Test validation fails when enabled is missing."""
        with pytest.raises(ValidationError):
            ModerationToggleRequest()


class TestStandaloneModerateRequest:
    """Tests for StandaloneModerateRequest DTO."""
    
    def test_valid_request(self):
        """Test DTO with valid values."""
        request = StandaloneModerateRequest(text="Hello world")
        
        assert request.text == "Hello world"
        assert request.threshold == 0.5
    
    def test_custom_threshold(self):
        """Test DTO with custom threshold."""
        request = StandaloneModerateRequest(
            text="Test text",
            threshold=0.8
        )
        
        assert request.text == "Test text"
        assert request.threshold == 0.8
    
    def test_text_trimmed(self):
        """Test text is trimmed of whitespace."""
        request = StandaloneModerateRequest(text="  Hello  ")
        
        assert request.text == "Hello"
    
    def test_empty_text(self):
        """Test validation fails for empty text."""
        with pytest.raises(ValidationError) as exc_info:
            StandaloneModerateRequest(text="")
        
        # Pydantic v2 uses min_length constraint which gives "String should have at least 1 character" error
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_whitespace_only_text(self):
        """Test validation fails for whitespace-only text."""
        with pytest.raises(ValidationError) as exc_info:
            StandaloneModerateRequest(text="   ")
        
        assert "Text cannot be empty" in str(exc_info.value)
    
    def test_text_too_long(self):
        """Test validation fails for text exceeding maximum length."""
        with pytest.raises(ValidationError):
            StandaloneModerateRequest(text="x" * 5001)
    
    def test_threshold_below_minimum(self):
        """Test validation fails for threshold below 0.0."""
        with pytest.raises(ValidationError):
            StandaloneModerateRequest(text="Test", threshold=-0.1)
    
    def test_threshold_above_maximum(self):
        """Test validation fails for threshold above 1.0."""
        with pytest.raises(ValidationError):
            StandaloneModerateRequest(text="Test", threshold=1.1)


class TestWebSocketConfigMessage:
    """Tests for WebSocketConfigMessage DTO."""
    
    def test_default_values(self):
        """Test DTO with default values."""
        config = WebSocketConfigMessage()
        
        assert config.type == "config"
        assert config.model == "zipformer"
        assert config.sample_rate == 16000
        assert config.moderation is True
        assert config.session_id is None
    
    def test_custom_values(self):
        """Test DTO with custom values."""
        config = WebSocketConfigMessage(
            model="whisper",
            sample_rate=48000,
            moderation=False,
            session_id="ws-123"
        )
        
        assert config.type == "config"
        assert config.model == "whisper"
        assert config.sample_rate == 48000
        assert config.moderation is False
        assert config.session_id == "ws-123"
    
    def test_invalid_sample_rate(self):
        """Test validation fails for non-standard sample rate."""
        with pytest.raises(ValidationError) as exc_info:
            WebSocketConfigMessage(sample_rate=12000)
        
        assert "Sample rate must be one of" in str(exc_info.value)
    
    def test_type_always_config(self):
        """Test type is always 'config'."""
        config = WebSocketConfigMessage()
        assert config.type == "config"
        
        # Even if we try to set it differently
        config2 = WebSocketConfigMessage(type="config")
        assert config2.type == "config"
