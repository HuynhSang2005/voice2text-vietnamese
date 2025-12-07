"""
Tests for Response DTOs and domain-to-DTO mappers.
"""
import pytest
from datetime import datetime
from typing import Optional

from app.application.dtos.responses import (
    TranscriptionResponse,
    ContentModerationResponse,
    ModerationResponse,
    HistoryResponse,
    ModelStatusResponse,
    ModelSwitchResponse,
    HealthCheckResponse,
    ErrorResponse,
)
from app.domain.entities import Transcription, ModerationResult


class TestTranscriptionResponse:
    """Tests for TranscriptionResponse DTO."""
    
    def test_from_entity_without_moderation(self):
        """Test converting Transcription entity to DTO without moderation."""
        # Create domain entity
        entity = Transcription(
            id=1,
            text="xin chào",
            confidence=0.95,
            is_final=True,
            model="zipformer",
            workflow_type="streaming",
            latency_ms=150,
            session_id="session-123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            moderation_result=None
        )
        
        # Convert to DTO
        dto = TranscriptionResponse.from_entity(entity)
        
        assert dto.id == 1
        assert dto.text == "xin chào"
        assert dto.confidence == 0.95
        assert dto.is_final is True
        assert dto.model == "zipformer"
        assert dto.workflow_type == "streaming"
        assert dto.latency_ms == 150
        assert dto.session_id == "session-123"
        assert dto.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert dto.content_moderation is None
    
    def test_from_entity_with_moderation(self):
        """Test converting Transcription entity to DTO with moderation."""
        # Create moderation result
        moderation = ModerationResult(
            label="OFFENSIVE",
            label_id=1,
            confidence=0.85,
            is_flagged=True,
            detected_keywords=["badword"]
        )
        
        # Create domain entity
        entity = Transcription(
            id=2,
            text="offensive content",
            confidence=0.90,
            is_final=True,
            model="zipformer",
            workflow_type="streaming",
            latency_ms=200,
            session_id="session-456",
            created_at=datetime(2024, 1, 1, 13, 0, 0),
            moderation_result=moderation
        )
        
        # Convert to DTO
        dto = TranscriptionResponse.from_entity(entity)
        
        assert dto.id == 2
        assert dto.text == "offensive content"
        assert dto.content_moderation is not None
        assert dto.content_moderation.label == "OFFENSIVE"
        assert dto.content_moderation.confidence == 0.85
        assert dto.content_moderation.is_flagged is True
        assert dto.content_moderation.detected_keywords == ["badword"]
    
    def test_direct_instantiation(self):
        """Test creating DTO directly (without from_entity)."""
        dto = TranscriptionResponse(
            id=3,
            text="test",
            confidence=0.88,
            is_final=False,
            model="whisper",
            workflow_type="batch",
            latency_ms=100,
            session_id=None,
            created_at=datetime(2024, 1, 1, 14, 0, 0),
            content_moderation=None
        )
        
        assert dto.id == 3
        assert dto.text == "test"
        assert dto.is_final is False


class TestContentModerationResponse:
    """Tests for ContentModerationResponse DTO."""
    
    def test_clean_content(self):
        """Test DTO for clean content."""
        dto = ContentModerationResponse(
            label="CLEAN",
            confidence=0.98,
            is_flagged=False,
            detected_keywords=[]
        )
        
        assert dto.label == "CLEAN"
        assert dto.confidence == 0.98
        assert dto.is_flagged is False
        assert dto.detected_keywords == []
    
    def test_offensive_content(self):
        """Test DTO for offensive content."""
        dto = ContentModerationResponse(
            label="OFFENSIVE",
            confidence=0.75,
            is_flagged=True,
            detected_keywords=["word1", "word2"]
        )
        
        assert dto.label == "OFFENSIVE"
        assert dto.confidence == 0.75
        assert dto.is_flagged is True
        assert dto.detected_keywords == ["word1", "word2"]


class TestModerationResponse:
    """Tests for ModerationResponse DTO."""
    
    def test_from_entity(self):
        """Test converting ModerationResult entity to DTO."""
        # Create domain entity
        entity = ModerationResult(
            label="HATE",
            label_id=2,
            confidence=0.92,
            is_flagged=True,
            detected_keywords=["hate1", "hate2"]
        )
        
        # Convert to DTO
        dto = ModerationResponse.from_entity(
            entity=entity,
            latency_ms=50,
            request_id="req-123"
        )
        
        assert dto.type == "moderation"
        assert dto.label == "HATE"
        assert dto.label_id == 2
        assert dto.confidence == 0.92
        assert dto.is_flagged is True
        assert dto.detected_keywords == ["hate1", "hate2"]
        assert dto.latency_ms == 50
        assert dto.request_id == "req-123"
    
    def test_from_entity_optional_params(self):
        """Test from_entity with optional parameters."""
        entity = ModerationResult(
            label="CLEAN",
            label_id=0,
            confidence=0.99,
            is_flagged=False,
            detected_keywords=[]
        )
        
        # Without optional params
        dto = ModerationResponse.from_entity(entity)
        
        assert dto.label == "CLEAN"
        assert dto.latency_ms is None
        assert dto.request_id is None
    
    def test_direct_instantiation(self):
        """Test creating DTO directly."""
        dto = ModerationResponse(
            type="moderation",
            label="OFFENSIVE",
            label_id=1,
            confidence=0.80,
            is_flagged=True,
            detected_keywords=["bad"],
            latency_ms=75,
            request_id="req-456"
        )
        
        assert dto.type == "moderation"
        assert dto.label == "OFFENSIVE"
        assert dto.latency_ms == 75


