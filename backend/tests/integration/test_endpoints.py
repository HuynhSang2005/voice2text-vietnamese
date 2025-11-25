import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../backend"))

from main import app
from app.core.manager import manager

client = TestClient(app)

def test_get_models():
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["id"] == "zipformer"

@patch("app.core.manager.ModelManager.get_queues")
@patch("app.core.manager.ModelManager.start_model")
def test_switch_model(mock_start_model, mock_get_queues):
    response = client.post("/models/switch?model=zipformer")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_start_model.assert_called_with("zipformer")

@patch("app.core.manager.ModelManager.start_model")
def test_switch_invalid_model(mock_start_model):

    mock_start_model.side_effect = ValueError("Invalid model")
    response = client.post("/models/switch?model=invalid")
    assert response.status_code == 400

@patch("app.core.manager.ModelManager.get_queues")
@patch("app.core.manager.ModelManager.start_model")
@pytest.mark.skip(reason="Covered by E2E test backend/tests/e2e/test_real_zipformer.py")
def test_websocket_connection(mock_start_model, mock_get_queues):
    # Mock queues
    input_q = MagicMock()
    output_q = MagicMock()
    mock_get_queues.return_value = (input_q, output_q)
    
    with client.websocket_connect("/ws/transcribe") as websocket:
        # Send config
        websocket.send_json({"type": "config", "model": "zipformer"})
        
        # Send audio bytes
        websocket.send_bytes(bytes(100))
        
        # Verify manager called
        mock_start_model.assert_called_with("zipformer")
        input_q.put.assert_called()
