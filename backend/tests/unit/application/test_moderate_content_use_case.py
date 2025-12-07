"""
Unit tests for moderation use cases.

Tests cover:
- ModerateContentUseCase: Constructor, validation, execution, error handling
- GetModerationStatusUseCase: Constructor, status retrieval, error handling
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from app.application.use_cases.moderate_content import (
    ModerateContentUseCase,
    GetModerationStatusUseCase
)
from app.application.dtos.requests import StandaloneModerateRequest
from app.application.dtos.responses import ContentModerationResponse
from app.domain.entities.moderation_result import ModerationResult
from app.domain.exceptions import ValidationException, BusinessRuleViolationException
from app.domain.exceptions.worker import WorkerException


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_moderation_worker():
    """Create mock moderation worker."""
    worker = AsyncMock()
    worker.is_ready = AsyncMock(return_value=True)
    return worker


@pytest.fixture
def sample_moderation_request():
    """Create sample moderation request."""
    return StandaloneModerateRequest(
        text="Sample text to moderate",
        threshold=0.5
    )


@pytest.fixture
def clean_moderation_result():
    """Create clean moderation result."""
    return ModerationResult(
        label=ModerationResult.CLEAN,
        confidence=0.98,
        is_flagged=False,
        detected_keywords=[],
        processed_at=datetime.now(timezone.utc),
        model_version="visobert-hsd-span"
    )


@pytest.fixture
def offensive_moderation_result():
    """Create offensive moderation result."""
    return ModerationResult(
        label=ModerationResult.OFFENSIVE,
        confidence=0.85,
        is_flagged=True,
        detected_keywords=["bad_word1", "bad_word2"],
        processed_at=datetime.now(timezone.utc),
        model_version="visobert-hsd-span"
    )


@pytest.fixture
def hate_speech_result():
    """Create hate speech moderation result."""
    return ModerationResult(
        label=ModerationResult.HATE,
        confidence=0.92,
        is_flagged=True,
        detected_keywords=["hate_word1", "hate_word2"],
        processed_at=datetime.now(timezone.utc),
        model_version="visobert-hsd-span"
    )


# ============================================================================
# ModerateContentUseCase - Constructor Tests
# ============================================================================

class TestModerateContentUseCaseConstructor:
    """Test ModerateContentUseCase constructor validation."""
    
    def test_constructor_with_valid_worker(self, mock_moderation_worker):
        """Should create use case with valid worker."""
        use_case = ModerateContentUseCase(mock_moderation_worker)
        assert use_case._moderation_worker is mock_moderation_worker
    
    def test_constructor_with_none_worker(self):
        """Should raise ValidationException when worker is None."""
        with pytest.raises(ValidationException) as exc_info:
            ModerateContentUseCase(None)
        
        assert exc_info.value.field == "moderation_worker"
        assert exc_info.value.value is None
        assert "must not be None" in exc_info.value.constraint


# ============================================================================
# ModerateContentUseCase - Validation Tests
# ============================================================================

class TestModerateContentUseCaseValidation:
    """Test request validation in ModerateContentUseCase."""
    
    @pytest.mark.asyncio
    async def test_execute_with_none_request(self, mock_moderation_worker):
        """Should raise ValidationException when request is None."""
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(None)
        
        assert exc_info.value.field == "request"
        assert exc_info.value.value is None
    
    @pytest.mark.asyncio
    async def test_execute_with_worker_not_ready(
        self,
        mock_moderation_worker,
        sample_moderation_request
    ):
        """Should raise BusinessRuleViolationException when worker not ready."""
        mock_moderation_worker.is_ready = AsyncMock(return_value=False)
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        with pytest.raises(BusinessRuleViolationException) as exc_info:
            await use_case.execute(sample_moderation_request)
        
        assert exc_info.value.rule == "moderation_worker_must_be_ready"


# ============================================================================
# ModerateContentUseCase - Execution Tests
# ============================================================================

class TestModerateContentUseCaseExecution:
    """Test ModerateContentUseCase execution logic."""
    
    @pytest.mark.asyncio
    async def test_execute_with_clean_content(
        self,
        mock_moderation_worker,
        sample_moderation_request,
        clean_moderation_result
    ):
        """Should return clean response for clean content."""
        mock_moderation_worker.moderate = AsyncMock(
            return_value=clean_moderation_result
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        response = await use_case.execute(sample_moderation_request)
        
        assert isinstance(response, ContentModerationResponse)
        assert response.label == "CLEAN"
        assert response.confidence == 0.98
        assert response.is_flagged is False
        assert response.detected_keywords == []
        
        # Verify worker called
        mock_moderation_worker.is_ready.assert_called_once()
        mock_moderation_worker.moderate.assert_called_once_with(
            sample_moderation_request.text
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_offensive_content_above_threshold(
        self,
        mock_moderation_worker,
        offensive_moderation_result
    ):
        """Should flag offensive content when confidence exceeds threshold."""
        request = StandaloneModerateRequest(
            text="Offensive content",
            threshold=0.7  # Below confidence of 0.85
        )
        mock_moderation_worker.moderate = AsyncMock(
            return_value=offensive_moderation_result
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        response = await use_case.execute(request)
        
        assert response.label == "OFFENSIVE"
        assert response.confidence == 0.85
        assert response.is_flagged is True  # Above threshold
        assert len(response.detected_keywords) == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_offensive_content_below_threshold(
        self,
        mock_moderation_worker,
        offensive_moderation_result
    ):
        """Should not flag offensive content when confidence below threshold."""
        request = StandaloneModerateRequest(
            text="Maybe offensive",
            threshold=0.95  # Above confidence of 0.85
        )
        mock_moderation_worker.moderate = AsyncMock(
            return_value=offensive_moderation_result
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        response = await use_case.execute(request)
        
        assert response.label == "OFFENSIVE"
        assert response.confidence == 0.85
        assert response.is_flagged is False  # Below threshold
        assert len(response.detected_keywords) == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_hate_speech(
        self,
        mock_moderation_worker,
        hate_speech_result
    ):
        """Should flag hate speech content."""
        request = StandaloneModerateRequest(
            text="Hate speech content",
            threshold=0.5
        )
        mock_moderation_worker.moderate = AsyncMock(
            return_value=hate_speech_result
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        response = await use_case.execute(request)
        
        assert response.label == "HATE"
        assert response.confidence == 0.92
        assert response.is_flagged is True
        assert len(response.detected_keywords) == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_worker_exception(
        self,
        mock_moderation_worker,
        sample_moderation_request
    ):
        """Should re-raise WorkerException from worker."""
        mock_moderation_worker.moderate = AsyncMock(
            side_effect=WorkerException(
                worker_type="moderation",
                message="Model inference failed"
            )
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute(sample_moderation_request)
        
        assert exc_info.value.worker_type == "moderation"
        assert "Model inference failed" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_execute_with_unexpected_exception(
        self,
        mock_moderation_worker,
        sample_moderation_request
    ):
        """Should wrap unexpected exceptions as WorkerException."""
        mock_moderation_worker.moderate = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )
        use_case = ModerateContentUseCase(mock_moderation_worker)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute(sample_moderation_request)
        
        assert exc_info.value.worker_type == "moderation"
        assert "unexpected error" in exc_info.value.message.lower()
        assert "Unexpected error" in exc_info.value.message


# ============================================================================
# GetModerationStatusUseCase - Constructor Tests
# ============================================================================

class TestGetModerationStatusUseCaseConstructor:
    """Test GetModerationStatusUseCase constructor."""
    
    def test_constructor_with_valid_worker(self, mock_moderation_worker):
        """Should create use case with valid worker."""
        use_case = GetModerationStatusUseCase(mock_moderation_worker)
        assert use_case._moderation_worker is mock_moderation_worker
    
    def test_constructor_with_none_worker(self):
        """Should accept None worker (moderation disabled)."""
        use_case = GetModerationStatusUseCase(None)
        assert use_case._moderation_worker is None


# ============================================================================
# GetModerationStatusUseCase - Execution Tests
# ============================================================================

class TestGetModerationStatusUseCaseExecution:
    """Test GetModerationStatusUseCase execution logic."""
    
    @pytest.mark.asyncio
    async def test_execute_with_ready_worker(self, mock_moderation_worker):
        """Should return available and ready status."""
        mock_moderation_worker.is_ready = AsyncMock(return_value=True)
        use_case = GetModerationStatusUseCase(mock_moderation_worker)
        
        status = await use_case.execute()
        
        assert status["is_available"] is True
        assert status["is_ready"] is True
        assert status["model_version"] == "visobert-hsd-span"
        mock_moderation_worker.is_ready.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_not_ready_worker(self, mock_moderation_worker):
        """Should return available but not ready status."""
        mock_moderation_worker.is_ready = AsyncMock(return_value=False)
        use_case = GetModerationStatusUseCase(mock_moderation_worker)
        
        status = await use_case.execute()
        
        assert status["is_available"] is True
        assert status["is_ready"] is False
        assert status["model_version"] == "visobert-hsd-span"
    
    @pytest.mark.asyncio
    async def test_execute_with_none_worker(self):
        """Should return unavailable status when worker is None."""
        use_case = GetModerationStatusUseCase(None)
        
        status = await use_case.execute()
        
        assert status["is_available"] is False
        assert status["is_ready"] is False
        assert status["model_version"] is None
    
    @pytest.mark.asyncio
    async def test_execute_with_exception(self, mock_moderation_worker):
        """Should return unavailable status on exception."""
        mock_moderation_worker.is_ready = AsyncMock(
            side_effect=Exception("Worker crashed")
        )
        use_case = GetModerationStatusUseCase(mock_moderation_worker)
        
        status = await use_case.execute()
        
        assert status["is_available"] is True
        assert status["is_ready"] is False
        assert status["model_version"] is None
        assert "error" in status
        assert "Worker crashed" in status["error"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestModerationUseCaseIntegration:
    """Integration tests for moderation use cases."""
    
    @pytest.mark.asyncio
    async def test_moderate_and_check_status(self, mock_moderation_worker):
        """Should work together for moderate + status check."""
        # Setup
        clean_result = ModerationResult(
            label=ModerationResult.CLEAN,
            confidence=0.99,
            is_flagged=False,
            detected_keywords=[]
        )
        mock_moderation_worker.moderate = AsyncMock(return_value=clean_result)
        mock_moderation_worker.is_ready = AsyncMock(return_value=True)
        
        # Create use cases
        moderate_use_case = ModerateContentUseCase(mock_moderation_worker)
        status_use_case = GetModerationStatusUseCase(mock_moderation_worker)
        
        # Check status first
        status = await status_use_case.execute()
        assert status["is_ready"] is True
        
        # Then moderate content
        request = StandaloneModerateRequest(
            text="Hello world",
            threshold=0.5
        )
        response = await moderate_use_case.execute(request)
        
        assert response.label == "CLEAN"
        assert response.is_flagged is False
