"""
Tests for History Management Use Cases.

Tests for GetHistoryUseCase, GetHistoryItemUseCase, and related functionality.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta
from pydantic_core import ValidationError as PydanticValidationError

from app.application.use_cases.get_history import (
    GetHistoryUseCase,
    GetHistoryItemUseCase
)
from app.application.dtos.requests import HistoryQueryRequest
from app.domain.entities import Transcription
from app.domain.exceptions import ValidationException


# ==================== Fixtures ====================

@pytest.fixture
def mock_repository():
    """Mock transcription repository."""
    repo = AsyncMock()
    repo.get_history = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_cache():
    """Mock cache implementation."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_pattern = AsyncMock()
    cache.clear = AsyncMock()
    return cache


@pytest.fixture
def sample_transcriptions():
    """Sample transcription entities for testing."""
    return [
        Transcription(
            id=1,
            session_id="session_1",
            model_id="zipformer",
            content="First transcription",
            latency_ms=100.0,
            created_at=datetime.now() - timedelta(days=2),
            moderation_confidence=0.95
        ),
        Transcription(
            id=2,
            session_id="session_2",
            model_id="zipformer",
            content="Second transcription",
            latency_ms=120.0,
            created_at=datetime.now() - timedelta(days=1),
            moderation_confidence=0.92
        ),
        Transcription(
            id=3,
            session_id="session_3",
            model_id="zipformer",
            content="Third transcription",
            latency_ms=90.0,
            created_at=datetime.now(),
            moderation_confidence=0.98
        )
    ]


# ==================== GetHistoryUseCase Tests ====================

class TestGetHistoryUseCaseConstructor:
    """Tests for GetHistoryUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_repository(self):
        """Test that repository is required."""
        with pytest.raises(TypeError, match="repository is required"):
            GetHistoryUseCase(repository=None)
    
    @pytest.mark.asyncio
    async def test_constructor_with_valid_dependencies(self, mock_repository):
        """Test successful initialization with required dependencies."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        assert use_case._repository is mock_repository
        assert use_case._cache is None
    
    @pytest.mark.asyncio
    async def test_constructor_with_optional_cache(self, mock_repository, mock_cache):
        """Test initialization with optional cache."""
        use_case = GetHistoryUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        
        assert use_case._repository is mock_repository
        assert use_case._cache is mock_cache


