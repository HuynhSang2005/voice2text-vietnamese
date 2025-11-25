import pytest
import multiprocessing
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../backend"))

from app.workers.whisper import WhisperWorker

@pytest.fixture
def mock_queues():
    input_q = MagicMock()
    output_q = MagicMock()
    return input_q, output_q

@pytest.fixture
def worker(mock_queues):
    input_q, output_q = mock_queues
    return WhisperWorker(input_q, output_q, "faster-whisper")

@patch("os.path.exists")
def test_load_model_faster_whisper(mock_exists, worker):
    mock_exists.return_value = True
    
    mock_whisper_mod = MagicMock()
    mock_whisper_cls = MagicMock()
    mock_whisper_mod.WhisperModel = mock_whisper_cls
    
    with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
        worker.load_model()
    
    mock_whisper_cls.assert_called_once()
    assert worker.model is not None

@patch("os.path.exists")
def test_load_model_phowhisper(mock_exists, mock_queues):
    mock_exists.return_value = True
    input_q, output_q = mock_queues
    worker = WhisperWorker(input_q, output_q, "phowhisper")
    
    mock_whisper_mod = MagicMock()
    mock_whisper_cls = MagicMock()
    mock_whisper_mod.WhisperModel = mock_whisper_cls
    
    with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
        worker.load_model()
    
    # Mock model transcribe
    mock_segment = MagicMock()
    mock_segment.text = "Xin chào"
    worker.model.transcribe.return_value = ([mock_segment], None)
    
    # Send small chunk (should buffer)
    small_chunk = bytes(1000)
    worker.process(small_chunk)
    worker.output_queue.put.assert_not_called()
    
    # Verify buffering logic:
    assert len(worker.buffer) > 0

@patch("os.path.exists")
def test_process_audio_transcription(mock_exists, worker):
    mock_exists.return_value = True
    
    mock_whisper_mod = MagicMock()
    mock_whisper_cls = MagicMock()
    mock_whisper_mod.WhisperModel = mock_whisper_cls
    
    with patch.dict("sys.modules", {"faster_whisper": mock_whisper_mod}):
        worker.load_model()
    
    # Mock model transcribe
    mock_segment = MagicMock()
    mock_segment.text = "Xin chào"
    worker.model.transcribe.return_value = ([mock_segment], None)
    
    # Send large chunk
    large_chunk = bytes(32000 * 2) # 2 seconds
    worker.process(large_chunk)
    
    # Should have called transcribe
    worker.model.transcribe.assert_called()
    
    # Should have put result in queue
    worker.output_queue.put.assert_called()
    result = worker.output_queue.put.call_args[0][0]
    assert result["text"] == "Xin chào"
