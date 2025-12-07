"""
Unit tests for TranscribeAudioUseCase.

Tests verify:
1. Streaming transcription workflow
2. Moderation integration (when enabled)
3. Repository persistence
4. Error handling scenarios
5. Batch transcription variant
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone
from typing import AsyncIterator

from app.application.use_cases.transcribe_audio import (
    TranscribeAudioUseCase,
    TranscribeAudioBatchUseCase,
)
from app.application.dtos.requests import TranscriptionRequest
from app.domain.entities.transcription import Transcription
from app.domain.entities.moderation_result import ModerationResult
from app.domain.value_objects.audio_data import AudioData
from app.domain.exceptions import (
    ValidationException,
    BusinessRuleViolationException as BusinessRuleException,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_transcription_worker():
    """Mock ITranscriptionWorker for testing."""
    worker = AsyncMock()
    worker.is_ready = AsyncMock(return_value=True)
    return worker


@pytest.fixture
def mock_moderation_worker():
    """Mock IModerationWorker for testing."""
    worker = AsyncMock()
    worker.is_ready = AsyncMock(return_value=True)
    worker.moderate = AsyncMock()
    return worker


@pytest.fixture
def mock_repository():
    """Mock ITranscriptionRepository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def sample_audio_data():
    """Create sample AudioData for testing."""
    return AudioData(
        data=b"fake_audio_bytes",
        sample_rate=16000,
        channels=1,  # Mono audio
        format="wav",
        duration_ms=1000
    )


@pytest.fixture
def sample_transcription_request():
    """Create sample TranscriptionRequest."""
    return TranscriptionRequest(
        model="zipformer",
        sample_rate=16000,
        enable_moderation=False,
        session_id="test-session-123",
        language="vi"
    )


# ==================== Constructor Tests ====================

class TestTranscribeAudioUseCaseConstructor:
    """Tests for use case initialization."""
    
    def test_valid_initialization(
        self,
        mock_transcription_worker,
        mock_moderation_worker,
        mock_repository
    ):
        """Test successful initialization with all dependencies."""
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=mock_moderation_worker,
            repository=mock_repository
        )
        
        assert use_case._transcription_worker == mock_transcription_worker
        assert use_case._moderation_worker == mock_moderation_worker
        assert use_case._repository == mock_repository
    
    def test_initialization_without_moderation_worker(
        self,
        mock_transcription_worker,
        mock_repository
    ):
        """Test initialization without optional moderation worker."""
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,
            repository=mock_repository
        )
        
        assert use_case._transcription_worker == mock_transcription_worker
        assert use_case._moderation_worker is None
        assert use_case._repository == mock_repository
    
    def test_initialization_fails_without_transcription_worker(
        self,
        mock_repository
    ):
        """Test initialization fails if transcription_worker is None."""
        with pytest.raises(ValueError) as exc_info:
            TranscribeAudioUseCase(
                transcription_worker=None,
                moderation_worker=None,
                repository=mock_repository
            )
        
        assert "transcription_worker is required" in str(exc_info.value)
    
    def test_initialization_fails_without_repository(
        self,
        mock_transcription_worker
    ):
        """Test initialization fails if repository is None."""
        with pytest.raises(ValueError) as exc_info:
            TranscribeAudioUseCase(
                transcription_worker=mock_transcription_worker,
                moderation_worker=None,
                repository=None
            )
        
        assert "repository is required" in str(exc_info.value)


# ==================== Streaming Transcription Tests ====================