class TestGetHistoryUseCaseValidation:
    """Tests for GetHistoryUseCase validation logic."""
    
    @pytest.mark.asyncio
    async def test_validates_negative_skip(self, mock_repository):
        """Test that negative skip is rejected by Pydantic validation."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        with pytest.raises(PydanticValidationError) as exc_info:
            request = HistoryQueryRequest(skip=-1, limit=20)
        
        # Pydantic validates at DTO layer, preventing invalid values
        assert "greater_than_equal" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_zero_limit(self, mock_repository):
        """Test that zero limit is rejected by Pydantic validation."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        with pytest.raises(PydanticValidationError) as exc_info:
            request = HistoryQueryRequest(skip=0, limit=0)
        
        # Pydantic validates at DTO layer, preventing invalid values
        assert "greater_than_equal" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_limit_exceeds_maximum(self, mock_repository):
        """Test that limit > 100 is rejected by Pydantic validation."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        with pytest.raises(PydanticValidationError) as exc_info:
            request = HistoryQueryRequest(skip=0, limit=101)
        
        # Pydantic validates at DTO layer, preventing invalid values
        assert "less_than_equal" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_date_range_order(self, mock_repository):
        """Test that start_date must be before end_date."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        end_date = datetime.now()
        start_date = end_date + timedelta(days=1)
        
        request = HistoryQueryRequest(
            skip=0,
            limit=20,
            start_date=start_date,
            end_date=end_date
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(request)
        
        assert "start_date must be before end_date" in str(exc_info.value)


class TestGetHistoryUseCaseExecution:
    """Tests for GetHistoryUseCase execution logic."""
    
    @pytest.mark.asyncio
    async def test_retrieves_history_without_cache(
        self,
        mock_repository,
        sample_transcriptions
    ):
        """Test successful history retrieval without caching."""
        mock_repository.get_history = AsyncMock(return_value=sample_transcriptions)
        
        use_case = GetHistoryUseCase(repository=mock_repository)
        request = HistoryQueryRequest(skip=0, limit=20)
        
        result = await use_case.execute(request)
        
        # Assert repository was called correctly
        mock_repository.get_history.assert_called_once_with(
            skip=0,
            limit=20,
            start_date=None,
            end_date=None
        )
        
        # Assert result is correct
        assert result == sample_transcriptions
        assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_retrieves_history_with_pagination(
        self,
        mock_repository,
        sample_transcriptions
    ):
        """Test history retrieval with pagination."""
        mock_repository.get_history = AsyncMock(
            return_value=sample_transcriptions[1:]
        )
        
        use_case = GetHistoryUseCase(repository=mock_repository)
        request = HistoryQueryRequest(skip=1, limit=2)
        
        result = await use_case.execute(request)
        
        # Assert pagination parameters were passed
        mock_repository.get_history.assert_called_once_with(
            skip=1,
            limit=2,
            start_date=None,
            end_date=None
        )
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_retrieves_history_with_date_filter(
        self,
        mock_repository,
        sample_transcriptions
    ):
        """Test history retrieval with date range filter."""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        mock_repository.get_history = AsyncMock(return_value=sample_transcriptions)
        
        use_case = GetHistoryUseCase(repository=mock_repository)
        request = HistoryQueryRequest(
            skip=0,
            limit=20,
            start_date=start_date,
            end_date=end_date
        )
        
        result = await use_case.execute(request)
        
        # Assert date filters were passed
        mock_repository.get_history.assert_called_once_with(
            skip=0,
            limit=20,
            start_date=start_date,
            end_date=end_date
        )
    
    @pytest.mark.asyncio
    async def test_returns_cached_result_if_available(
        self,
        mock_repository,
        mock_cache,
        sample_transcriptions
    ):
        """Test that cached results are returned without hitting repository."""
        # Setup cache to return cached data
        mock_cache.get = AsyncMock(return_value=sample_transcriptions)
        
        use_case = GetHistoryUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        request = HistoryQueryRequest(skip=0, limit=20)
        
        result = await use_case.execute(request)
        
        # Assert cache was checked
        mock_cache.get.assert_called_once()
        
        # Assert repository was NOT called
        mock_repository.get_history.assert_not_called()
        
        # Assert cached result was returned
        assert result == sample_transcriptions
    
    @pytest.mark.asyncio
    async def test_caches_result_after_retrieval(
        self,
        mock_repository,
        mock_cache,
        sample_transcriptions
    ):
        """Test that results are cached after retrieval from repository."""
        mock_repository.get_history = AsyncMock(return_value=sample_transcriptions)
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss
        
        use_case = GetHistoryUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        request = HistoryQueryRequest(skip=0, limit=20)
        
        result = await use_case.execute(request)
        
        # Assert cache was checked
        mock_cache.get.assert_called_once()
        
        # Assert repository was called
        mock_repository.get_history.assert_called_once()
        
        # Assert result was cached
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][1] == sample_transcriptions  # Cached value
        assert call_args[1]["ttl"] == 300  # 5 minutes TTL


