"""
Application Layer - Worker Interfaces

This module defines Protocol interfaces for worker abstractions.
These interfaces are implemented by the Infrastructure layer.

Following Clean Architecture:
- Application defines WHAT workers should do (interfaces)
- Infrastructure defines HOW workers do it (implementations)
"""

from typing import Protocol, AsyncIterator, Optional
from app.domain.entities.transcription import Transcription
from app.domain.entities.moderation_result import ModerationResult
from app.domain.value_objects.audio_data import AudioData
from app.domain.value_objects.model_config import ModelConfig


class ITranscriptionWorker(Protocol):
    """
    Interface for speech-to-text transcription workers.

    Implementations handle audio processing and model inference
    for converting speech to text. Workers may use multiprocessing,
    threading, or async patterns depending on the model requirements.

    Example:
        ```python
        class ZipformerWorker(ITranscriptionWorker):
            async def process_audio_stream(
                self, audio_stream: AsyncIterator[AudioData]
            ) -> AsyncIterator[Transcription]:
                async for audio in audio_stream:
                    # Process with Sherpa-ONNX Zipformer
                    result = self._model.transcribe(audio.data)
                    yield Transcription(
                        text=result.text,
                        confidence=ConfidenceScore(result.confidence),
                        ...
                    )
        ```
    """

    async def process_audio_stream(
        self, audio_stream: AsyncIterator[AudioData]
    ) -> AsyncIterator[Transcription]:
        """
        Process streaming audio data and yield transcription results.

        This method handles real-time audio transcription, processing
        audio chunks as they arrive and yielding results incrementally.

        Args:
            audio_stream: Async iterator yielding AudioData chunks

        Yields:
            Transcription: Transcription results with text, confidence,
                          and metadata

        Raises:
            WorkerException: If worker fails or model crashes
            ValidationException: If audio format is invalid

        Example:
            ```python
            async def transcribe():
                audio_stream = get_audio_stream()
                async for result in worker.process_audio_stream(audio_stream):
                    print(f"Transcribed: {result.text}")
            ```
        """
        ...

    async def start(self) -> None:
        """
        Start the worker and load the model.

        This method initializes the worker process, loads the ML model
        into memory, and prepares it for inference. Should be called
        before processing any audio.

        Raises:
            WorkerException: If worker fails to start or model fails to load

        Example:
            ```python
            worker = ZipformerWorker(config)
            await worker.start()  # Load model
            # Now ready to process audio
            ```
        """
        ...

    async def stop(self) -> None:
        """
        Stop the worker and cleanup resources.

        This method gracefully shuts down the worker, unloads the model,
        and cleans up any resources (memory, processes, queues). Should
        always be called when done processing.

        Example:
            ```python
            try:
                await worker.start()
                # Process audio...
            finally:
                await worker.stop()  # Always cleanup
            ```
        """
        ...

    async def is_ready(self) -> bool:
        """
        Check if worker is ready to process audio.

        Returns:
            bool: True if worker started and model loaded, False otherwise

        Example:
            ```python
            if await worker.is_ready():
                await worker.process_audio_stream(audio)
            else:
                raise RuntimeError("Worker not ready")
            ```
        """
        ...


class IModerationWorker(Protocol):
    """
    Interface for content moderation workers.

    Implementations handle hate speech detection and content classification
    using NLP models. Workers analyze text and return moderation results
    with labels and confidence scores.

    Example:
        ```python
        class ViSoBERTWorker(IModerationWorker):
            async def moderate(self, text: str) -> ModerationResult:
                # Run ViSoBERT-HSD-Span model
                result = self._model.predict(text)
                return ModerationResult(
                    text=text,
                    label=result.label,
                    confidence=ConfidenceScore(result.score),
                    ...
                )
        ```
    """

    async def moderate(self, text: str) -> ModerationResult:
        """
        Analyze text for hate speech and inappropriate content.

        This method runs content moderation on the input text, returning
        a classification label (CLEAN, OFFENSIVE, HATE_SPEECH) and
        confidence score.

        Args:
            text: Text content to moderate

        Returns:
            ModerationResult: Moderation result with label, confidence,
                             and optional detected spans

        Raises:
            WorkerException: If moderation worker fails
            ValidationException: If text is empty or too long

        Example:
            ```python
            result = await worker.moderate("Xin chào")
            if result.is_offensive():
                print(f"Offensive content detected: {result.label}")
            ```
        """
        ...

    async def start(self) -> None:
        """
        Start the moderation worker and load the model.

        Raises:
            WorkerException: If worker fails to start or model fails to load
        """
        ...

    async def stop(self) -> None:
        """
        Stop the moderation worker and cleanup resources.
        """
        ...

    async def is_ready(self) -> bool:
        """
        Check if moderation worker is ready.

        Returns:
            bool: True if worker started and model loaded, False otherwise
        """
        ...


