"""
Tests for Delete History Use Cases.

Tests for DeleteHistoryItemUseCase, DeleteAllHistoryUseCase, and
DeleteHistoryByDateRangeUseCase.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from app.application.use_cases.delete_history import (
    DeleteHistoryItemUseCase,
    DeleteAllHistoryUseCase,
    DeleteHistoryByDateRangeUseCase
)
from app.domain.entities import Transcription
from app.domain.exceptions import (
    EntityNotFoundException,
    ValidationException,
    BusinessRuleViolationException
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_repository():
    """Mock transcription repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.delete = AsyncMock()
    repo.get_history = AsyncMock()
    return repo


@pytest.fixture
def mock_cache():
    """Mock cache implementation."""
    cache = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_pattern = AsyncMock()
    cache.clear = AsyncMock()
    return cache


@pytest.fixture
def sample_transcription():
    """Sample transcription entity."""
    return Transcription(
        id=1,
        session_id="test_session",
        model_id="zipformer",
        content="Test transcription",
        latency_ms=100.0,
        created_at=datetime.now(),
        moderation_confidence=0.95
    )


# ==================== DeleteHistoryItemUseCase Tests ====================

class TestDeleteHistoryItemUseCaseConstructor:
    """Tests for DeleteHistoryItemUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_repository(self):
        """Test that repository is required."""
        with pytest.raises(TypeError, match="repository is required"):
            DeleteHistoryItemUseCase(repository=None)
    
    @pytest.mark.asyncio
    async def test_constructor_with_valid_dependencies(self, mock_repository):
        """Test successful initialization."""
        use_case = DeleteHistoryItemUseCase(repository=mock_repository)
        
        assert use_case._repository is mock_repository
        assert use_case._cache is None


class TestDeleteHistoryItemUseCaseValidation:
    """Tests for DeleteHistoryItemUseCase validation."""
    
    @pytest.mark.asyncio
    async def test_validates_zero_id(self, mock_repository):
        """Test that ID = 0 is rejected."""
        use_case = DeleteHistoryItemUseCase(repository=mock_repository)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(transcription_id=0)
        
        assert "transcription_id must be > 0" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_negative_id(self, mock_repository):
        """Test that negative ID is rejected."""
        use_case = DeleteHistoryItemUseCase(repository=mock_repository)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(transcription_id=-5)
        
        assert "transcription_id must be > 0" in str(exc_info.value)


class TestDeleteHistoryItemUseCaseExecution:
    """Tests for DeleteHistoryItemUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_deletes_existing_transcription(
        self,
        mock_repository,
        sample_transcription
    ):
        """Test successful deletion of existing transcription."""
        mock_repository.get_by_id = AsyncMock(return_value=sample_transcription)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteHistoryItemUseCase(repository=mock_repository)
        result = await use_case.execute(transcription_id=1)
        
        # Assert existence check was performed
        mock_repository.get_by_id.assert_called_once_with(1)
        
        # Assert deletion was performed
        mock_repository.delete.assert_called_once_with(1)
        
        # Assert success
        assert result is True
    
    @pytest.mark.asyncio
    async def test_fails_for_nonexistent_transcription(self, mock_repository):
        """Test that deletion fails for non-existent transcription."""
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        use_case = DeleteHistoryItemUseCase(repository=mock_repository)
        
        with pytest.raises(EntityNotFoundException) as exc_info:
            await use_case.execute(transcription_id=999)
        
        # Assert existence check was performed
        mock_repository.get_by_id.assert_called_once_with(999)
        
        # Assert deletion was NOT attempted
        mock_repository.delete.assert_not_called()
        
        # Assert correct exception
        assert "Transcription" in str(exc_info.value)
        assert "999" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalidates_cache_after_deletion(
        self,
        mock_repository,
        mock_cache,
        sample_transcription
    ):
        """Test that cache is invalidated after successful deletion."""
        mock_repository.get_by_id = AsyncMock(return_value=sample_transcription)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteHistoryItemUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        result = await use_case.execute(transcription_id=1)
        
        # Assert deletion was successful
        assert result is True
        
        # Assert specific transcription cache was deleted
        mock_cache.delete.assert_called_once_with("transcription:1")
        
        # Assert history list cache was invalidated
        mock_cache.delete_pattern.assert_called_once_with("history:*")
    
    @pytest.mark.asyncio
    async def test_does_not_invalidate_cache_on_failure(
        self,
        mock_repository,
        mock_cache,
        sample_transcription
    ):
        """Test that cache is NOT invalidated if deletion fails."""
        mock_repository.get_by_id = AsyncMock(return_value=sample_transcription)
        mock_repository.delete = AsyncMock(return_value=False)
        
        use_case = DeleteHistoryItemUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        result = await use_case.execute(transcription_id=1)
        
        # Assert deletion failed
        assert result is False
        
        # Assert cache was NOT invalidated
        mock_cache.delete.assert_not_called()
        mock_cache.delete_pattern.assert_not_called()


