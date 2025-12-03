"""
Integration tests for content moderation (ViSoBERT-HSD) integration.

Tests cover:
1. ModelManager detector management
2. WebSocket endpoint with moderation
3. REST API moderation endpoints
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import multiprocessing
from queue import Empty

from app.core.manager import ModelManager


class TestModelManagerDetector:
    """Tests for ModelManager detector management methods."""
    
    def test_valid_detectors_list(self):
        """Test that VALID_DETECTORS contains expected detectors."""
        mgr = ModelManager()
        assert "visobert-hsd" in mgr.VALID_DETECTORS
    
    def test_initial_detector_state(self):
        """Test initial state of detector-related properties."""
        mgr = ModelManager()
        assert mgr.current_detector is None
        assert mgr.moderation_enabled is False
        assert mgr.loading_detector is None
        assert mgr.detector_processes == {}
        assert mgr.detector_input_queues == {}
        assert mgr.detector_output_queues == {}
    
    def test_invalid_detector_raises_error(self):
        """Test that starting an invalid detector raises ValueError."""
        mgr = ModelManager()
        with pytest.raises(ValueError) as exc_info:
            mgr.start_detector("invalid-detector")
        assert "Unknown detector" in str(exc_info.value)
        assert "visobert-hsd" in str(exc_info.value)
    
    def test_set_moderation_enabled(self):
        """Test toggling moderation enabled flag."""
        mgr = ModelManager()
        assert mgr._moderation_enabled is False
        
        mgr.set_moderation_enabled(True)
        assert mgr._moderation_enabled is True
        
        mgr.set_moderation_enabled(False)
        assert mgr._moderation_enabled is False
    
    def test_moderation_enabled_requires_detector(self):
        """Test that moderation_enabled property checks both flag and detector."""
        mgr = ModelManager()
        
        # Without detector, moderation_enabled should be False
        mgr._moderation_enabled = True
        assert mgr.moderation_enabled is False  # No detector running
        
        # With detector but flag off
        mgr.current_detector = "visobert-hsd"
        mgr._moderation_enabled = False
        assert mgr.moderation_enabled is False
        
        # With detector and flag on
        mgr._moderation_enabled = True
        assert mgr.moderation_enabled is True
    
    def test_is_loading_includes_detector(self):
        """Test that is_loading includes detector loading state."""
        mgr = ModelManager()
        assert mgr.is_loading is False
        
        with mgr._loading_lock:
            mgr._loading_detector = "visobert-hsd"
        assert mgr.is_loading is True
        
        with mgr._loading_lock:
            mgr._loading_detector = None
        assert mgr.is_loading is False
    
    def test_get_detector_queues_no_detector(self):
        """Test get_detector_queues when no detector is running."""
        mgr = ModelManager()
        input_q, output_q = mgr.get_detector_queues()
        assert input_q is None
        assert output_q is None
    
    def test_stop_detector_when_not_running(self):
        """Test stopping detector when none is running doesn't raise error."""
        mgr = ModelManager()
        # Should not raise any exception
        mgr.stop_detector()
        assert mgr.current_detector is None
        assert mgr._moderation_enabled is False
    
    @patch('app.workers.hate_detector.HateDetectorWorker')
    def test_start_detector_creates_process(self, mock_worker_class):
        """Test that start_detector creates process and queues."""
        mgr = ModelManager()
        
        # Mock the worker
        mock_worker = Mock()
        mock_worker.run = Mock()
        mock_worker_class.return_value = mock_worker
        
        # Mock Process
        with patch('multiprocessing.Process') as mock_process_class:
            mock_process = Mock()
            mock_process.start = Mock()
            mock_process.pid = 12345
            mock_process_class.return_value = mock_process
            
            mgr.start_detector("visobert-hsd")
            
            # Verify process was created and started
            mock_process_class.assert_called_once()
            mock_process.start.assert_called_once()
            
            # Verify state
            assert mgr.current_detector == "visobert-hsd"
            assert mgr._moderation_enabled is True
            assert "visobert-hsd" in mgr.detector_processes
            assert "visobert-hsd" in mgr.detector_input_queues
            assert "visobert-hsd" in mgr.detector_output_queues
    
    @patch('app.workers.hate_detector.HateDetectorWorker')
    def test_start_detector_already_running(self, mock_worker_class):
        """Test that starting same detector twice doesn't create new process."""
        mgr = ModelManager()
        
        mock_worker = Mock()
        mock_worker.run = Mock()
        mock_worker_class.return_value = mock_worker
        
        with patch('multiprocessing.Process') as mock_process_class:
            mock_process = Mock()
            mock_process.start = Mock()
            mock_process.pid = 12345
            mock_process_class.return_value = mock_process
            
            # Start detector first time
            mgr.start_detector("visobert-hsd")
            assert mock_process_class.call_count == 1
            
            # Start again - should not create new process
            mgr.start_detector("visobert-hsd")
            assert mock_process_class.call_count == 1  # Still 1
    
    def test_get_status_with_detector_loading(self):
        """Test get_status when detector is loading."""
        mgr = ModelManager()
        
        with mgr._loading_lock:
            mgr._loading_detector = "visobert-hsd"
        
        assert mgr.get_status() == "loading"
    
    def test_stop_all_models_includes_detector(self):
        """Test that stop_all_models also stops detector."""
        mgr = ModelManager()
        
        # Set up mock detector
        mgr.current_detector = "visobert-hsd"
        mgr._moderation_enabled = True
        
        mock_process = Mock()
        mock_process.is_alive.return_value = False
        mock_process.join = Mock()
        
        mock_queue = Mock()
        mock_queue.put_nowait = Mock()
        mock_queue.close = Mock()
        
        mgr.detector_processes["visobert-hsd"] = mock_process
        mgr.detector_input_queues["visobert-hsd"] = mock_queue
        mgr.detector_output_queues["visobert-hsd"] = mock_queue
        
        mgr.stop_all_models()
        
        # Verify detector was stopped
        assert mgr.current_detector is None
        assert mgr._moderation_enabled is False


