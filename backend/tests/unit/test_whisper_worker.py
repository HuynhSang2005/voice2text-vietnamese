"""
Unit tests for WhisperWorker.

Tests the Whisper worker's ability to:
- Load faster-whisper model (both standard and PhoWhisper)
- Process audio with energy-based VAD
- Buffer audio until minimum duration or silence
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.workers.whisper import WhisperWorker


class TestWhisperWorkerInit:
    """Test WhisperWorker initialization and configuration."""
    
    def test_vad_constants(self):
        """Test VAD configuration constants are correct."""
        assert WhisperWorker.SILENCE_THRESHOLD == 0.0005
        assert WhisperWorker.MIN_DURATION == 3.0
        assert WhisperWorker.MAX_DURATION == 15.0

    @pytest.fixture
    def mock_queues(self):
        """Mock input/output queues."""
        input_q = MagicMock()
        output_q = MagicMock()
        return input_q, output_q

    def test_faster_whisper_init(self, mock_queues):
        """Test initialization with faster-whisper model."""
        input_q, output_q = mock_queues
        worker = WhisperWorker(input_q, output_q, "faster-whisper")
        assert worker.model_name == "faster-whisper"
    
    def test_phowhisper_init(self, mock_queues):
        """Test initialization with phowhisper model."""
        input_q, output_q = mock_queues
        worker = WhisperWorker(input_q, output_q, "phowhisper")
        assert worker.model_name == "phowhisper"


class TestWhisperModelLoading:
    """Test WhisperWorker model loading."""
    
    @pytest.fixture
    def mock_queues(self):
        """Mock input/output queues."""
        input_q = MagicMock()
        output_q = MagicMock()
        return input_q, output_q

    @pytest.fixture
    def faster_whisper_worker(self, mock_queues):
        """Create faster-whisper worker."""
        input_q, output_q = mock_queues
        return WhisperWorker(input_q, output_q, "faster-whisper")
    
    @pytest.fixture
    def phowhisper_worker(self, mock_queues):
        """Create phowhisper worker."""
        input_q, output_q = mock_queues
        return WhisperWorker(input_q, output_q, "phowhisper")

    @patch("os.path.exists")
    def test_load_model_faster_whisper(self, mock_exists, faster_whisper_worker):
        """Test loading faster-whisper model."""
        mock_exists.return_value = True
        
        mock_whisper_mod = MagicMock()
        mock_whisper_cls = MagicMock()
        mock_whisper_mod.WhisperModel = mock_whisper_cls
        
        with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
            faster_whisper_worker.load_model()
        
        # Should load 'small' model directly
        mock_whisper_cls.assert_called_once()
        call_args = mock_whisper_cls.call_args
        assert call_args[0][0] == "small"  # model name
        assert call_args[1]["device"] == "cpu"
        assert call_args[1]["compute_type"] == "int8"
        assert faster_whisper_worker.model is not None
        assert isinstance(faster_whisper_worker.buffer, np.ndarray)

    @patch("os.path.exists")
    def test_load_model_phowhisper_local(self, mock_exists, phowhisper_worker):
        """Test loading PhoWhisper from local path."""
        mock_exists.return_value = True
        
        mock_whisper_mod = MagicMock()
        mock_whisper_cls = MagicMock()
        mock_whisper_mod.WhisperModel = mock_whisper_cls
        
        with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
            phowhisper_worker.load_model()
        
        # Should load from local path containing 'phowhisper-ct2'
        mock_whisper_cls.assert_called_once()
        call_args = mock_whisper_cls.call_args[0]
        assert "phowhisper-ct2" in call_args[0]

    @patch("os.path.exists")
    def test_load_model_phowhisper_fallback(self, mock_exists, phowhisper_worker):
        """Test PhoWhisper falls back to 'small' if local not found."""
        mock_exists.return_value = False
        
        mock_whisper_mod = MagicMock()
        mock_whisper_cls = MagicMock()
        mock_whisper_mod.WhisperModel = mock_whisper_cls
        
        with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
            phowhisper_worker.load_model()
        
        # Should fallback to 'small'
        call_args = mock_whisper_cls.call_args[0]
        assert call_args[0] == "small"


class TestWhisperAudioProcessing:
    """Test WhisperWorker audio processing with VAD."""
    
    @pytest.fixture
    def mock_queues(self):
        """Mock input/output queues."""
        input_q = MagicMock()
        output_q = MagicMock()
        return input_q, output_q
    
    @pytest.fixture
    def loaded_worker(self, mock_queues):
        """Create worker with mocked model."""
        input_q, output_q = mock_queues
        worker = WhisperWorker(input_q, output_q, "faster-whisper")
        
        # Mock model
        worker.model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Xin chào"
        worker.model.transcribe.return_value = ([mock_segment], None)
        worker.buffer = np.array([], dtype=np.float32)
        
        return worker

    def test_process_small_chunk_buffers(self, loaded_worker):
        """Test small audio chunk is buffered, not transcribed."""
        # Send small chunk (< MIN_DURATION)
        small_chunk = bytes(16000)  # 0.5 seconds at 16kHz
        loaded_worker.process(small_chunk)
        
        # Should buffer, not transcribe
        loaded_worker.model.transcribe.assert_not_called()
        loaded_worker.output_queue.put.assert_not_called()
        assert len(loaded_worker.buffer) > 0

    def test_process_large_chunk_transcribes(self, loaded_worker):
        """Test large audio chunk triggers transcription."""
        # Send large chunk (> MAX_DURATION)
        # 16 seconds at 16kHz, int16 = 16 * 16000 * 2 = 512000 bytes
        large_chunk = bytes(512000)
        loaded_worker.process(large_chunk)
        
        # Should have called transcribe
        loaded_worker.model.transcribe.assert_called()
        
        # Should have put result in queue
        loaded_worker.output_queue.put.assert_called()
        result = loaded_worker.output_queue.put.call_args[0][0]
        assert result["text"] == "Xin chào"
        assert result["is_final"] is True
        assert result["model"] == "faster-whisper"

    def test_process_multiple_small_chunks(self, loaded_worker):
        """Test multiple small chunks accumulate in buffer."""
        chunk_size = 16000  # 0.5 seconds
        
        # Send 5 small chunks
        for _ in range(5):
            loaded_worker.process(bytes(chunk_size))
        
        # Buffer should have accumulated
        expected_samples = (chunk_size * 5) // 2  # bytes / 2 for int16
        assert len(loaded_worker.buffer) >= expected_samples * 0.9  # Allow for floating point

    def test_process_reset_clears_buffer(self, loaded_worker):
        """Test reset command clears buffer."""
        # Add some data to buffer
        loaded_worker.process(bytes(16000))
        assert len(loaded_worker.buffer) > 0
        
        # Send reset
        loaded_worker.process({"reset": True})
        
        # Buffer should be cleared
        assert len(loaded_worker.buffer) == 0

    def test_process_dict_with_audio(self, loaded_worker):
        """Test processing dict format with audio."""
        loaded_worker.process({"audio": bytes(16000)})
        assert len(loaded_worker.buffer) > 0

    def test_process_without_model(self, mock_queues):
        """Test process returns early if model not loaded."""
        input_q, output_q = mock_queues
        worker = WhisperWorker(input_q, output_q, "faster-whisper")
        worker.model = None
        
        worker.process(bytes(16000))
        
        # Should not put anything in queue
        output_q.put.assert_not_called()


class TestVADLogic:
    """Test Voice Activity Detection logic."""
    
    @pytest.fixture
    def loaded_worker(self):
        """Create worker with mocked model."""
        worker = WhisperWorker(MagicMock(), MagicMock(), "faster-whisper")
        worker.model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "test"
        worker.model.transcribe.return_value = ([mock_segment], None)
        worker.buffer = np.array([], dtype=np.float32)
        return worker
    
    def test_silence_detection(self, loaded_worker):
        """Test silence is detected correctly."""
        # Create 4 seconds of data (> MIN_DURATION)
        # First 3.5 seconds of audio, then 0.5 seconds of silence
        audio_samples = np.random.randint(-1000, 1000, 3 * 16000, dtype=np.int16)
        silence_samples = np.zeros(16000, dtype=np.int16)  # Pure silence
        
        combined = np.concatenate([audio_samples, silence_samples])
        loaded_worker.process(combined.tobytes())
        
        # Should have triggered transcription due to silence at end
        loaded_worker.model.transcribe.assert_called()

    def test_no_transcription_below_min_duration(self, loaded_worker):
        """Test no transcription if buffer < MIN_DURATION even with silence."""
        # 2 seconds (< MIN_DURATION of 3s)
        silence = np.zeros(2 * 16000, dtype=np.int16)
        loaded_worker.process(silence.tobytes())
        
        # Should NOT transcribe
        loaded_worker.model.transcribe.assert_not_called()