class IWorkerManager(Protocol):
    """
    Interface for managing multiple workers.

    The worker manager orchestrates multiple worker instances, handles
    model switching, monitors worker health, and manages the worker
    lifecycle. It abstracts away the complexity of multiprocessing
    or distributed worker management.

    Example:
        ```python
        class MultiprocessingWorkerManager(IWorkerManager):
            async def get_transcription_worker(
                self
            ) -> Optional[ITranscriptionWorker]:
                if self._current_stt_worker and await self._current_stt_worker.is_ready():
                    return self._current_stt_worker
                return None
        ```
    """

    async def get_transcription_worker(self) -> Optional[ITranscriptionWorker]:
        """
        Get the active transcription worker.

        Returns:
            Optional[ITranscriptionWorker]: The currently active STT worker,
                                            or None if no worker is active

        Example:
            ```python
            worker = await manager.get_transcription_worker()
            if worker:
                async for result in worker.process_audio_stream(audio):
                    print(result.text)
            ```
        """
        ...

    async def get_moderation_worker(self) -> Optional[IModerationWorker]:
        """
        Get the active moderation worker.

        Returns:
            Optional[IModerationWorker]: The currently active moderation worker,
                                         or None if moderation is disabled

        Example:
            ```python
            worker = await manager.get_moderation_worker()
            if worker:
                result = await worker.moderate(text)
            ```
        """
        ...

    async def switch_model(self, model_config: ModelConfig) -> None:
        """
        Switch to a different model configuration.

        This method gracefully shuts down the current worker (if any)
        and starts a new worker with the specified model configuration.

        Args:
            model_config: Configuration for the new model to load

        Raises:
            WorkerException: If model switch fails
            ValidationException: If model_config is invalid

        Example:
            ```python
            new_config = ModelConfig.for_zipformer(
                model_path="/path/to/model"
            )
            await manager.switch_model(new_config)
            ```
        """
        ...

    async def enable_moderation(self, enabled: bool) -> None:
        """
        Enable or disable content moderation.

        Args:
            enabled: True to enable moderation, False to disable

        Example:
            ```python
            await manager.enable_moderation(True)  # Turn on moderation
            await manager.enable_moderation(False)  # Turn off
            ```
        """
        ...

    async def get_model_status(self) -> dict:
        """
        Get status of all managed workers.

        Returns:
            dict: Status information including:
                - current_model: Name of active STT model
                - model_ready: Whether STT worker is ready
                - moderation_enabled: Whether moderation is active
                - moderation_ready: Whether moderation worker is ready

        Example:
            ```python
            status = await manager.get_model_status()
            print(f"Model: {status['current_model']}")
            print(f"Ready: {status['model_ready']}")
            ```
        """
        ...

    async def start_all(self) -> None:
        """
        Start all configured workers.

        Raises:
            WorkerException: If any worker fails to start
        """
        ...

    async def stop_all(self) -> None:
        """
        Stop all workers and cleanup resources.

        This method should be called during application shutdown to
        gracefully terminate all worker processes.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check health of all workers.

        Returns:
            bool: True if all active workers are healthy, False otherwise

        Example:
            ```python
            if not await manager.health_check():
                logger.error("Worker health check failed!")
                await manager.restart_workers()
            ```
        """
        ...
