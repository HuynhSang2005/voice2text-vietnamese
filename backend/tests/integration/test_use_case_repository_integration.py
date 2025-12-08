"""
Integration tests for Use Case → Repository interactions.

Tests verify end-to-end data flow from application layer to infrastructure:
- TranscribeAudioUseCase with real TranscriptionRepositoryImpl
- GetHistoryUseCase with real TranscriptionRepositoryImpl
- DeleteHistoryUseCase with real TranscriptionRepositoryImpl
- Real database interactions (SQLite)
- Transaction handling
- Error propagation

These tests use real repository implementations but mock workers.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from app.application.use_cases.transcribe_audio import TranscribeAudioUseCase
from app.application.use_cases.get_history import GetHistoryUseCase
from app.application.use_cases.delete_history import DeleteHistoryItemUseCase
from app.application.dtos.requests import TranscriptionRequest, HistoryQueryRequest
from app.infrastructure.database.repositories.transcription_repo_impl import (
    TranscriptionRepositoryImpl,
)
from app.domain.entities.transcription import Transcription
from app.domain.entities.moderation_result import ModerationResult
from app.domain.value_objects.audio_data import AudioData


# ==================== Database Fixtures ====================


@pytest_asyncio.fixture
async def test_db_engine():
    """Create test database engine (in-memory SQLite)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session_maker = sessionmaker(
        test_db_engine,
        class_=SQLModelAsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def transcription_repository(test_db_session):
    """Create real TranscriptionRepositoryImpl with test database."""
    return TranscriptionRepositoryImpl(session=test_db_session)


# ==================== Mock Worker Fixtures ====================


@pytest.fixture
def mock_transcription_worker():
    """Mock ITranscriptionWorker for testing."""
    worker = AsyncMock()
    worker.is_ready = AsyncMock(return_value=True)
    
    async def mock_process_stream(audio_data: AudioData):
        """Simulate streaming transcription results."""
        # Yield multiple results to simulate streaming
        yield Transcription(
            id=None,
            text="Xin chào",
            confidence=0.95,
            model_name="zipformer",
            audio_duration_ms=audio_data.duration_ms,
            session_id="test-session",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        yield Transcription(
            id=None,
            text="Tôi là trợ lý AI",
            confidence=0.92,
            model_name="zipformer",
            audio_duration_ms=audio_data.duration_ms,
            session_id="test-session",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
    
    worker.process_audio_stream = mock_process_stream
    return worker


@pytest.fixture
def mock_moderation_worker():
    """Mock IModerationWorker for testing."""
    worker = AsyncMock()
    worker.is_ready = AsyncMock(return_value=True)
    
    async def mock_moderate(text: str):
        """Simulate moderation results."""
        return ModerationResult(
            text=text,
            label="CLEAN",
            confidence=0.98,
            spans=[],
        )
    
    worker.moderate = mock_moderate
    return worker


# ==================== Helper Functions ====================


async def create_audio_stream() -> AsyncIterator[AudioData]:
    """Create sample audio stream for testing."""
    for i in range(2):
        yield AudioData(
            data=f"audio_chunk_{i}".encode(),
            sample_rate=16000,
            channels=1,
            format="wav",
            duration_ms=1000,
        )


# ==================== Test Cases ====================


class TestTranscribeAudioUseCaseWithRepository:
    """Test TranscribeAudioUseCase with real repository."""
    
    @pytest.mark.asyncio
    async def test_transcribe_saves_to_database(
        self,
        transcription_repository,
        mock_transcription_worker,
    ):
        """Test that transcription results are saved to database."""
        # Arrange
        use_case = TranscribeAudioUseCase(
            transcription_repo=transcription_repository,
            transcription_worker=mock_transcription_worker,
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
        async for response in use_case.execute(request, create_audio_stream()):
            results.append(response)
        
        # Assert
        assert len(results) == 2
        assert results[0].text == "Xin chào"
        assert results[1].text == "Tôi là trợ lý AI"
        
        # Verify data persisted to database
        history = await transcription_repository.list(skip=0, limit=10)
        assert len(history) == 2
        assert history[0].text in ["Xin chào", "Tôi là trợ lý AI"]
        assert history[1].text in ["Xin chào", "Tôi là trợ lý AI"]
    
    @pytest.mark.asyncio
    async def test_transcribe_with_moderation_saves_labels(
        self,
        transcription_repository,
        mock_transcription_worker,
        mock_moderation_worker,
    ):
        """Test transcription with moderation saves moderation labels."""
        # Arrange
        use_case = TranscribeAudioUseCase(
            transcription_repo=transcription_repository,
            transcription_worker=mock_transcription_worker,
            moderation_worker=mock_moderation_worker,
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
        async for response in use_case.execute(request, create_audio_stream()):
            results.append(response)
        
        # Assert
        assert len(results) == 2
        
        # Verify moderation labels saved
        history = await transcription_repository.list(skip=0, limit=10)
        for item in history:
            assert item.moderation_label == "CLEAN"
            assert item.moderation_confidence == 0.98


class TestGetHistoryUseCaseWithRepository:
    """Test GetHistoryUseCase with real repository."""
    
    @pytest.mark.asyncio
    async def test_get_history_retrieves_from_database(
        self,
        transcription_repository,
    ):
        """Test that GetHistoryUseCase retrieves data from database."""
        # Arrange - populate database
        transcription1 = Transcription(
            id=None,
            text="First transcription",
            confidence=0.95,
            model_name="zipformer",
            audio_duration_ms=1000,
            session_id="session-1",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        transcription2 = Transcription(
            id=None,
            text="Second transcription",
            confidence=0.92,
            model_name="zipformer",
            audio_duration_ms=2000,
            session_id="session-1",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        
        await transcription_repository.save(transcription1)
        await transcription_repository.save(transcription2)
        
        # Create use case
        use_case = GetHistoryUseCase(transcription_repo=transcription_repository)
        
        request = HistoryQueryRequest(skip=0, limit=10)
        
        # Act
        response = await use_case.execute(request)
        
        # Assert
        assert response.total == 2
        assert len(response.items) == 2
        assert response.items[0].text in ["First transcription", "Second transcription"]
        assert response.items[1].text in ["First transcription", "Second transcription"]
    
    @pytest.mark.asyncio
    async def test_get_history_pagination(
        self,
        transcription_repository,
    ):
        """Test pagination in GetHistoryUseCase."""
        # Arrange - populate with 5 items
        for i in range(5):
            transcription = Transcription(
                id=None,
                text=f"Transcription {i}",
                confidence=0.95,
                model_name="zipformer",
                audio_duration_ms=1000,
                session_id="session-1",
                language="vi",
                moderation_label=None,
                moderation_confidence=None,
                created_at=datetime.now(timezone.utc),
            )
            await transcription_repository.save(transcription)
        
        use_case = GetHistoryUseCase(transcription_repo=transcription_repository)
        
        # Act - get first page (2 items)
        request = HistoryQueryRequest(skip=0, limit=2)
        response = await use_case.execute(request)
        
        # Assert
        assert response.total == 5
        assert len(response.items) == 2
        assert response.skip == 0
        assert response.limit == 2


class TestDeleteHistoryUseCaseWithRepository:
    """Test DeleteHistoryItemUseCase with real repository."""
    
    @pytest.mark.asyncio
    async def test_delete_removes_from_database(
        self,
        transcription_repository,
    ):
        """Test that DeleteHistoryItemUseCase removes data from database."""
        # Arrange - populate database
        transcription = Transcription(
            id=None,
            text="To be deleted",
            confidence=0.95,
            model_name="zipformer",
            audio_duration_ms=1000,
            session_id="session-1",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        
        saved = await transcription_repository.save(transcription)
        transcription_id = saved.id
        
        # Verify it exists
        found = await transcription_repository.get_by_id(transcription_id)
        assert found is not None
        
        # Create use case
        use_case = DeleteHistoryItemUseCase(transcription_repo=transcription_repository)
        
        # Act
        await use_case.execute(transcription_id)
        
        # Assert
        deleted = await transcription_repository.get_by_id(transcription_id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_id_raises_error(
        self,
        transcription_repository,
    ):
        """Test deleting non-existent ID raises error."""
        # Arrange
        use_case = DeleteHistoryItemUseCase(transcription_repo=transcription_repository)
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise EntityNotFoundException
            await use_case.execute(999999)


# ==================== Transaction Tests ====================


class TestRepositoryTransactions:
    """Test transaction handling in repository."""
    
    @pytest.mark.asyncio
    async def test_rollback_on_error(
        self,
        transcription_repository,
        test_db_session,
    ):
        """Test that errors trigger rollback."""
        # Arrange
        transcription = Transcription(
            id=None,
            text="Test transcription",
            confidence=0.95,
            model_name="zipformer",
            audio_duration_ms=1000,
            session_id="session-1",
            language="vi",
            moderation_label=None,
            moderation_confidence=None,
            created_at=datetime.now(timezone.utc),
        )
        
        # Act - force an error during save
        with pytest.raises(Exception):
            # Simulate error by passing invalid data
            transcription.confidence = None  # This should fail validation
            await transcription_repository.save(transcription)
        
        # Assert - verify nothing was saved
        history = await transcription_repository.list(skip=0, limit=10)
        assert len(history) == 0