class TestHistoryResponse:
    """Tests for HistoryResponse DTO."""
    
    def test_empty_history(self):
        """Test DTO for empty history."""
        dto = HistoryResponse(
            items=[],
            total=0,
            skip=0,
            limit=50,
            has_more=False
        )
        
        assert dto.items == []
        assert dto.total == 0
        assert dto.skip == 0
        assert dto.limit == 50
        assert dto.has_more is False
    
    def test_with_items(self):
        """Test DTO with transcription items."""
        items = [
            TranscriptionResponse(
                id=1,
                text="text1",
                confidence=0.9,
                is_final=True,
                model="zipformer",
                workflow_type="streaming",
                latency_ms=100,
                session_id=None,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                content_moderation=None
            ),
            TranscriptionResponse(
                id=2,
                text="text2",
                confidence=0.85,
                is_final=True,
                model="zipformer",
                workflow_type="streaming",
                latency_ms=150,
                session_id=None,
                created_at=datetime(2024, 1, 1, 13, 0, 0),
                content_moderation=None
            )
        ]
        
        dto = HistoryResponse(
            items=items,
            total=100,
            skip=10,
            limit=20,
            has_more=True
        )
        
        assert len(dto.items) == 2
        assert dto.total == 100
        assert dto.skip == 10
        assert dto.limit == 20
        assert dto.has_more is True


class TestModelStatusResponse:
    """Tests for ModelStatusResponse DTO."""
    
    def test_ready_status(self):
        """Test DTO for ready status."""
        dto = ModelStatusResponse(
            current_model="zipformer",
            is_loaded=True,
            status="ready",
            moderation_enabled=True,
            moderation_worker_ready=True
        )
        
        assert dto.current_model == "zipformer"
        assert dto.is_loaded is True
        assert dto.status == "ready"
        assert dto.moderation_enabled is True
        assert dto.moderation_worker_ready is True
    
    def test_loading_status(self):
        """Test DTO for loading status."""
        dto = ModelStatusResponse(
            current_model=None,
            is_loaded=False,
            status="loading",
            moderation_enabled=False,
            moderation_worker_ready=False
        )
        
        assert dto.current_model is None
        assert dto.is_loaded is False
        assert dto.status == "loading"
        assert dto.moderation_enabled is False
        assert dto.moderation_worker_ready is False


class TestModelSwitchResponse:
    """Tests for ModelSwitchResponse DTO."""
    
    def test_successful_switch(self):
        """Test DTO for successful model switch."""
        dto = ModelSwitchResponse(
            success=True,
            message="Model switched successfully",
            previous_model="zipformer",
            new_model="whisper"
        )
        
        assert dto.success is True
        assert dto.message == "Model switched successfully"
        assert dto.previous_model == "zipformer"
        assert dto.new_model == "whisper"
    
    def test_failed_switch(self):
        """Test DTO for failed model switch."""
        dto = ModelSwitchResponse(
            success=False,
            message="Model not found",
            previous_model="zipformer",
            new_model=None
        )
        
        assert dto.success is False
        assert dto.message == "Model not found"
        assert dto.previous_model == "zipformer"
        assert dto.new_model is None


class TestHealthCheckResponse:
    """Tests for HealthCheckResponse DTO."""
    
    def test_healthy_status(self):
        """Test DTO for healthy status."""
        components = {
            "database": "healthy",
            "zipformer_worker": "healthy",
            "moderation_worker": "healthy"
        }
        
        dto = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            components=components
        )
        
        assert dto.status == "healthy"
        assert dto.version == "1.0.0"
        assert dto.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert dto.components == components
    
    def test_degraded_status(self):
        """Test DTO for degraded status."""
        components = {
            "database": "healthy",
            "zipformer_worker": "healthy",
            "moderation_worker": "unhealthy"
        }
        
        dto = HealthCheckResponse(
            status="degraded",
            version="1.0.0",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            components=components
        )
        
        assert dto.status == "degraded"
        assert dto.components["moderation_worker"] == "unhealthy"


class TestErrorResponse:
    """Tests for ErrorResponse DTO (RFC 7807 compliant)."""
    
    def test_validation_error(self):
        """Test DTO for validation error."""
        dto = ErrorResponse(
            type="https://api.example.com/errors/validation-error",
            title="Validation Error",
            status=400,
            detail="Invalid sample rate: must be one of 8000, 16000, 22050, 44100, 48000",
            instance="/api/v1/transcribe"
        )
        
        assert dto.type == "https://api.example.com/errors/validation-error"
        assert dto.title == "Validation Error"
        assert dto.status == 400
        assert "Invalid sample rate" in dto.detail
        assert dto.instance == "/api/v1/transcribe"
    
    def test_not_found_error(self):
        """Test DTO for not found error."""
        dto = ErrorResponse(
            type="https://api.example.com/errors/not-found",
            title="Not Found",
            status=404,
            detail="Transcription with ID 999 not found",
            instance="/api/v1/history/999"
        )
        
        assert dto.type == "https://api.example.com/errors/not-found"
        assert dto.title == "Not Found"
        assert dto.status == 404
        assert dto.instance == "/api/v1/history/999"
    
    def test_internal_server_error(self):
        """Test DTO for internal server error."""
        dto = ErrorResponse(
            type="https://api.example.com/errors/internal-error",
            title="Internal Server Error",
            status=500,
            detail="Worker process crashed unexpectedly",
            instance="/api/v1/transcribe"
        )
        
        assert dto.type == "https://api.example.com/errors/internal-error"
        assert dto.status == 500
        assert "Worker process crashed" in dto.detail
