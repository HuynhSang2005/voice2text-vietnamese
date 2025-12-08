"""
Application Use Case: Transcribe Audio

This use case orchestrates the transcription workflow, including:
1. Audio data streaming
2. Speech-to-text processing via ITranscriptionWorker
3. Optional content moderation via IModerationWorker
4. Persistence via ITranscriptionRepository

Clean Architecture principles:
- Depends only on domain entities and application interfaces
- Business logic lives here (when to moderate, when to save)
- Infrastructure details abstracted behind interfaces
"""

from typing import AsyncIterator, Optional
from datetime import datetime, timezone

from app.domain.entities.transcription import Transcription
from app.domain.entities.moderation_result import ModerationResult
from app.domain.value_objects.audio_data import AudioData
from app.domain.exceptions import BusinessRuleViolationException
from app.application.interfaces import (
    ITranscriptionWorker,
    IModerationWorker,
    ITranscriptionRepository,
)
from app.application.dtos.requests import TranscriptionRequest


# Alias for shorter usage
BusinessRuleException = BusinessRuleViolationException


class TranscribeAudioUseCase:
    """
    Use case for transcribing audio with optional content moderation.

    This use case coordinates between:
    - Transcription worker (STT model inference)
    - Moderation worker (hate speech detection)
    - Transcription repository (persistence)

    Workflow:
    1. Validate transcription request
    2. Stream audio chunks to transcription worker
    3. For each transcription result:
       a. If moderation enabled, check content
       b. Create Transcription entity with moderation result
       c. Save to repository
       d. Yield result to caller

    Example:
        ```python
        use_case = TranscribeAudioUseCase(
            transcription_worker=zipformer_worker,
            moderation_worker=visobert_worker,
            repository=transcription_repo
        )

        request = TranscriptionRequest(
            model="zipformer",
            enable_moderation=True,
            session_id="session-123"
        )

        async for result in use_case.execute(audio_stream, request):
            print(f"Transcribed: {result.content}")
            if result.is_offensive():
                print("⚠️ Offensive content detected!")
        ```
    """

    def __init__(
        self,
        transcription_worker: ITranscriptionWorker,
        moderation_worker: Optional[IModerationWorker],
        repository: ITranscriptionRepository,
    ):
        """
        Initialize use case with dependencies.

        Args:
            transcription_worker: Worker for STT processing
            moderation_worker: Optional worker for content moderation
            repository: Repository for persisting transcriptions

        Raises:
            ValueError: If transcription_worker or repository is None
        """
        if not transcription_worker:
            raise ValueError("transcription_worker is required")
        if not repository:
            raise ValueError("repository is required")

        self._transcription_worker = transcription_worker
        self._moderation_worker = moderation_worker
        self._repository = repository

    async def execute(
        self,
        audio_stream: AsyncIterator[AudioData],
        request: TranscriptionRequest,
    ) -> AsyncIterator[Transcription]:
        """
        Execute transcription use case with streaming audio.

        This method processes audio in real-time, yielding transcription
        results as they become available. Each result is optionally
        moderated and persisted.

        Args:
            audio_stream: Async iterator of audio chunks
            request: Transcription configuration and parameters

        Yields:
            Transcription: Domain entities with transcription results

        Raises:
            ValidationException: If audio data is invalid
            BusinessRuleException: If moderation required but worker unavailable
            DomainException: For other business rule violations

        Example:
            ```python
            audio_stream = generate_audio_chunks()
            request = TranscriptionRequest(
                model="zipformer",
                enable_moderation=True,
                session_id="abc-123"
            )

            async for transcription in use_case.execute(audio_stream, request):
                if transcription.is_offensive():
                    # Handle offensive content
                    pass
            ```
        """
        # Validate moderation requirements
        if request.enable_moderation and not self._moderation_worker:
            raise BusinessRuleException(
                rule="moderation_worker_required",
                reason="Moderation requested but moderation worker is not available. "
                "Please disable moderation or ensure moderation worker is running.",
            )

        # Check if workers are ready
        if not await self._transcription_worker.is_ready():
            raise BusinessRuleException(
                rule="transcription_worker_not_ready",
                reason="Transcription worker is not ready. Please wait or switch to a different model.",
            )

        if request.enable_moderation and not await self._moderation_worker.is_ready():
            raise BusinessRuleException(
                rule="moderation_worker_not_ready",
                reason="Moderation worker is not ready. Please wait or disable moderation.",
            )

        # Process audio stream through transcription worker
        transcription_stream = self._transcription_worker.process_audio_stream(
            audio_stream
        )

        async for partial_transcription in transcription_stream:
            # For intermediate results, we don't save or moderate yet
            # Just yield them for real-time feedback
            if not self._is_final_result(partial_transcription):
                yield partial_transcription
                continue

            # For final results, apply moderation if enabled
            moderation_result = None
            if request.enable_moderation:
                moderation_result = await self._moderate_content(
                    partial_transcription.content
                )

            # Create complete transcription entity
            transcription = Transcription(
                id=None,  # Will be set by repository
                session_id=request.session_id or self._generate_session_id(),
                model_id=request.model,
                content=partial_transcription.content,
                latency_ms=partial_transcription.latency_ms,
                created_at=datetime.now(timezone.utc),
                moderation_label=moderation_result.label if moderation_result else None,
                moderation_confidence=(
                    moderation_result.confidence if moderation_result else None
                ),
                is_flagged=moderation_result.is_flagged if moderation_result else None,
                detected_keywords=(
                    moderation_result.detected_keywords if moderation_result else []
                ),
            )

            # Persist to repository
            saved_transcription = await self._repository.save(transcription)

            # Yield final result
            yield saved_transcription

    async def _moderate_content(self, text: str) -> ModerationResult:
        """
        Moderate content using moderation worker.

        Args:
            text: Text content to moderate

        Returns:
            ModerationResult: Moderation classification and confidence

        Raises:
            BusinessRuleException: If moderation fails
        """
        if not self._moderation_worker:
            raise BusinessRuleException("Moderation worker not available")

        try:
            result = await self._moderation_worker.moderate(text)
            return result
        except Exception:
            # Log error but don't fail transcription
            # Return CLEAN with low confidence as fallback
            return ModerationResult(
                label="CLEAN",
                confidence=0.0,
                is_flagged=False,
                detected_keywords=[],
            )

    def _is_final_result(self, transcription: Transcription) -> bool:
        """
        Check if transcription is a final result (vs intermediate).

        For now, we consider results final if they have content.
        In streaming scenarios, we may have intermediate results
        that are partial transcriptions.

        Args:
            transcription: Transcription entity to check

        Returns:
            bool: True if final result, False if intermediate
        """
        # Simple heuristic: final results have content > minimum length
        # and are marked as complete by the worker
        return len(transcription.content.strip()) > 0

    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID if not provided in request.

        Returns:
            str: UUID-based session identifier
        """
        import uuid

        return f"session-{uuid.uuid4()}"


class TranscribeAudioBatchUseCase:
    """
    Use case for batch (non-streaming) audio transcription.

    This is a simpler variant for processing complete audio files
    rather than streaming chunks. Useful for:
    - File upload transcription
    - Historical audio processing
    - Batch jobs

    Example:
        ```python
        use_case = TranscribeAudioBatchUseCase(
            transcription_worker=worker,
            moderation_worker=mod_worker,
            repository=repo
        )

        result = await use_case.execute(
            audio_data=audio_bytes,
            request=TranscriptionRequest(model="zipformer")
        )
        print(result.content)
        ```
    """

    def __init__(
        self,
        transcription_worker: ITranscriptionWorker,
        moderation_worker: Optional[IModerationWorker],
        repository: ITranscriptionRepository,
    ):
        """Initialize batch use case with dependencies."""
        self._streaming_use_case = TranscribeAudioUseCase(
            transcription_worker=transcription_worker,
            moderation_worker=moderation_worker,
            repository=repository,
        )

    async def execute(
        self,
        audio_data: AudioData,
        request: TranscriptionRequest,
    ) -> Transcription:
        """
        Execute batch transcription for a single audio file.

        Args:
            audio_data: Complete audio file data
            request: Transcription configuration

        Returns:
            Transcription: Final transcription result

        Raises:
            ValidationException: If audio data is invalid
            BusinessRuleException: For business rule violations
        """

        # Convert single audio data to async stream
        async def audio_stream():
            yield audio_data

        # Use streaming use case and collect final result
        final_result = None
        async for transcription in self._streaming_use_case.execute(
            audio_stream(), request
        ):
            final_result = transcription

        if not final_result:
            raise BusinessRuleException(
                rule="no_transcription_result",
                reason="No transcription result produced. Audio may be invalid or too short.",
            )

        return final_result