class TestTranscribeAudioStreamingWorkflow:
    """Tests for streaming transcription workflow."""
    
    @pytest.mark.asyncio
    async def test_successful_streaming_transcription_without_moderation(
        self,
        mock_transcription_worker,
        mock_repository,
        sample_audio_data,
        sample_transcription_request
    ):
        """Test successful streaming transcription without moderation."""
        # Setup: Mock worker to return transcription result
        worker_result = Transcription(
            id=None,
            session_id="test-session-123",
            model_id="zipformer",
            content="xin chào",
            latency_ms=250.0,
            created_at=datetime.now(timezone.utc)
        )
        
        async def mock_process_stream(audio_stream):
            async for _ in audio_stream:
                yield worker_result
        
        mock_transcription_worker.process_audio_stream = mock_process_stream
        
        # Mock repository to return saved entity with ID
        saved_result = Transcription(
            id=1,
            session_id="test-session-123",
            model_id="zipformer",
            content="xin chào",
            latency_ms=250.0,
            created_at=worker_result.created_at
        )
        mock_repository.save = AsyncMock(return_value=saved_result)
        
        # Create use case
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,
            repository=mock_repository
        )
        
        # Execute: Stream audio
        async def audio_stream():
            yield sample_audio_data
        
        results = []
        async for transcription in use_case.execute(audio_stream(), sample_transcription_request):
            results.append(transcription)
        
        # Assert: One result with correct data
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].content == "xin chào"
        assert results[0].model_id == "zipformer"
        assert results[0].session_id == "test-session-123"
        
        # Verify repository was called
        mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_streaming_with_moderation_clean(
        self,
        mock_transcription_worker,
        mock_moderation_worker,
        mock_repository,
        sample_audio_data
    ):
        """Test streaming transcription with moderation (clean content)."""
        # Setup: Enable moderation in request
        request = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True,
            session_id="test-session-456"
        )
        
        # Mock transcription result
        worker_result = Transcription(
            id=None,
            session_id="test-session-456",
            model_id="zipformer",
            content="hello world",
            latency_ms=200.0,
            created_at=datetime.now(timezone.utc)
        )
        
        async def mock_process_stream(audio_stream):
            async for _ in audio_stream:
                yield worker_result
        
        mock_transcription_worker.process_audio_stream = mock_process_stream
        
        # Mock moderation result (CLEAN)
        moderation_result = ModerationResult(
            label="CLEAN",
            confidence=0.98,
            is_flagged=False,
            detected_keywords=[]
        )
        mock_moderation_worker.moderate = AsyncMock(return_value=moderation_result)
        
        # Mock repository
        saved_result = Transcription(
            id=2,
            session_id="test-session-456",
            model_id="zipformer",
            content="hello world",
            latency_ms=200.0,
            created_at=worker_result.created_at,
            moderation_label="CLEAN",
            moderation_confidence=0.98,
            is_flagged=False,
            detected_keywords=[]
        )
        mock_repository.save = AsyncMock(return_value=saved_result)
        
        # Execute
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=mock_moderation_worker,
            repository=mock_repository
        )
        
        async def audio_stream():
            yield sample_audio_data
        
        results = []
        async for transcription in use_case.execute(audio_stream(), request):
            results.append(transcription)
        
        # Assert
        assert len(results) == 1
        assert results[0].moderation_label == "CLEAN"
        assert results[0].moderation_confidence == 0.98
        assert results[0].is_flagged is False
        assert results[0].is_clean() is True
        
        # Verify moderation was called
        mock_moderation_worker.moderate.assert_called_once_with("hello world")
    
    @pytest.mark.asyncio
    async def test_successful_streaming_with_moderation_offensive(
        self,
        mock_transcription_worker,
        mock_moderation_worker,
        mock_repository,
        sample_audio_data
    ):
        """Test streaming transcription with moderation (offensive content)."""
        request = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True,
            session_id="test-session-789"
        )
        
        # Mock offensive transcription
        worker_result = Transcription(
            id=None,
            session_id="test-session-789",
            model_id="zipformer",
            content="offensive text here",
            latency_ms=220.0,
            created_at=datetime.now(timezone.utc)
        )
        
        async def mock_process_stream(audio_stream):
            async for _ in audio_stream:
                yield worker_result
        
        mock_transcription_worker.process_audio_stream = mock_process_stream
        
        # Mock moderation result (OFFENSIVE)
        moderation_result = ModerationResult(
            label="OFFENSIVE",
            confidence=0.85,
            is_flagged=True,
            detected_keywords=["offensive", "word"]
        )
        mock_moderation_worker.moderate = AsyncMock(return_value=moderation_result)
        
        # Mock repository
        saved_result = Transcription(
            id=3,
            session_id="test-session-789",
            model_id="zipformer",
            content="offensive text here",
            latency_ms=220.0,
            created_at=worker_result.created_at,
            moderation_label="OFFENSIVE",
            moderation_confidence=0.85,
            is_flagged=True,
            detected_keywords=["offensive", "word"]
        )
        mock_repository.save = AsyncMock(return_value=saved_result)
        
        # Execute
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=mock_moderation_worker,
            repository=mock_repository
        )
        
        async def audio_stream():
            yield sample_audio_data
        
        results = []
        async for transcription in use_case.execute(audio_stream(), request):
            results.append(transcription)
        
        # Assert
        assert len(results) == 1
        assert results[0].moderation_label == "OFFENSIVE"
        assert results[0].is_flagged is True
        assert results[0].is_offensive() is True
        assert results[0].detected_keywords == ["offensive", "word"]


# ==================== Error Handling Tests ====================