class TestGetHistoryUseCaseCacheKey:
    """Tests for cache key generation."""
    
    @pytest.mark.asyncio
    async def test_generates_cache_key_with_basic_params(self, mock_repository):
        """Test cache key generation with basic parameters."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        request = HistoryQueryRequest(skip=0, limit=20)
        
        cache_key = use_case._generate_cache_key(request)
        
        assert cache_key == "history:skip:0:limit:20"
    
    @pytest.mark.asyncio
    async def test_generates_cache_key_with_dates(self, mock_repository):
        """Test cache key generation with date filters."""
        use_case = GetHistoryUseCase(repository=mock_repository)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        request = HistoryQueryRequest(
            skip=0,
            limit=20,
            start_date=start_date,
            end_date=end_date
        )
        
        cache_key = use_case._generate_cache_key(request)
        
        assert "history:skip:0:limit:20" in cache_key
        assert "start:2024-01-01" in cache_key
        assert "end:2024-12-31" in cache_key


# ==================== GetHistoryItemUseCase Tests ====================

class TestGetHistoryItemUseCaseConstructor:
    """Tests for GetHistoryItemUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_repository(self):
        """Test that repository is required."""
        with pytest.raises(TypeError, match="repository is required"):
            GetHistoryItemUseCase(repository=None)
    
    @pytest.mark.asyncio
    async def test_constructor_with_valid_dependencies(self, mock_repository):
        """Test successful initialization."""
        use_case = GetHistoryItemUseCase(repository=mock_repository)
        
        assert use_case._repository is mock_repository
        assert use_case._cache is None


class TestGetHistoryItemUseCaseValidation:
    """Tests for GetHistoryItemUseCase validation."""
    
    @pytest.mark.asyncio
    async def test_validates_zero_id(self, mock_repository):
        """Test that ID = 0 is rejected."""
        use_case = GetHistoryItemUseCase(repository=mock_repository)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(transcription_id=0)
        
        assert "transcription_id must be > 0" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_negative_id(self, mock_repository):
        """Test that negative ID is rejected."""
        use_case = GetHistoryItemUseCase(repository=mock_repository)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(transcription_id=-5)
        
        assert "transcription_id must be > 0" in str(exc_info.value)


class TestGetHistoryItemUseCaseExecution:
    """Tests for GetHistoryItemUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_retrieves_existing_transcription(
        self,
        mock_repository,
        sample_transcriptions
    ):
        """Test successful retrieval of existing transcription."""
        transcription = sample_transcriptions[0]
        mock_repository.get_by_id = AsyncMock(return_value=transcription)
        
        use_case = GetHistoryItemUseCase(repository=mock_repository)
        result = await use_case.execute(transcription_id=1)
        
        # Assert repository was called
        mock_repository.get_by_id.assert_called_once_with(1)
        
        # Assert result is correct
        assert result == transcription
        assert result.id == 1
    
    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_transcription(self, mock_repository):
        """Test that None is returned for non-existent transcription."""
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        use_case = GetHistoryItemUseCase(repository=mock_repository)
        result = await use_case.execute(transcription_id=999)
        
        mock_repository.get_by_id.assert_called_once_with(999)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_returns_cached_transcription(
        self,
        mock_repository,
        mock_cache,
        sample_transcriptions
    ):
        """Test that cached transcription is returned without hitting repository."""
        transcription = sample_transcriptions[0]
        mock_cache.get = AsyncMock(return_value=transcription)
        
        use_case = GetHistoryItemUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        result = await use_case.execute(transcription_id=1)
        
        # Assert cache was checked
        mock_cache.get.assert_called_once_with("transcription:1")
        
        # Assert repository was NOT called
        mock_repository.get_by_id.assert_not_called()
        
        # Assert cached result was returned
        assert result == transcription
    
    @pytest.mark.asyncio
    async def test_caches_transcription_after_retrieval(
        self,
        mock_repository,
        mock_cache,
        sample_transcriptions
    ):
        """Test that transcription is cached after retrieval."""
        transcription = sample_transcriptions[0]
        mock_repository.get_by_id = AsyncMock(return_value=transcription)
        mock_cache.get = AsyncMock(return_value=None)  # Cache miss
        
        use_case = GetHistoryItemUseCase(
            repository=mock_repository,
            cache=mock_cache
        )
        result = await use_case.execute(transcription_id=1)
        
        # Assert repository was called
        mock_repository.get_by_id.assert_called_once_with(1)
        
        # Assert result was cached
        mock_cache.set.assert_called_once_with(
            "transcription:1",
            transcription,
            ttl=600  # 10 minutes
        )
