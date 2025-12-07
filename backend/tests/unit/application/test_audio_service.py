"""
Unit tests for AudioService.

Tests cover:
- Constructor validation
- Audio validation (format, size, sample rate, channels)
- Audio chunking
- Processing time estimation
- Configuration getters
"""

import pytest
from app.application.services.audio_service import AudioService
from app.domain.value_objects.audio_data import AudioData
from app.domain.exceptions import ValidationException


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def default_audio_service():
    """Create audio service with default configuration."""
    return AudioService()


@pytest.fixture
def strict_audio_service():
    """Create audio service with strict validation."""
    return AudioService(
        max_file_size_mb=5,
        supported_formats=['pcm', 'wav'],
        min_sample_rate=16000,
        max_sample_rate=32000,
        require_mono=True
    )


@pytest.fixture
def sample_pcm_audio():
    """Create sample PCM mono audio (1 second at 16kHz)."""
    # 16000 Hz * 1 channel * 2 bytes * 1 second = 32000 bytes
    data = b'\x00' * 32000
    return AudioData.create_pcm_mono(data, sample_rate=16000, duration_ms=1000)


@pytest.fixture
def large_audio():
    """Create large audio file (>10MB)."""
    # 11MB of data
    data = b'\x00' * (11 * 1024 * 1024)
    return AudioData.create_pcm_mono(data, sample_rate=16000)


# ============================================================================
# Constructor Tests
# ============================================================================

class TestAudioServiceConstructor:
    """Test AudioService constructor validation."""
    
    def test_constructor_with_defaults(self):
        """Should create service with default values."""
        service = AudioService()
        assert service.get_max_file_size_mb() == 10
        assert service.get_sample_rate_range() == (8000, 48000)
        assert 'pcm' in service.get_supported_formats()
    
    def test_constructor_with_custom_values(self):
        """Should create service with custom configuration."""
        service = AudioService(
            max_file_size_mb=5,
            supported_formats=['pcm', 'wav'],
            min_sample_rate=16000,
            max_sample_rate=32000,
            require_mono=True
        )
        assert service.get_max_file_size_mb() == 5
        assert service.get_sample_rate_range() == (16000, 32000)
        assert service.get_supported_formats() == ['pcm', 'wav']
    
    def test_constructor_with_invalid_file_size(self):
        """Should raise ValidationException for negative file size."""
        with pytest.raises(ValidationException) as exc_info:
            AudioService(max_file_size_mb=-1)
        
        assert exc_info.value.field == "max_file_size_mb"
        assert "must be positive" in exc_info.value.constraint
    
    def test_constructor_with_invalid_sample_rate(self):
        """Should raise ValidationException for invalid sample rate range."""
        with pytest.raises(ValidationException) as exc_info:
            AudioService(min_sample_rate=48000, max_sample_rate=16000)
        
        assert exc_info.value.field == "sample_rate_range"


# ============================================================================
# Audio Validation Tests
# ============================================================================

class TestAudioServiceValidation:
    """Test audio validation methods."""
    
    def test_validate_valid_audio(self, default_audio_service, sample_pcm_audio):
        """Should validate correct audio successfully."""
        is_valid, errors = default_audio_service.validate_audio(sample_pcm_audio)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_audio_too_large(self, default_audio_service, large_audio):
        """Should reject audio exceeding max file size."""
        is_valid, errors = default_audio_service.validate_audio(large_audio)
        assert is_valid is False
        assert len(errors) == 1
        assert "too large" in errors[0].lower()
    
    def test_validate_unsupported_format(self, strict_audio_service):
        """Should reject unsupported audio format."""
        audio = AudioData(
            data=b'\x00' * 1000,
            sample_rate=16000,
            channels=1,
            format='mp3'  # Not in strict service's supported formats
        )
        is_valid, errors = strict_audio_service.validate_audio(audio)
        assert is_valid is False
        assert any("unsupported" in e.lower() for e in errors)
    
    def test_validate_sample_rate_too_low(self, strict_audio_service):
        """Should reject sample rate below minimum."""
        audio = AudioData.create_pcm_mono(
            b'\x00' * 1000,
            sample_rate=8000  # Below strict service's min of 16000
        )
        is_valid, errors = strict_audio_service.validate_audio(audio)
        assert is_valid is False
        assert any("too low" in e.lower() for e in errors)
    
    def test_validate_sample_rate_too_high(self, strict_audio_service):
        """Should reject sample rate above maximum."""
        audio = AudioData.create_pcm_mono(
            b'\x00' * 1000,
            sample_rate=48000  # Above strict service's max of 32000
        )
        is_valid, errors = strict_audio_service.validate_audio(audio)
        assert is_valid is False
        assert any("too high" in e.lower() for e in errors)
    
    def test_validate_stereo_when_mono_required(self, strict_audio_service):
        """Should reject stereo audio when mono is required."""
        audio = AudioData(
            data=b'\x00' * 1000,
            sample_rate=16000,
            channels=2,  # Stereo
            format='pcm'
        )
        is_valid, errors = strict_audio_service.validate_audio(audio)
        assert is_valid is False
        assert any("mono" in e.lower() for e in errors)
    
    def test_validate_audio_or_raise_with_valid(
        self,
        default_audio_service,
        sample_pcm_audio
    ):
        """Should not raise for valid audio."""
        # Should not raise
        default_audio_service.validate_audio_or_raise(sample_pcm_audio)
    
    def test_validate_audio_or_raise_with_invalid(
        self,
        default_audio_service,
        large_audio
    ):
        """Should raise ValidationException for invalid audio."""
        with pytest.raises(ValidationException) as exc_info:
            default_audio_service.validate_audio_or_raise(large_audio)
        
        assert exc_info.value.field == "audio_data"


