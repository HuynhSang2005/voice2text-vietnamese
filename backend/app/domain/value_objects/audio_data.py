"""Audio data value object."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AudioData:
    """
    Immutable value object representing audio data.
    
    Encapsulates raw audio bytes with metadata about format and quality.
    Ensures audio data validity through validation.
    
    Attributes:
        data: Raw audio bytes
        sample_rate: Sample rate in Hz (e.g., 16000, 44100)
        channels: Number of audio channels (1=mono, 2=stereo)
        format: Audio format (e.g., 'pcm', 'wav', 'mp3')
        duration_ms: Duration in milliseconds (optional)
    """
    
    data: bytes
    sample_rate: int
    channels: int
    format: str
    duration_ms: Optional[float] = None
    
    # Supported formats
    SUPPORTED_FORMATS = {'pcm', 'wav', 'mp3', 'flac', 'ogg'}
    
    # Standard sample rates
    STANDARD_SAMPLE_RATES = {8000, 16000, 22050, 32000, 44100, 48000}
    
    def __post_init__(self) -> None:
        """Validate audio data after initialization."""
        if not self.data:
            raise ValueError("Audio data cannot be empty")
        
        if self.sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate}")
        
        if self.sample_rate not in self.STANDARD_SAMPLE_RATES:
            # Warning: non-standard sample rate (still allowed)
            pass
        
        if self.channels not in (1, 2):
            raise ValueError(f"Channels must be 1 (mono) or 2 (stereo), got {self.channels}")
        
        if self.format.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {self.format}. "
                f"Must be one of {self.SUPPORTED_FORMATS}"
            )
        
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError(f"Duration must be non-negative, got {self.duration_ms}")
    
    def is_mono(self) -> bool:
        """Check if audio is mono (single channel)."""
        return self.channels == 1
    
    def is_stereo(self) -> bool:
        """Check if audio is stereo (two channels)."""
        return self.channels == 2
    
    def get_size_bytes(self) -> int:
        """Get size of audio data in bytes."""
        return len(self.data)
    
    def get_size_kb(self) -> float:
        """Get size of audio data in kilobytes."""
        return self.get_size_bytes() / 1024
    
    def is_standard_sample_rate(self) -> bool:
        """Check if sample rate is a standard value."""
        return self.sample_rate in self.STANDARD_SAMPLE_RATES
    
    def is_high_quality(self) -> bool:
        """Check if audio is high quality (>=44.1kHz)."""
        return self.sample_rate >= 44100
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary (excludes raw data for size).
        
        Returns:
            Dictionary with metadata only.
        """
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
            "duration_ms": self.duration_ms,
            "size_bytes": self.get_size_bytes(),
            "is_mono": self.is_mono(),
            "is_high_quality": self.is_high_quality(),
        }
    
    @classmethod
    def create_pcm_mono(
        cls,
        data: bytes,
        sample_rate: int = 16000,
        duration_ms: Optional[float] = None,
    ) -> "AudioData":
        """
        Factory method for creating PCM mono audio (common for STT).
        
        Args:
            data: Raw PCM audio bytes
            sample_rate: Sample rate (default: 16000 Hz for speech)
            duration_ms: Optional duration in milliseconds
        
        Returns:
            AudioData instance configured for PCM mono.
        """
        return cls(
            data=data,
            sample_rate=sample_rate,
            channels=1,
            format='pcm',
            duration_ms=duration_ms,
        )
    
    @classmethod
    def from_wav(
        cls,
        data: bytes,
        sample_rate: int,
        channels: int,
        duration_ms: Optional[float] = None,
    ) -> "AudioData":
        """
        Factory method for creating WAV audio data.
        
        Args:
            data: WAV file bytes
            sample_rate: Sample rate in Hz
            channels: Number of channels (1 or 2)
            duration_ms: Optional duration in milliseconds
        
        Returns:
            AudioData instance for WAV format.
        """
        return cls(
            data=data,
            sample_rate=sample_rate,
            channels=channels,
            format='wav',
            duration_ms=duration_ms,
        )
