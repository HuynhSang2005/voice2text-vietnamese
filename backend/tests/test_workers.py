import pytest
from unittest.mock import MagicMock, patch
import multiprocessing
import numpy as np
from app.workers.zipformer import ZipformerWorker
from app.workers.whisper import WhisperWorker

@pytest.fixture
def mock_queues():
    input_q = multiprocessing.Queue()
    output_q = multiprocessing.Queue()
    return input_q, output_q

def test_zipformer_worker_initialization(mock_queues):
    input_q, output_q = mock_queues
    worker = ZipformerWorker(input_q, output_q, "zipformer")
    assert worker.model_path == "zipformer"
    assert worker.is_running is True

@patch("app.workers.zipformer.os.path.exists")
def test_zipformer_load_model(mock_exists, mock_queues):
    input_q, output_q = mock_queues
    mock_exists.return_value = True # Pretend model files exist
    
    worker = ZipformerWorker(input_q, output_q, "zipformer")
    
    # We need to mock the module that is imported INSIDE the function
    # Since we can't easily patch a local import, we can mock sys.modules
    # OR better: Refactor the worker to allow dependency injection or use a global import if safe.
    # Given the constraint of local import for pickling, we can use sys.modules patching.
    
    mock_sherpa = MagicMock()
    with patch.dict("sys.modules", {"sherpa_onnx": mock_sherpa}):
        worker.load_model()
    
    assert worker.recognizer is not None
    mock_sherpa.OnlineRecognizer.assert_called_once()

def test_whisper_worker_process(mock_queues):
    input_q, output_q = mock_queues
    
    worker = WhisperWorker(input_q, output_q, "faster-whisper")
    
    # Mock faster_whisper module
    mock_whisper_module = MagicMock()
    mock_model_instance = MagicMock()
    mock_whisper_module.WhisperModel.return_value = mock_model_instance
    
    # Mock transcribe return
    Segment = MagicMock()
    Segment.text = "Hello world"
    mock_model_instance.transcribe.return_value = ([Segment], None)
    
    with patch.dict("sys.modules", {"faster_whisper": mock_whisper_module}):
        worker.load_model()
    
    # Create dummy audio data (1.5 seconds of silence)
    # 16000 Hz * 1.5s = 24000 samples. Int16 = 2 bytes/sample.
    audio_data = np.zeros(24000, dtype=np.int16).tobytes()
    
    worker.process(audio_data)
    
    # Check output queue
    result = output_q.get(timeout=1)
    assert result["text"] == "Hello world"
    assert result["model"] == "faster-whisper"