class TestTranscribeAudioErrorHandling:
    """Tests for error scenarios."""
    
    @pytest.mark.asyncio
    async def test_fails_when_moderation_requested_but_worker_unavailable(
        self,
        mock_transcription_worker,
        mock_repository,
        sample_audio_data
    ):
        """Test fails if moderation enabled but worker is None."""
        request = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True  # Moderation requested
        )
        
        # Create use case WITHOUT moderation worker
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,  # Worker unavailable
            repository=mock_repository
        )
        
        async def audio_stream():
            yield sample_audio_data
        
        # Execute and expect BusinessRuleException
        with pytest.raises(BusinessRuleException) as exc_info:
            async for _ in use_case.execute(audio_stream(), request):
                pass
        
        assert "moderation worker is not available" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fails_when_transcription_worker_not_ready(
        self,
        mock_transcription_worker,
        mock_repository,
        sample_audio_data,
        sample_transcription_request
    ):
        """Test fails if transcription worker is not ready."""
        # Mock worker as not ready
        mock_transcription_worker.is_ready = AsyncMock(return_value=False)
        
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,
            repository=mock_repository
        )
        
        async def audio_stream():
            yield sample_audio_data
        
        with pytest.raises(BusinessRuleException) as exc_info:
            async for _ in use_case.execute(audio_stream(), sample_transcription_request):
                pass
        
        assert "worker is not ready" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_fails_when_moderation_worker_not_ready(
        self,
        mock_transcription_worker,
        mock_moderation_worker,
        mock_repository,
        sample_audio_data
    ):
        """Test fails if moderation worker is not ready."""
        request = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True
        )
        
        # Moderation worker not ready
        mock_moderation_worker.is_ready = AsyncMock(return_value=False)
        
        use_case = TranscribeAudioUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=mock_moderation_worker,
            repository=mock_repository
        )
        
        async def audio_stream():
            yield sample_audio_data
        
        # Create request with moderation enabled
        request_with_moderation = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True
        )
        
        with pytest.raises(BusinessRuleException) as exc_info:
            async for _ in use_case.execute(audio_stream(), request_with_moderation):
                pass
        
        assert "moderation worker is not ready" in str(exc_info.value).lower()


# ==================== Batch Transcription Tests ====================

class TestTranscribeAudioBatchUseCase:
    """Tests for batch (non-streaming) transcription."""
    
    @pytest.mark.asyncio
    async def test_successful_batch_transcription(
        self,
        mock_transcription_worker,
        mock_repository,
        sample_audio_data,
        sample_transcription_request
    ):
        """Test successful batch transcription."""
        # Mock worker result
        worker_result = Transcription(
            id=None,
            session_id="batch-session",
            model_id="zipformer",
            content="batch transcription",
            latency_ms=300.0,
            created_at=datetime.now(timezone.utc)
        )
        
        async def mock_process_stream(audio_stream):
            async for _ in audio_stream:
                yield worker_result
        
        mock_transcription_worker.process_audio_stream = mock_process_stream
        
        # Mock repository
        saved_result = Transcription(
            id=10,
            session_id="batch-session",
            model_id="zipformer",
            content="batch transcription",
            latency_ms=300.0,
            created_at=worker_result.created_at
        )
        mock_repository.save = AsyncMock(return_value=saved_result)
        
        # Execute batch use case
        batch_use_case = TranscribeAudioBatchUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,
            repository=mock_repository
        )
        
        result = await batch_use_case.execute(
            sample_audio_data,
            sample_transcription_request
        )
        
        # Assert
        assert result.id == 10
        assert result.content == "batch transcription"
        assert result.model_id == "zipformer"
    
    @pytest.mark.asyncio
    async def test_batch_fails_if_no_result_produced(
        self,
        mock_transcription_worker,
        mock_repository,
        sample_audio_data,
        sample_transcription_request
    ):
        """Test batch fails if worker produces no results."""
        # Mock worker to yield nothing - create proper async generator
        async def mock_process_stream(audio_stream):
            async for _ in audio_stream:
                pass  # Consume input but yield nothing
            return  # Exit without yielding any transcriptions
            yield  # This line makes it an async generator (never reached)
        
        mock_transcription_worker.process_audio_stream = mock_process_stream
        
        batch_use_case = TranscribeAudioBatchUseCase(
            transcription_worker=mock_transcription_worker,
            moderation_worker=None,
            repository=mock_repository
        )
        
        with pytest.raises(BusinessRuleException) as exc_info:
            await batch_use_case.execute(
                sample_audio_data,
                sample_transcription_request
            )
        
        assert "no transcription result produced" in str(exc_info.value).lower()