# ============================================================================
# Audio Chunking Tests
# ============================================================================

class TestAudioServiceChunking:
    """Test audio chunking functionality."""
    
    def test_chunk_audio_basic(self, default_audio_service):
        """Should chunk audio into fixed-size pieces."""
        # Create 10 seconds of audio at 16kHz mono
        bytes_per_second = 16000 * 1 * 2  # 32000 bytes/sec
        data = b'\x00' * (10 * bytes_per_second)
        audio = AudioData.create_pcm_mono(data, sample_rate=16000, duration_ms=10000)
        
        chunks = list(default_audio_service.chunk_audio(audio, chunk_size_ms=3000))
        
        # Should have 4 chunks (3s + 3s + 3s + 1s)
        assert len(chunks) == 4
        assert all(isinstance(c, AudioData) for c in chunks)
        
        # First 3 chunks should be ~3 seconds
        for chunk in chunks[:3]:
            assert 2900 <= chunk.duration_ms <= 3100
        
        # Last chunk should be ~1 second
        assert 900 <= chunks[3].duration_ms <= 1100
    
    def test_chunk_audio_preserves_format(self, default_audio_service, sample_pcm_audio):
        """Should preserve audio format in chunks."""
        chunks = list(default_audio_service.chunk_audio(sample_pcm_audio, 500))
        
        for chunk in chunks:
            assert chunk.sample_rate == sample_pcm_audio.sample_rate
            assert chunk.channels == sample_pcm_audio.channels
            assert chunk.format == sample_pcm_audio.format
    
    def test_chunk_audio_with_invalid_chunk_size(
        self,
        default_audio_service,
        sample_pcm_audio
    ):
        """Should raise ValidationException for invalid chunk size."""
        with pytest.raises(ValidationException) as exc_info:
            list(default_audio_service.chunk_audio(sample_pcm_audio, chunk_size_ms=-1))
        
        assert exc_info.value.field == "chunk_size_ms"
    
    def test_chunk_audio_single_chunk(self, default_audio_service):
        """Should return single chunk if audio shorter than chunk size."""
        # 1 second audio, 3 second chunks
        data = b'\x00' * 32000
        audio = AudioData.create_pcm_mono(data, sample_rate=16000, duration_ms=1000)
        
        chunks = list(default_audio_service.chunk_audio(audio, chunk_size_ms=3000))
        
        assert len(chunks) == 1
        assert chunks[0].duration_ms == 1000


# ============================================================================
# Processing Time Estimation Tests
# ============================================================================

class TestAudioServiceProcessingTime:
    """Test processing time estimation."""
    
    def test_estimate_processing_time_with_duration(self, default_audio_service):
        """Should estimate processing time from duration."""
        audio = AudioData.create_pcm_mono(
            b'\x00' * 32000,
            sample_rate=16000,
            duration_ms=60000  # 1 minute
        )
        
        # 10x real-time (0.1 multiplier)
        estimated = default_audio_service.estimate_processing_time(audio, 0.1)
        assert 5.9 <= estimated <= 6.1  # ~6 seconds
    
    def test_estimate_processing_time_without_duration(self, default_audio_service):
        """Should estimate processing time from size when duration missing."""
        # 1 second at 16kHz mono = 32000 bytes
        audio = AudioData.create_pcm_mono(
            b'\x00' * 32000,
            sample_rate=16000,
            duration_ms=None  # No duration
        )
        
        estimated = default_audio_service.estimate_processing_time(audio, 0.1)
        assert 0.09 <= estimated <= 0.11  # ~0.1 seconds
    
    def test_estimate_processing_time_with_custom_multiplier(
        self,
        default_audio_service
    ):
        """Should use custom processing rate multiplier."""
        audio = AudioData.create_pcm_mono(
            b'\x00' * 32000,
            sample_rate=16000,
            duration_ms=10000  # 10 seconds
        )
        
        # Real-time processing (1.0 multiplier)
        estimated = default_audio_service.estimate_processing_time(audio, 1.0)
        assert 9.9 <= estimated <= 10.1  # ~10 seconds


# ============================================================================
# Configuration Getters Tests
# ============================================================================

class TestAudioServiceGetters:
    """Test configuration getter methods."""
    
    def test_get_supported_formats(self, default_audio_service):
        """Should return list of supported formats."""
        formats = default_audio_service.get_supported_formats()
        assert isinstance(formats, list)
        assert 'pcm' in formats
        assert 'wav' in formats
    
    def test_get_supported_formats_returns_copy(self, default_audio_service):
        """Should return copy to prevent mutation."""
        formats1 = default_audio_service.get_supported_formats()
        formats2 = default_audio_service.get_supported_formats()
        assert formats1 == formats2
        assert formats1 is not formats2  # Different objects
    
    def test_get_max_file_size_mb(self, default_audio_service):
        """Should return max file size in MB."""
        max_size = default_audio_service.get_max_file_size_mb()
        assert max_size == 10.0
    
    def test_get_sample_rate_range(self, default_audio_service):
        """Should return sample rate range tuple."""
        min_rate, max_rate = default_audio_service.get_sample_rate_range()
        assert min_rate == 8000
        assert max_rate == 48000