# ==================== DeleteAllHistoryUseCase Tests ====================

class TestDeleteAllHistoryUseCaseConstructor:
    """Tests for DeleteAllHistoryUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_repository(self):
        """Test that repository is required."""
        with pytest.raises(TypeError, match="repository is required"):
            DeleteAllHistoryUseCase(repository=None)


class TestDeleteAllHistoryUseCaseSafety:
    """Tests for DeleteAllHistoryUseCase safety checks."""
    
    @pytest.mark.asyncio
    async def test_requires_confirmation(self, mock_repository):
        """Test that deletion requires explicit confirmation."""
        use_case = DeleteAllHistoryUseCase(repository=mock_repository)
        
        with pytest.raises(BusinessRuleViolationException) as exc_info:
            await use_case.execute(confirm=False)
        
        # Assert correct exception
        assert "confirmation" in str(exc_info.value).lower()
        
        # Assert repository was NOT called
        mock_repository.get_history.assert_not_called()
        mock_repository.delete.assert_not_called()


class TestDeleteAllHistoryUseCaseExecution:
    """Tests for DeleteAllHistoryUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_deletes_all_transcriptions(self, mock_repository):
        """Test successful deletion of all transcriptions."""
        # Setup repository with multiple transcriptions
        now = datetime.now()
        transcriptions = [
            Transcription(id=1, session_id="s1", model_id="zipformer", content="First", 
                         latency_ms=100.0, created_at=now, moderation_confidence=0.9),
            Transcription(id=2, session_id="s2", model_id="zipformer", content="Second", 
                         latency_ms=100.0, created_at=now, moderation_confidence=0.9),
            Transcription(id=3, session_id="s3", model_id="zipformer", content="Third", 
                         latency_ms=100.0, created_at=now, moderation_confidence=0.9)
        ]
        mock_repository.get_history = AsyncMock(return_value=transcriptions)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteAllHistoryUseCase(repository=mock_repository)
        count = await use_case.execute(confirm=True)
        
        # Assert all transcriptions were deleted
        assert count == 3
        assert mock_repository.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_history(self, mock_repository):
        """Test that zero is returned when history is empty."""
        mock_repository.get_history = AsyncMock(return_value=[])
        
        use_case = DeleteAllHistoryUseCase(repository=mock_repository)
        count = await use_case.execute(confirm=True)
        
        # Assert no deletions
        assert count == 0
        mock_repository.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_clears_all_cache(self, mock_repository, mock_cache):
        """Test that entire cache is cleared after deletion."""
        now = datetime.now()
        transcriptions = [
            Transcription(id=1, session_id="test", model_id="zipformer", content="Test", 
                         latency_ms=100.0, created_at=now, moderation_confidence=0.9)
        ]
        mock_repository.get_history = AsyncMock(return_value=transcriptions)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteAllHistoryUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        count = await use_case.execute(confirm=True)
        
        # Assert cache was cleared
        mock_cache.clear.assert_called_once()


# ==================== DeleteHistoryByDateRangeUseCase Tests ====================

