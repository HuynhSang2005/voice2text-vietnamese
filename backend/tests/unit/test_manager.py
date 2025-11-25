import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import multiprocessing

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../backend"))

from app.core.manager import ModelManager

@pytest.fixture
def manager():
    return ModelManager()

@patch("app.core.manager.multiprocessing.Process")
@patch("app.core.manager.ModelManager._get_worker_class")
def test_start_model_zipformer(mock_get_worker, mock_process_cls, manager):
    # Setup mock worker class and instance
    mock_worker_cls = MagicMock()
    mock_worker_instance = MagicMock()
    mock_worker_cls.return_value = mock_worker_instance
    mock_get_worker.return_value = mock_worker_cls
    
    # Setup mock process
    mock_process_instance = MagicMock()
    mock_process_cls.return_value = mock_process_instance
    
    # Start model
    manager.start_model("zipformer")
    
    # Verify worker created
    mock_worker_cls.assert_called_once()
    
    # Verify process created and started
    mock_process_cls.assert_called_once_with(target=mock_worker_instance.run)
    mock_process_instance.start.assert_called_once()
    
    # Verify queues created
    assert "zipformer" in manager.active_processes
    assert "zipformer" in manager.input_queues
    
    # Verify get_queues
    input_q, output_q = manager.get_queues("zipformer")
    assert input_q is not None
    assert output_q is not None

@patch("app.core.manager.multiprocessing.Process")
@patch("app.core.manager.ModelManager._get_worker_class")
def test_start_model_whisper(mock_get_worker, mock_process_cls, manager):
    mock_worker_cls = MagicMock()
    mock_worker_instance = MagicMock()
    mock_worker_cls.return_value = mock_worker_instance
    mock_get_worker.return_value = mock_worker_cls
    
    mock_process_instance = MagicMock()
    mock_process_cls.return_value = mock_process_instance
    
    manager.start_model("faster-whisper")
    
    mock_worker_cls.assert_called_once()
    args = mock_worker_cls.call_args[0]
    assert args[2] == "faster-whisper" # model_type arg
    mock_process_instance.start.assert_called_once()

def test_start_invalid_model(manager):
    # Ensure _get_worker_class returns None for invalid
    with patch.object(manager, "_get_worker_class", return_value=None):
        with pytest.raises(ValueError):
            manager.start_model("invalid-model")

@patch("app.core.manager.ModelManager._get_worker_class")
def test_stop_model(mock_get_worker, manager):
    # Setup mock
    mock_worker_cls = MagicMock()
    mock_get_worker.return_value = mock_worker_cls
    
    # Mock process to avoid real start
    with patch("app.core.manager.multiprocessing.Process") as mock_process_cls:
        mock_process_instance = MagicMock()
        mock_process_cls.return_value = mock_process_instance
        
        # Start then stop
        manager.start_model("zipformer")
        manager.stop_current_model()
        
        assert "zipformer" not in manager.active_processes
        assert "zipformer" not in manager.input_queues
        mock_process_instance.join.assert_called()
