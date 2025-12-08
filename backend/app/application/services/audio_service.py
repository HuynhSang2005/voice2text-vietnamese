"""
Audio processing service for application layer.

This service provides audio-related utilities including:
- Format validation
- Audio chunking for streaming
- Sample rate validation
- Size validation
"""

from typing import Iterator, List
from app.domain.value_objects.audio_data import AudioData
from app.domain.exceptions import ValidationException


class AudioService:
    """
    Service for audio processing and validation.

    This service provides utilities for working with audio data in the
    application layer. It handles validation, chunking, and format conversion
    without depending on specific infrastructure implementations.

    Use Cases:
    - Validate audio before transcription
    - Split large audio files into chunks for streaming
    - Check audio quality requirements
    - Validate audio format compatibility

    Example:
        ```python
        service = AudioService(
            max_file_size_mb=10,
            supported_formats=['pcm', 'wav'],
            min_sample_rate=8000
        )

        # Validate audio
        is_valid, errors = service.validate_audio(audio_data)
        if not is_valid:
            raise ValidationException(...)

        # Chunk for streaming
        chunks = service.chunk_audio(audio_data, chunk_size_ms=3000)
        for chunk in chunks:
            await process_chunk(chunk)
        ```
    """

    # Default configuration
    DEFAULT_MAX_FILE_SIZE_MB = 10
    DEFAULT_CHUNK_SIZE_MS = 3000  # 3 seconds
    DEFAULT_MIN_SAMPLE_RATE = 8000
    DEFAULT_MAX_SAMPLE_RATE = 48000

    def __init__(
        self,
        max_file_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB,
        supported_formats: List[str] = None,
        min_sample_rate: int = DEFAULT_MIN_SAMPLE_RATE,
        max_sample_rate: int = DEFAULT_MAX_SAMPLE_RATE,
        require_mono: bool = False,
    ):
        """
        Initialize audio service with configuration.

        Args:
            max_file_size_mb: Maximum audio file size in MB
            supported_formats: List of supported formats (default: all AudioData formats)
            min_sample_rate: Minimum sample rate in Hz
            max_sample_rate: Maximum sample rate in Hz
            require_mono: Whether to require mono audio
        """
        if max_file_size_mb <= 0:
            raise ValidationException(
                field="max_file_size_mb",
                value=max_file_size_mb,
                constraint="must be positive",
            )

        if min_sample_rate <= 0 or max_sample_rate <= 0:
            raise ValidationException(
                field="sample_rate",
                value=(min_sample_rate, max_sample_rate),
                constraint="must be positive",
            )

        if min_sample_rate > max_sample_rate:
            raise ValidationException(
                field="sample_rate_range",
                value=(min_sample_rate, max_sample_rate),
                constraint="min_sample_rate must be <= max_sample_rate",
            )

        self._max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self._supported_formats = (
            supported_formats
            if supported_formats
            else list(AudioData.SUPPORTED_FORMATS)
        )
        self._min_sample_rate = min_sample_rate
        self._max_sample_rate = max_sample_rate
        self._require_mono = require_mono

    def validate_audio(self, audio_data: AudioData) -> tuple[bool, List[str]]:
        """
        Validate audio data against service configuration.

        Returns tuple of (is_valid, error_messages). If is_valid is True,
        error_messages will be empty. Otherwise, error_messages contains
        all validation failures.

        Args:
            audio_data: Audio data to validate

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            ```python
            is_valid, errors = service.validate_audio(audio)
            if not is_valid:
                print(f"Validation failed: {', '.join(errors)}")
            ```
        """
        errors = []

        # Check file size
        if audio_data.get_size_bytes() > self._max_file_size_bytes:
            errors.append(
                f"Audio file too large: {audio_data.get_size_kb():.2f}KB "
                f"exceeds maximum {self._max_file_size_bytes / 1024:.2f}KB"
            )

        # Check format
        if audio_data.format.lower() not in self._supported_formats:
            errors.append(
                f"Unsupported audio format: {audio_data.format}. "
                f"Supported: {', '.join(self._supported_formats)}"
            )

        # Check sample rate
        if audio_data.sample_rate < self._min_sample_rate:
            errors.append(
                f"Sample rate too low: {audio_data.sample_rate}Hz "
                f"is below minimum {self._min_sample_rate}Hz"
            )

        if audio_data.sample_rate > self._max_sample_rate:
            errors.append(
                f"Sample rate too high: {audio_data.sample_rate}Hz "
                f"exceeds maximum {self._max_sample_rate}Hz"
            )

        # Check channels
        if self._require_mono and not audio_data.is_mono():
            errors.append(
                f"Audio must be mono (1 channel), got {audio_data.channels} channels"
            )

        return (len(errors) == 0, errors)

    def validate_audio_or_raise(self, audio_data: AudioData) -> None:
        """
        Validate audio and raise ValidationException if invalid.

        Args:
            audio_data: Audio data to validate

        Raises:
            ValidationException: If audio validation fails

        Example:
            ```python
            try:
                service.validate_audio_or_raise(audio)
            except ValidationException as e:
                print(f"Invalid audio: {e}")
            ```
        """
        is_valid, errors = self.validate_audio(audio_data)
        if not is_valid:
            raise ValidationException(
                field="audio_data",
                value=audio_data.to_dict(),
                constraint="; ".join(errors),
            )

    def chunk_audio(
        self, audio_data: AudioData, chunk_size_ms: int = DEFAULT_CHUNK_SIZE_MS
    ) -> Iterator[AudioData]:
        """
        Split audio into fixed-size chunks for streaming processing.

        This method yields AudioData chunks of approximately chunk_size_ms
        milliseconds. The last chunk may be smaller than chunk_size_ms.

        Args:
            audio_data: Source audio to chunk
            chunk_size_ms: Chunk size in milliseconds (default: 3000ms)

        Yields:
            AudioData chunks of approximately chunk_size_ms duration

        Raises:
            ValidationException: If chunk_size_ms is invalid

        Example:
            ```python
            audio = AudioData.create_pcm_mono(large_audio_bytes)
            for i, chunk in enumerate(service.chunk_audio(audio, 3000)):
                print(f"Processing chunk {i+1}: {chunk.get_size_kb():.2f}KB")
                await transcribe_chunk(chunk)
            ```
        """
        if chunk_size_ms <= 0:
            raise ValidationException(
                field="chunk_size_ms",
                value=chunk_size_ms,
                constraint="must be positive",
            )

        # Calculate bytes per chunk based on audio format
        # For PCM: bytes_per_sample = 2 (16-bit), bytes_per_second = sample_rate * channels * 2
        bytes_per_second = audio_data.sample_rate * audio_data.channels * 2
        bytes_per_chunk = int((chunk_size_ms / 1000.0) * bytes_per_second)

        if bytes_per_chunk <= 0:
            raise ValidationException(
                field="chunk_calculation",
                value={
                    "chunk_size_ms": chunk_size_ms,
                    "bytes_per_chunk": bytes_per_chunk,
                },
                constraint="calculated chunk size must be positive",
            )

        # Split audio data into chunks
        total_bytes = len(audio_data.data)
        offset = 0

        while offset < total_bytes:
            # Get chunk data
            chunk_data = audio_data.data[offset : offset + bytes_per_chunk]
            chunk_duration = (len(chunk_data) / bytes_per_second) * 1000

            # Create chunk AudioData
            chunk = AudioData(
                data=chunk_data,
                sample_rate=audio_data.sample_rate,
                channels=audio_data.channels,
                format=audio_data.format,
                duration_ms=chunk_duration,
            )

            yield chunk
            offset += bytes_per_chunk

    def estimate_processing_time(
        self, audio_data: AudioData, processing_rate_multiplier: float = 0.1
    ) -> float:
        """
        Estimate processing time for audio transcription.

        Returns estimated time in seconds based on audio duration and
        a processing rate multiplier (e.g., 0.1 means processing is 10x
        faster than real-time).

        Args:
            audio_data: Audio to estimate processing time for
            processing_rate_multiplier: Processing speed multiplier (default: 0.1)

        Returns:
            Estimated processing time in seconds

        Example:
            ```python
            audio = AudioData.create_pcm_mono(data, duration_ms=60000)  # 1 minute
            estimated_seconds = service.estimate_processing_time(audio, 0.1)
            # estimated_seconds ≈ 6.0 (60s * 0.1)
            ```
        """
        if audio_data.duration_ms is None:
            # Estimate duration from size if not provided
            bytes_per_second = audio_data.sample_rate * audio_data.channels * 2
            duration_seconds = len(audio_data.data) / bytes_per_second
        else:
            duration_seconds = audio_data.duration_ms / 1000.0

        return duration_seconds * processing_rate_multiplier

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported audio formats.

        Returns:
            List of supported format strings
        """
        return self._supported_formats.copy()

    def get_max_file_size_mb(self) -> float:
        """
        Get maximum file size in MB.

        Returns:
            Maximum file size in megabytes
        """
        return self._max_file_size_bytes / (1024 * 1024)

    def get_sample_rate_range(self) -> tuple[int, int]:
        """
        Get valid sample rate range.

        Returns:
            Tuple of (min_sample_rate, max_sample_rate)
        """
        return (self._min_sample_rate, self._max_sample_rate)