class TestDeleteHistoryByDateRangeUseCaseConstructor:
    """Tests for DeleteHistoryByDateRangeUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_repository(self):
        """Test that repository is required."""
        with pytest.raises(TypeError, match="repository is required"):
            DeleteHistoryByDateRangeUseCase(repository=None)


class TestDeleteHistoryByDateRangeUseCaseValidation:
    """Tests for DeleteHistoryByDateRangeUseCase validation."""
    
    @pytest.mark.asyncio
    async def test_validates_date_range_order(self, mock_repository):
        """Test that start_date must be before end_date."""
        use_case = DeleteHistoryByDateRangeUseCase(repository=mock_repository)
        
        end_date = datetime.now()
        start_date = end_date + timedelta(days=1)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(start_date=start_date, end_date=end_date)
        
        assert "start_date must be before end_date" in str(exc_info.value)


class TestDeleteHistoryByDateRangeUseCaseExecution:
    """Tests for DeleteHistoryByDateRangeUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_deletes_transcriptions_in_range(self, mock_repository):
        """Test deletion of transcriptions within date range."""
        # Setup transcriptions in range
        transcriptions = [
            Transcription(
                id=1,
                session_id="s1",
                model_id="zipformer",
                content="Old 1",
                latency_ms=100.0,
                created_at=datetime.now() - timedelta(days=10),
                moderation_confidence=0.9
            ),
            Transcription(
                id=2,
                session_id="s2",
                model_id="zipformer",
                content="Old 2",
                latency_ms=100.0,
                created_at=datetime.now() - timedelta(days=5),
                moderation_confidence=0.9
            )
        ]
        mock_repository.get_history = AsyncMock(return_value=transcriptions)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteHistoryByDateRangeUseCase(repository=mock_repository)
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now() - timedelta(days=1)
        
        count = await use_case.execute(start_date=start_date, end_date=end_date)
        
        # Assert correct count
        assert count == 2
        
        # Assert get_history was called with date range
        mock_repository.get_history.assert_called_once()
        call_kwargs = mock_repository.get_history.call_args.kwargs
        assert call_kwargs["start_date"] == start_date
        assert call_kwargs["end_date"] == end_date
    
    @pytest.mark.asyncio
    async def test_deletes_old_transcriptions(self, mock_repository):
        """Test deletion of old transcriptions (before end_date)."""
        old_transcription = Transcription(
            id=1,
            session_id="old_session",
            model_id="zipformer",
            content="Old",
            latency_ms=100.0,
            created_at=datetime.now() - timedelta(days=100),
            moderation_confidence=0.9
        )
        mock_repository.get_history = AsyncMock(return_value=[old_transcription])
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteHistoryByDateRangeUseCase(repository=mock_repository)
        
        # Delete everything older than 30 days
        end_date = datetime.now() - timedelta(days=30)
        count = await use_case.execute(end_date=end_date)
        
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_invalidates_cache_after_deletion(
        self,
        mock_repository,
        mock_cache
    ):
        """Test that cache is invalidated after deletion."""
        now = datetime.now()
        transcriptions = [
            Transcription(id=1, session_id="test", model_id="zipformer", content="Test",
                         latency_ms=100.0, created_at=now, moderation_confidence=0.9)
        ]
        mock_repository.get_history = AsyncMock(return_value=transcriptions)
        mock_repository.delete = AsyncMock(return_value=True)
        
        use_case = DeleteHistoryByDateRangeUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        
        count = await use_case.execute(end_date=datetime.now())
        
        # Assert cache patterns were deleted
        assert mock_cache.delete_pattern.call_count == 2
        calls = [call[0][0] for call in mock_cache.delete_pattern.call_args_list]
        assert "history:*" in calls
        assert "transcription:*" in calls
    
    @pytest.mark.asyncio
    async def test_does_not_invalidate_cache_if_no_deletions(
        self,
        mock_repository,
        mock_cache
    ):
        """Test that cache is not invalidated if no transcriptions deleted."""
        mock_repository.get_history = AsyncMock(return_value=[])
        
        use_case = DeleteHistoryByDateRangeUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        
        count = await use_case.execute(end_date=datetime.now())
        
        # Assert no deletions
        assert count == 0
        
        # Assert cache was not invalidated
        mock_cache.delete_pattern.assert_not_called()