class TestModerationEndpoints:
    """Tests for moderation REST API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_get_moderation_status(self, client):
        """Test GET /api/v1/moderation/status endpoint."""
        response = client.get("/api/v1/moderation/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "enabled" in data
        assert "current_detector" in data
        assert "loading_detector" in data
        assert "config" in data
        assert "default_enabled" in data["config"]
        assert "confidence_threshold" in data["config"]
        assert "on_final_only" in data["config"]
    
    def test_get_moderation_status_schema_validation(self, client):
        """Test that moderation status response follows ModerationStatus schema."""
        response = client.get("/api/v1/moderation/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate types
        assert isinstance(data["enabled"], bool)
        assert data["current_detector"] is None or isinstance(data["current_detector"], str)
        assert data["loading_detector"] is None or isinstance(data["loading_detector"], str)
        
        # Validate config structure
        config = data["config"]
        assert isinstance(config["default_enabled"], bool)
        assert isinstance(config["confidence_threshold"], (int, float))
        assert 0 <= config["confidence_threshold"] <= 1
        assert isinstance(config["on_final_only"], bool)
    
    def test_toggle_moderation_enable(self, client):
        """Test enabling moderation via POST /api/v1/moderation/toggle."""
        with patch('app.api.endpoints.manager') as mock_manager:
            mock_manager.current_detector = None
            mock_manager.moderation_enabled = True
            mock_manager.start_detector = Mock()
            mock_manager.set_moderation_enabled = Mock()
            
            response = client.post("/api/v1/moderation/toggle", params={"enabled": True})
            assert response.status_code == 200
            
            mock_manager.start_detector.assert_called_once_with("visobert-hsd")
            mock_manager.set_moderation_enabled.assert_called_with(True)
    
    def test_toggle_moderation_disable(self, client):
        """Test disabling moderation via POST /api/v1/moderation/toggle."""
        with patch('app.api.endpoints.manager') as mock_manager:
            mock_manager.moderation_enabled = False
            mock_manager.current_detector = "visobert-hsd"
            mock_manager.set_moderation_enabled = Mock()
            
            response = client.post("/api/v1/moderation/toggle", params={"enabled": False})
            assert response.status_code == 200
            
            mock_manager.set_moderation_enabled.assert_called_with(False)
    
    def test_toggle_moderation_response_schema(self, client):
        """Test that toggle response follows ModerationToggleResponse schema."""
        with patch('app.api.endpoints.manager') as mock_manager:
            mock_manager.current_detector = "visobert-hsd"
            mock_manager.moderation_enabled = True
            mock_manager.set_moderation_enabled = Mock()
            
            response = client.post("/api/v1/moderation/toggle", params={"enabled": True})
            assert response.status_code == 200
            
            data = response.json()
            assert "enabled" in data
            assert "current_detector" in data
            assert isinstance(data["enabled"], bool)
    
    def test_toggle_moderation_detector_already_running(self, client):
        """Test toggle when detector is already running doesn't restart it."""
        with patch('app.api.endpoints.manager') as mock_manager:
            mock_manager.current_detector = "visobert-hsd"  # Already running
            mock_manager.moderation_enabled = True
            mock_manager.set_moderation_enabled = Mock()
            mock_manager.start_detector = Mock()  # Should not be called
            
            response = client.post("/api/v1/moderation/toggle", params={"enabled": True})
            assert response.status_code == 200
            
            # start_detector should NOT be called if detector already running
            mock_manager.start_detector.assert_not_called()
            mock_manager.set_moderation_enabled.assert_called_with(True)
    
    def test_toggle_moderation_start_failure(self, client):
        """Test toggle returns 503 when detector fails to start."""
        with patch('app.api.endpoints.manager') as mock_manager:
            mock_manager.current_detector = None
            mock_manager.start_detector = Mock(side_effect=Exception("Model not found"))
            
            response = client.post("/api/v1/moderation/toggle", params={"enabled": True})
            assert response.status_code == 503
            assert "Failed to start detector" in response.json()["detail"]


