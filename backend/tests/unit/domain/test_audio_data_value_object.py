"""Unit tests for AudioData value object."""
import pytest
from app.domain.value_objects.audio_data import AudioData


class TestAudioDataValueObject:
    """Test suite for AudioData value object."""
    
    def test_create_valid_audio_data(self):
        """Test creating audio data with valid parameters."""
        data = b"raw_audio_bytes"
        audio = AudioData(
            data=data,
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.data == data
        assert audio.sample_rate == 16000
        assert audio.channels == 1
        assert audio.format == "pcm"
        assert audio.duration_ms is None
    
    def test_create_audio_with_duration(self):
        """Test creating audio data with duration."""
        audio = AudioData(
            data=b"test",
            sample_rate=44100,
            channels=2,
            format="wav",
            duration_ms=1500.5,
        )
        
        assert audio.duration_ms == 1500.5
    
    def test_validation_empty_data(self):
        """Test validation rejects empty audio data."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AudioData(
                data=b"",
                sample_rate=16000,
                channels=1,
                format="pcm",
            )
    
    def test_validation_negative_sample_rate(self):
        """Test validation rejects negative sample rate."""
        with pytest.raises(ValueError, match="must be positive"):
            AudioData(
                data=b"test",
                sample_rate=-16000,
                channels=1,
                format="pcm",
            )
    
    def test_validation_zero_sample_rate(self):
        """Test validation rejects zero sample rate."""
        with pytest.raises(ValueError, match="must be positive"):
            AudioData(
                data=b"test",
                sample_rate=0,
                channels=1,
                format="pcm",
            )
    
    def test_validation_invalid_channels(self):
        """Test validation rejects invalid channel counts."""
        with pytest.raises(ValueError, match="must be 1 .* or 2"):
            AudioData(
                data=b"test",
                sample_rate=16000,
                channels=3,
                format="pcm",
            )
    
    def test_validation_unsupported_format(self):
        """Test validation rejects unsupported formats."""
        with pytest.raises(ValueError, match="Unsupported audio format"):
            AudioData(
                data=b"test",
                sample_rate=16000,
                channels=1,
                format="xyz",
            )
    
    def test_validation_negative_duration(self):
        """Test validation rejects negative duration."""
        with pytest.raises(ValueError, match="must be non-negative"):
            AudioData(
                data=b"test",
                sample_rate=16000,
                channels=1,
                format="pcm",
                duration_ms=-100,
            )
    
    def test_is_mono_returns_true_for_single_channel(self):
        """Test is_mono() returns True for single channel audio."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.is_mono() is True
    
    def test_is_mono_returns_false_for_stereo(self):
        """Test is_mono() returns False for stereo audio."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=2,
            format="pcm",
        )
        
        assert audio.is_mono() is False
    
    def test_is_stereo_returns_true_for_two_channels(self):
        """Test is_stereo() returns True for two channel audio."""
        audio = AudioData(
            data=b"test",
            sample_rate=44100,
            channels=2,
            format="wav",
        )
        
        assert audio.is_stereo() is True
    
    def test_is_stereo_returns_false_for_mono(self):
        """Test is_stereo() returns False for mono audio."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.is_stereo() is False
    
    def test_get_size_bytes(self):
        """Test get_size_bytes() returns correct byte count."""
        data = b"test_audio_data_bytes"
        audio = AudioData(
            data=data,
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.get_size_bytes() == len(data)
    
    def test_get_size_kb(self):
        """Test get_size_kb() returns correct kilobyte count."""
        data = b"x" * 2048  # 2 KB
        audio = AudioData(
            data=data,
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.get_size_kb() == 2.0
    
    def test_is_standard_sample_rate_returns_true(self):
        """Test is_standard_sample_rate() for standard rates."""
        standard_rates = [8000, 16000, 22050, 32000, 44100, 48000]
        
        for rate in standard_rates:
            audio = AudioData(
                data=b"test",
                sample_rate=rate,
                channels=1,
                format="pcm",
            )
            assert audio.is_standard_sample_rate() is True
    
    def test_is_standard_sample_rate_returns_false(self):
        """Test is_standard_sample_rate() for non-standard rates."""
        audio = AudioData(
            data=b"test",
            sample_rate=12345,
            channels=1,
            format="pcm",
        )
        
        assert audio.is_standard_sample_rate() is False
    
    def test_is_high_quality_returns_true_for_high_rates(self):
        """Test is_high_quality() returns True for >= 44.1kHz."""
        audio_44k = AudioData(
            data=b"test",
            sample_rate=44100,
            channels=2,
            format="wav",
        )
        
        audio_48k = AudioData(
            data=b"test",
            sample_rate=48000,
            channels=2,
            format="wav",
        )
        
        assert audio_44k.is_high_quality() is True
        assert audio_48k.is_high_quality() is True
    
    def test_is_high_quality_returns_false_for_low_rates(self):
        """Test is_high_quality() returns False for < 44.1kHz."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio.is_high_quality() is False
    
    def test_to_dict_excludes_raw_data(self):
        """Test to_dict() excludes raw audio data for size."""
        audio = AudioData(
            data=b"test_data",
            sample_rate=16000,
            channels=1,
            format="pcm",
            duration_ms=1000,
        )
        
        result = audio.to_dict()
        
        assert "data" not in result
        assert result["sample_rate"] == 16000
        assert result["channels"] == 1
        assert result["format"] == "pcm"
        assert result["duration_ms"] == 1000
        assert result["size_bytes"] == 9
        assert result["is_mono"] is True
        assert result["is_high_quality"] is False
    
    def test_create_pcm_mono_factory_method(self):
        """Test create_pcm_mono() factory method."""
        data = b"pcm_audio"
        audio = AudioData.create_pcm_mono(
            data=data,
            sample_rate=16000,
            duration_ms=500,
        )
        
        assert audio.data == data
        assert audio.sample_rate == 16000
        assert audio.channels == 1
        assert audio.format == "pcm"
        assert audio.duration_ms == 500
        assert audio.is_mono() is True
    
    def test_create_pcm_mono_default_sample_rate(self):
        """Test create_pcm_mono() uses default 16kHz sample rate."""
        audio = AudioData.create_pcm_mono(data=b"test")
        
        assert audio.sample_rate == 16000
        assert audio.format == "pcm"
        assert audio.channels == 1
    
    def test_from_wav_factory_method(self):
        """Test from_wav() factory method."""
        data = b"wav_file_bytes"
        audio = AudioData.from_wav(
            data=data,
            sample_rate=44100,
            channels=2,
            duration_ms=2000,
        )
        
        assert audio.data == data
        assert audio.sample_rate == 44100
        assert audio.channels == 2
        assert audio.format == "wav"
        assert audio.duration_ms == 2000
        assert audio.is_stereo() is True
    
    def test_immutability(self):
        """Test that audio data is immutable (frozen)."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        with pytest.raises(AttributeError):
            audio.sample_rate = 44100  # type: ignore
    
    def test_supported_formats(self):
        """Test all supported audio formats."""
        formats = ["pcm", "wav", "mp3", "flac", "ogg"]
        
        for fmt in formats:
            audio = AudioData(
                data=b"test",
                sample_rate=16000,
                channels=1,
                format=fmt,
            )
            assert audio.format == fmt
    
    def test_format_case_insensitive(self):
        """Test format validation is case-insensitive."""
        audio = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="PCM",
        )
        
        assert audio.format == "PCM"
    
    def test_equality_based_on_all_fields(self):
        """Test equality compares all fields."""
        audio1 = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        audio2 = AudioData(
            data=b"test",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        audio3 = AudioData(
            data=b"different",
            sample_rate=16000,
            channels=1,
            format="pcm",
        )
        
        assert audio1 == audio2
        assert audio1 != audio3
