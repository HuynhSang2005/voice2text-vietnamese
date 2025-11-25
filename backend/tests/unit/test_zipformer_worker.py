import pytest
import multiprocessing
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../backend"))

from app.workers.zipformer import ZipformerWorker

@pytest.fixture
def mock_queues():
    input_q = MagicMock()
    output_q = MagicMock()
    return input_q, output_q

@pytest.fixture
def worker(mock_queues):
    input_q, output_q = mock_queues
    return ZipformerWorker(input_q, output_q, "zipformer")

@patch("os.path.exists")
def test_load_model_success(mock_exists, worker):
    # Mock file existence
    mock_exists.return_value = True
    
    # Mock sherpa_onnx module
    mock_sherpa = MagicMock()
    mock_recognizer = MagicMock()
    mock_sherpa.OfflineRecognizer.from_transducer.return_value = mock_recognizer
    mock_recognizer.create_stream.return_value = MagicMock()
    
    with patch.dict("sys.modules", {"sherpa_onnx": mock_sherpa}):
        # Run load_model
        worker.load_model()
    
    # Verify sherpa was called with correct args
    mock_sherpa.OfflineRecognizer.from_transducer.assert_called_once()
    call_kwargs = mock_sherpa.OfflineRecognizer.from_transducer.call_args.kwargs
    assert call_kwargs["decoding_method"] == "greedy_search"
    assert call_kwargs["provider"] == "cpu"
    assert worker.recognizer is not None

@patch("os.path.exists")
def test_load_model_missing_files(mock_exists, worker):
    # Mock file missing
    mock_exists.return_value = False
    
    # Mock sherpa_onnx to avoid import error
    with patch.dict("sys.modules", {"sherpa_onnx": MagicMock()}):
        # Run load_model, expect FileNotFoundError
        with pytest.raises(FileNotFoundError):
            worker.load_model()

@patch("os.path.exists")
def test_process_audio(mock_exists, worker):
    # Setup worker with mocked recognizer
    mock_exists.return_value = True
    mock_sherpa = MagicMock()
    mock_recognizer = MagicMock()
    mock_stream = MagicMock()
    mock_sherpa.OfflineRecognizer.from_transducer.return_value = mock_recognizer
    mock_recognizer.create_stream.return_value = mock_stream
    
    with patch.dict("sys.modules", {"sherpa_onnx": mock_sherpa}):
        worker.load_model()
    
    # Mock recognition result
    mock_stream.result.text = "Xin chào"
    # OfflineRecognizer doesn't use is_endpoint or is_ready loop in the same way
    
    # Create dummy audio data (16k samples, int16)
    audio_data = bytes(32000) 
    
    # Run process
    worker.process(audio_data)
    
    # Verify stream accepted waveform
    mock_stream.accept_waveform.assert_called_once()
    
    # Verify decode_stream called
    mock_recognizer.decode_stream.assert_called_once_with(mock_stream)
    
    # Verify output queue received result
    worker.output_queue.put.assert_called_once()
    result = worker.output_queue.put.call_args[0][0]
    # Expect formatted text
    assert result["text"] == "Xin chào"
    assert result["is_final"] is False
    assert result["model"] == "zipformer"

def test_format_vietnamese_text(worker):
    assert worker.format_vietnamese_text("XIN CHÀO") == "Xin chào"
    assert worker.format_vietnamese_text("tôi LÀ người VIỆT nam") == "Tôi là người việt nam"
    assert worker.format_vietnamese_text("") == ""
    assert worker.format_vietnamese_text("A") == "A"

@patch("os.path.exists")
def test_process_reset(mock_exists, worker):
    # Setup worker
    mock_exists.return_value = True
    mock_sherpa = MagicMock()
    mock_recognizer = MagicMock()
    mock_sherpa.OfflineRecognizer.from_transducer.return_value = mock_recognizer
    
    with patch.dict("sys.modules", {"sherpa_onnx": mock_sherpa}):
        worker.load_model()
        
    # Send reset command
    worker.process({"reset": True})
    
    # Verify create_stream called (once during load, once during reset)
    assert mock_recognizer.create_stream.call_count == 2
