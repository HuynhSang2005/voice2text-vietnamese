"""
Delete History Item Use Case - Remove transcription records.

This module implements the business logic for deleting transcription records
from the repository, with optional cache invalidation.
"""

from typing import Optional

from app.domain.repositories.transcription_repository import ITranscriptionRepository
from app.application.interfaces.cache import ICache
from app.domain.exceptions import (
    EntityNotFoundException,
    ValidationException,
    BusinessRuleViolationException,
)


class DeleteHistoryItemUseCase:
    """
    Use case for deleting a single transcription record.

    Supports hard delete (permanent removal) and invalidates cache if available.

    Example:
        ```python
        use_case = DeleteHistoryItemUseCase(repository=repo, cache=cache)
        success = await use_case.execute(transcription_id=123)
        ```
    """

    def __init__(
        self, repository: ITranscriptionRepository, cache: Optional[ICache] = None
    ):
        """
        Initialize the use case with dependencies.

        Args:
            repository: Repository for accessing transcription data
            cache: Optional cache for invalidation

        Raises:
            TypeError: If repository is None
        """
        if not repository:
            raise TypeError("repository is required")

        self._repository = repository
        self._cache = cache

    async def execute(self, transcription_id: int) -> bool:
        """
        Execute the use case to delete a transcription.

        Permanently removes the transcription from the repository and
        invalidates any cached entries.

        Args:
            transcription_id: ID of the transcription to delete

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            ValidationException: If transcription_id is invalid
            EntityNotFoundException: If transcription doesn't exist

        Example:
            ```python
            success = await use_case.execute(transcription_id=123)
            if success:
                print("Transcription deleted successfully")
            ```
        """
        # Validate ID
        if transcription_id <= 0:
            raise ValidationException(
                field="transcription_id",
                value=transcription_id,
                constraint="transcription_id must be > 0",
            )

        # Check if transcription exists
        existing = await self._repository.get_by_id(transcription_id)
        if not existing:
            raise EntityNotFoundException(
                entity_type="Transcription", entity_id=transcription_id
            )

        # Delete from repository
        success = await self._repository.delete(transcription_id)

        # Invalidate cache if available and deletion was successful
        if success and self._cache:
            await self._invalidate_cache(transcription_id)

        return success

    async def _invalidate_cache(self, transcription_id: int) -> None:
        """
        Invalidate cache entries related to the deleted transcription.

        Args:
            transcription_id: ID of the deleted transcription
        """
        # Invalidate specific transcription cache
        cache_key = f"transcription:{transcription_id}"
        await self._cache.delete(cache_key)

        # Invalidate history list caches (pattern-based)
        # This ensures that any cached history lists are refreshed
        await self._cache.delete_pattern("history:*")


class DeleteAllHistoryUseCase:
    """
    Use case for deleting all transcription records.

    WARNING: This permanently removes all transcription history.
    Use with caution.

    Example:
        ```python
        use_case = DeleteAllHistoryUseCase(repository=repo, cache=cache)
        count = await use_case.execute(confirm=True)
        ```
    """

    def __init__(
        self, repository: ITranscriptionRepository, cache: Optional[ICache] = None
    ):
        """
        Initialize the use case with dependencies.

        Args:
            repository: Repository for accessing transcription data
            cache: Optional cache for invalidation

        Raises:
            TypeError: If repository is None
        """
        if not repository:
            raise TypeError("repository is required")

        self._repository = repository
        self._cache = cache

    async def execute(self, confirm: bool = False) -> int:
        """
        Execute the use case to delete all transcriptions.

        Args:
            confirm: Must be True to proceed with deletion (safety check)

        Returns:
            Number of transcriptions deleted

        Raises:
            BusinessRuleViolationException: If confirm is not True

        Example:
            ```python
            # This will raise an exception
            await use_case.execute(confirm=False)

            # This will proceed with deletion
            count = await use_case.execute(confirm=True)
            print(f"Deleted {count} transcriptions")
            ```
        """
        # Safety check - require explicit confirmation
        if not confirm:
            raise BusinessRuleViolationException(
                rule="delete_all_confirmation_required",
                reason="Deleting all history requires explicit confirmation. "
                "Pass confirm=True to proceed.",
            )

        # Get count before deletion for return value
        all_history = await self._repository.get_history(skip=0, limit=1000000)
        count = len(all_history)

        # Delete all transcriptions
        for transcription in all_history:
            await self._repository.delete(transcription.id)

        # Clear all cache if available
        if self._cache:
            await self._cache.clear()

        return count


class DeleteHistoryByDateRangeUseCase:
    """
    Use case for deleting transcriptions within a date range.

    Allows bulk deletion of old transcriptions while preserving recent ones.

    Example:
        ```python
        use_case = DeleteHistoryByDateRangeUseCase(repository=repo, cache=cache)
        count = await use_case.execute(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30)
        )
        ```
    """

    def __init__(
        self, repository: ITranscriptionRepository, cache: Optional[ICache] = None
    ):
        """
        Initialize the use case with dependencies.

        Args:
            repository: Repository for accessing transcription data
            cache: Optional cache for invalidation

        Raises:
            TypeError: If repository is None
        """
        if not repository:
            raise TypeError("repository is required")

        self._repository = repository
        self._cache = cache

    async def execute(
        self, start_date: Optional[object] = None, end_date: Optional[object] = None
    ) -> int:
        """
        Execute the use case to delete transcriptions in date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Number of transcriptions deleted

        Raises:
            ValidationException: If date range is invalid

        Example:
            ```python
            from datetime import datetime, timedelta

            # Delete all transcriptions older than 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            count = await use_case.execute(end_date=thirty_days_ago)
            ```
        """
        # Validate date range
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationException(
                    field="start_date",
                    value=start_date,
                    constraint="start_date must be before end_date",
                )

        # Get transcriptions in range
        history = await self._repository.get_history(
            skip=0, limit=1000000, start_date=start_date, end_date=end_date
        )

        # Delete each transcription
        count = 0
        for transcription in history:
            success = await self._repository.delete(transcription.id)
            if success:
                count += 1

        # Clear cache if available
        if self._cache and count > 0:
            await self._cache.delete_pattern("history:*")
            await self._cache.delete_pattern("transcription:*")

        return count