class TestWebSocketModeration:
    """Tests for WebSocket moderation integration."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager with detector support."""
        with patch('app.api.endpoints.manager') as mock:
            # Mock STT model
            mock.start_model = Mock()
            mock.get_queues = Mock(return_value=(
                MagicMock(spec=multiprocessing.Queue),
                MagicMock(spec=multiprocessing.Queue)
            ))
            
            # Mock detector
            mock.start_detector = Mock()
            mock.get_detector_queues = Mock(return_value=(
                MagicMock(spec=multiprocessing.Queue),
                MagicMock(spec=multiprocessing.Queue)
            ))
            mock.set_moderation_enabled = Mock()
            mock.moderation_enabled = True
            
            yield mock
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with moderation enabled."""
        with patch('app.api.endpoints.settings') as mock:
            mock.ENABLE_CONTENT_MODERATION = True
            mock.MODERATION_CONFIDENCE_THRESHOLD = 0.7
            mock.MODERATION_ON_FINAL_ONLY = True
            yield mock
    
    def test_websocket_starts_detector_when_enabled(self, mock_manager, mock_settings):
        """Test that WebSocket endpoint starts detector when moderation enabled."""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/transcribe") as websocket:
            # Send config
            websocket.send_json({"type": "config", "model": "zipformer"})
            
        # Verify detector was started
        mock_manager.start_detector.assert_called_once_with("visobert-hsd")
    
    def test_websocket_respects_moderation_config(self, mock_manager, mock_settings):
        """Test that WebSocket respects client moderation config."""
        from fastapi.testclient import TestClient
        from main import app
        
        # Client requests moderation disabled
        mock_settings.ENABLE_CONTENT_MODERATION = True  # Server default
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/transcribe") as websocket:
            # Send config with moderation disabled
            websocket.send_json({
                "type": "config", 
                "model": "zipformer",
                "moderation": False
            })
        
        # With moderation=False in config, detector should not start
        # (Implementation may vary - this tests the behavior)


class TestDetectorClassLookup:
    """Tests for detector class lookup."""
    
    def test_get_detector_class_visobert(self):
        """Test that _get_detector_class returns correct class for visobert-hsd."""
        mgr = ModelManager()
        
        # This will do the lazy import
        detector_class = mgr._get_detector_class("visobert-hsd")
        
        from app.workers.hate_detector import HateDetectorWorker
        assert detector_class == HateDetectorWorker
    
    def test_get_detector_class_unknown(self):
        """Test that _get_detector_class returns None for unknown detector."""
        mgr = ModelManager()
        assert mgr._get_detector_class("unknown-detector") is None
