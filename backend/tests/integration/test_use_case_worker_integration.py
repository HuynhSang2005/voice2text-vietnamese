"""
Integration tests for Use Case → Worker interactions.

Tests verify end-to-end data flow from application layer to worker layer:
- TranscribeAudioUseCase with real ZipformerWorker
- ModerateContentUseCase with real SpanDetectorWorker
- Real model inference (not mocked)
- Worker lifecycle management
- Error handling with real workers

These tests use real worker implementations but mock repositories.
They are slower because they load actual ML models.

Note: These tests require model files to be present:
- backend/models_storage/zipformer/hynt-zipformer-30M-6000h/
- backend/models_storage/visobert-hsd-span/onnx/
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from typing import AsyncIterator
import os
import sys

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.application.use_cases.transcribe_audio import TranscribeAudioUseCase
from app.application.use_cases.moderate_content import ModerateContentUseCase
from app.application.dtos.requests import TranscriptionRequest, ModerationRequest
from app.infrastructure.workers.zipformer_worker import ZipformerWorker
from app.infrastructure.workers.span_detector_worker import SpanDetectorWorker
from app.domain.entities.transcription import Transcription
from app.domain.value_objects.audio_data import AudioData


# ==================== Configuration ====================


# Path to model files
ZIPFORMER_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../models_storage/zipformer/hynt-zipformer-30M-6000h",
)

VISOBERT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../models_storage/visobert-hsd-span/onnx",
)

# Skip tests if models not available
pytestmark = pytest.mark.skipif(
    not os.path.exists(ZIPFORMER_MODEL_PATH),
    reason="Zipformer model files not found. Run scripts/setup_models.py first.",
)


# ==================== Worker Fixtures ====================


@pytest_asyncio.fixture(scope="module")
async def zipformer_worker():
    """
    Create real ZipformerWorker for testing.
    
    Scope: module - worker is expensive to initialize, reuse across tests.
    """
    worker = ZipformerWorker(
        worker_id=0,
        model_path=ZIPFORMER_MODEL_PATH,
        num_threads=2,  # Use fewer threads for testing
    )
    
    # Start worker process
    worker.start()
    
    # Wait for worker to be ready
    import asyncio
    for _ in range(30):  # Wait up to 30 seconds
        if await worker.is_ready():
            break
        await asyncio.sleep(1)
    else:
        pytest.fail("Zipformer worker failed to start within 30 seconds")
    
    yield worker
    
    # Cleanup
    worker.stop()


@pytest_asyncio.fixture(scope="module")
async def span_detector_worker():
    """
    Create real SpanDetectorWorker for testing.
    
    Scope: module - worker is expensive to initialize, reuse across tests.
    """
    if not os.path.exists(VISOBERT_MODEL_PATH):
        pytest.skip("ViSoBERT model files not found")
    
    worker = SpanDetectorWorker(
        worker_id=0,
        model_path=VISOBERT_MODEL_PATH,
        num_threads=2,
    )
    
    # Start worker process
    worker.start()
    
    # Wait for worker to be ready
    import asyncio
    for _ in range(30):
        if await worker.is_ready():
            break
        await asyncio.sleep(1)
    else:
        pytest.fail("SpanDetector worker failed to start within 30 seconds")
    
    yield worker
    
    # Cleanup
    worker.stop()


# ==================== Mock Repository Fixtures ====================


@pytest.fixture
def mock_transcription_repository():
    """Mock ITranscriptionRepository for testing."""
    repo = AsyncMock()
    
    async def mock_save(transcription: Transcription):
        """Simulate save operation."""
        # Assign ID to simulate database save
        transcription.id = 1
        return transcription
    
    repo.save = mock_save
    return repo


# ==================== Helper Functions ====================


async def create_test_audio_stream() -> AsyncIterator[AudioData]:
    """
    Create test audio stream.
    
    Note: For real testing, you'd need actual audio files.
    This is a placeholder that demonstrates the pattern.
    """
    # For now, yield empty audio data
    # In real tests, you'd load actual .wav files
    yield AudioData(
        data=b"\x00" * 32000,  # 1 second of silence at 16kHz
        sample_rate=16000,
        channels=1,
        format="wav",
        duration_ms=1000,
    )


# ==================== Test Cases ====================


@pytest.mark.slow
class TestTranscribeAudioUseCaseWithZipformerWorker:
    """Test TranscribeAudioUseCase with real ZipformerWorker."""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_real_worker(
        self,
        zipformer_worker,
        mock_transcription_repository,
    ):
        """Test transcription with real Zipformer worker."""
        # Arrange
        use_case = TranscribeAudioUseCase(
            transcription_repo=mock_transcription_repository,
            transcription_worker=zipformer_worker,
            moderation_worker=None,
        )
        
        request = TranscriptionRequest(
            model="zipformer",
            sample_rate=16000,
            enable_moderation=False,
            session_id="test-session",
            language="vi",
        )
        
        # Act
        results = []
        async for response in use_case.execute(request, create_test_audio_stream()):
            results.append(response)
        
        # Assert
        assert len(results) > 0
        
        # Verify response structure
        for result in results:
            assert hasattr(result, "text")
            assert hasattr(result, "confidence")
            assert result.model_name == "zipformer"
            assert isinstance(result.text, str)
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_worker_is_ready(self, zipformer_worker):
        """Test that worker reports ready status."""
        assert await zipformer_worker.is_ready() is True
    
    @pytest.mark.asyncio
    async def test_worker_processes_audio_data(self, zipformer_worker):
        """Test worker can process AudioData directly."""
        # Arrange
        audio_data = AudioData(
            data=b"\x00" * 32000,
            sample_rate=16000,
            channels=1,
            format="wav",
            duration_ms=1000,
        )
        
        # Act
        results = []
        async for result in zipformer_worker.process_audio_stream(audio_data):
            results.append(result)
        
        # Assert
        assert len(results) > 0
        assert isinstance(results[0], Transcription)


@pytest.mark.slow
class TestModerateContentUseCaseWithSpanDetectorWorker:
    """Test ModerateContentUseCase with real SpanDetectorWorker."""
    
    @pytest.mark.asyncio
    async def test_moderate_clean_text(self, span_detector_worker):
        """Test moderation with clean text."""
        # Skip if model not available
        if not os.path.exists(VISOBERT_MODEL_PATH):
            pytest.skip("ViSoBERT model not available")
        
        # Arrange
        use_case = ModerateContentUseCase(moderation_worker=span_detector_worker)
        
        request = ModerationRequest(text="Xin chào, tôi là trợ lý AI")
        
        # Act
        response = await use_case.execute(request)
        
        # Assert
        assert response is not None
        assert hasattr(response, "label")
        assert hasattr(response, "confidence")
        assert isinstance(response.label, str)
        assert isinstance(response.confidence, float)
        assert 0.0 <= response.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_moderate_offensive_text(self, span_detector_worker):
        """Test moderation with potentially offensive text."""
        if not os.path.exists(VISOBERT_MODEL_PATH):
            pytest.skip("ViSoBERT model not available")
        
        # Arrange
        use_case = ModerateContentUseCase(moderation_worker=span_detector_worker)
        
        # Use a test phrase (note: actual offensive content detection depends on model)
        request = ModerationRequest(text="Test offensive content detection")
        
        # Act
        response = await use_case.execute(request)
        
        # Assert
        assert response is not None
        assert response.label in ["CLEAN", "OFFENSIVE", "HATE"]
        assert 0.0 <= response.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_worker_is_ready(self, span_detector_worker):
        """Test that SpanDetector worker reports ready status."""
        if not os.path.exists(VISOBERT_MODEL_PATH):
            pytest.skip("ViSoBERT model not available")
        
        assert await span_detector_worker.is_ready() is True


@pytest.mark.slow
class TestIntegratedTranscriptionWithModeration:
    """Test full transcription + moderation pipeline."""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_moderation_enabled(
        self,
        zipformer_worker,
        span_detector_worker,
        mock_transcription_repository,
    ):
        """Test transcription with moderation enabled."""
        if not os.path.exists(VISOBERT_MODEL_PATH):
            pytest.skip("ViSoBERT model not available")
        
        # Arrange
        use_case = TranscribeAudioUseCase(
            transcription_repo=mock_transcription_repository,
            transcription_worker=zipformer_worker,
            moderation_worker=span_detector_worker,
        )
        
        request = TranscriptionRequest(
            model="zipformer",
            sample_rate=16000,
            enable_moderation=True,
            session_id="test-session",
            language="vi",
        )
        
        # Act
        results = []
        async for response in use_case.execute(request, create_test_audio_stream()):
            results.append(response)
        
        # Assert
        assert len(results) > 0
        
        # Verify moderation was applied
        for result in results:
            assert result.moderation_label is not None
            assert result.moderation_confidence is not None
            assert result.moderation_label in ["CLEAN", "OFFENSIVE", "HATE"]
            assert 0.0 <= result.moderation_confidence <= 1.0


# ==================== Worker Lifecycle Tests ====================


@pytest.mark.slow
class TestWorkerLifecycle:
    """Test worker start/stop/restart scenarios."""
    
    @pytest.mark.asyncio
    async def test_worker_restart(self):
        """Test worker can be stopped and restarted."""
        # Arrange
        worker = ZipformerWorker(
            worker_id=0,
            model_path=ZIPFORMER_MODEL_PATH,
            num_threads=2,
        )
        
        # Act - Start
        worker.start()
        
        import asyncio
        for _ in range(30):
            if await worker.is_ready():
                break
            await asyncio.sleep(1)
        
        assert await worker.is_ready() is True
        
        # Act - Stop
        worker.stop()
        
        # Wait for worker to stop
        await asyncio.sleep(2)
        
        # Act - Restart
        worker.start()
        
        for _ in range(30):
            if await worker.is_ready():
                break
            await asyncio.sleep(1)
        
        # Assert
        assert await worker.is_ready() is True
        
        # Cleanup
        worker.stop()
    
    @pytest.mark.asyncio
    async def test_worker_handles_shutdown_gracefully(self):
        """Test worker shuts down without errors."""
        # Arrange
        worker = ZipformerWorker(
            worker_id=0,
            model_path=ZIPFORMER_MODEL_PATH,
            num_threads=2,
        )
        
        worker.start()
        
        import asyncio
        for _ in range(30):
            if await worker.is_ready():
                break
            await asyncio.sleep(1)
        
        # Act
        try:
            worker.stop()
            # Should not raise any exceptions
            assert True
        except Exception as e:
            pytest.fail(f"Worker shutdown raised exception: {e}")


# ==================== Performance Tests ====================


@pytest.mark.slow
class TestWorkerPerformance:
    """Test worker performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_transcription_latency(self, zipformer_worker):
        """Test transcription latency is within acceptable bounds."""
        import time
        
        # Arrange
        audio_data = AudioData(
            data=b"\x00" * 32000,  # 1 second of audio
            sample_rate=16000,
            channels=1,
            format="wav",
            duration_ms=1000,
        )
        
        # Act
        start_time = time.time()
        
        results = []
        async for result in zipformer_worker.process_audio_stream(audio_data):
            results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # Assert
        assert len(results) > 0
        # Latency should be < 5 seconds for 1 second of audio
        # (this is a generous bound for testing)
        assert elapsed_time < 5.0, f"Transcription took {elapsed_time}s, expected < 5s"
    
    @pytest.mark.asyncio
    async def test_moderation_latency(self, span_detector_worker):
        """Test moderation latency is within acceptable bounds."""
        if not os.path.exists(VISOBERT_MODEL_PATH):
            pytest.skip("ViSoBERT model not available")
        
        import time
        
        # Arrange
        text = "Xin chào, tôi là trợ lý AI. Tôi có thể giúp gì cho bạn?"
        
        # Act
        start_time = time.time()
        result = await span_detector_worker.moderate(text)
        elapsed_time = time.time() - start_time
        
        # Assert
        assert result is not None
        # Moderation should be < 2 seconds
        assert elapsed_time < 2.0, f"Moderation took {elapsed_time}s, expected < 2s"
