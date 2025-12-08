"""
Get History Use Case - Retrieve transcription history with pagination and filtering.

This module implements the business logic for retrieving transcription history
from the repository, with support for pagination, filtering, and optional caching.
"""

from typing import List, Optional


from app.domain.entities import Transcription
from app.domain.repositories.transcription_repository import ITranscriptionRepository
from app.application.interfaces.cache import ICache
from app.application.dtos.requests import HistoryQueryRequest
from app.domain.exceptions import ValidationException


class GetHistoryUseCase:
    """
    Use case for retrieving transcription history.

    Supports pagination, filtering by date range, and optional caching
    for improved performance.

    Example:
        ```python
        use_case = GetHistoryUseCase(repository=repo, cache=cache)
        request = HistoryQueryRequest(skip=0, limit=20)
        history = await use_case.execute(request)
        ```
    """

    def __init__(
        self, repository: ITranscriptionRepository, cache: Optional[ICache] = None
    ):
        """
        Initialize the use case with dependencies.

        Args:
            repository: Repository for accessing transcription data
            cache: Optional cache for improved performance

        Raises:
            TypeError: If repository is None
        """
        if not repository:
            raise TypeError("repository is required")

        self._repository = repository
        self._cache = cache

    async def execute(self, request: HistoryQueryRequest) -> List[Transcription]:
        """
        Execute the use case to retrieve history.

        Retrieves transcription history based on the request parameters,
        with optional caching for frequently accessed data.

        Args:
            request: Query parameters (pagination, filters)

        Returns:
            List of Transcription entities matching the criteria

        Raises:
            ValidationException: If request parameters are invalid

        Example:
            ```python
            request = HistoryQueryRequest(
                skip=0,
                limit=20,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31)
            )
            history = await use_case.execute(request)
            ```
        """
        # Validate pagination parameters
        if request.skip < 0:
            raise ValidationException(
                field="skip", value=request.skip, constraint="skip must be >= 0"
            )

        if request.limit <= 0:
            raise ValidationException(
                field="limit", value=request.limit, constraint="limit must be > 0"
            )

        if request.limit > 100:
            raise ValidationException(
                field="limit", value=request.limit, constraint="limit must be <= 100"
            )

        # Validate date range if provided
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise ValidationException(
                    field="start_date",
                    value=request.start_date,
                    constraint="start_date must be before end_date",
                )

        # Check cache if available
        if self._cache:
            cache_key = self._generate_cache_key(request)
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                return cached_result

        # Query repository
        history = await self._repository.get_history(
            skip=request.skip,
            limit=request.limit,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        # Cache the result if cache is available
        if self._cache and history:
            cache_key = self._generate_cache_key(request)
            await self._cache.set(cache_key, history, ttl=300)  # Cache for 5 minutes

        return history

    def _generate_cache_key(self, request: HistoryQueryRequest) -> str:
        """
        Generate a cache key from the request parameters.

        Args:
            request: Query request

        Returns:
            Cache key string
        """
        parts = ["history", f"skip:{request.skip}", f"limit:{request.limit}"]

        if request.start_date:
            parts.append(f"start:{request.start_date.isoformat()}")

        if request.end_date:
            parts.append(f"end:{request.end_date.isoformat()}")

        return ":".join(parts)


class GetHistoryItemUseCase:
    """
    Use case for retrieving a single transcription by ID.

    Example:
        ```python
        use_case = GetHistoryItemUseCase(repository=repo, cache=cache)
        transcription = await use_case.execute(transcription_id=123)
        ```
    """

    def __init__(
        self, repository: ITranscriptionRepository, cache: Optional[ICache] = None
    ):
        """
        Initialize the use case with dependencies.

        Args:
            repository: Repository for accessing transcription data
            cache: Optional cache for improved performance

        Raises:
            TypeError: If repository is None
        """
        if not repository:
            raise TypeError("repository is required")

        self._repository = repository
        self._cache = cache

    async def execute(self, transcription_id: int) -> Optional[Transcription]:
        """
        Execute the use case to retrieve a single transcription.

        Args:
            transcription_id: ID of the transcription to retrieve

        Returns:
            Transcription entity if found, None otherwise

        Raises:
            ValidationException: If transcription_id is invalid

        Example:
            ```python
            transcription = await use_case.execute(transcription_id=123)
            if transcription:
                print(f"Found: {transcription.content}")
            ```
        """
        # Validate ID
        if transcription_id <= 0:
            raise ValidationException(
                field="transcription_id",
                value=transcription_id,
                constraint="transcription_id must be > 0",
            )

        # Check cache if available
        if self._cache:
            cache_key = f"transcription:{transcription_id}"
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                return cached_result

        # Query repository
        transcription = await self._repository.get_by_id(transcription_id)

        # Cache the result if found and cache is available
        if self._cache and transcription:
            cache_key = f"transcription:{transcription_id}"
            await self._cache.set(
                cache_key, transcription, ttl=600  # Cache for 10 minutes
            )

        return transcription
