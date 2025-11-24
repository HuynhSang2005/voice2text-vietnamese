import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_websocket_transcription_flow():
    # We need to mock the manager because we don't want to spawn real processes in tests
    with patch("app.api.endpoints.manager") as mock_manager:
        # Setup mock queues
        input_q = MagicMock()
        output_q = MagicMock()
        
        # When get_queues is called, return our mocks
        mock_manager.get_queues.return_value = (input_q, output_q)
        
        # Mock output queue to return a result immediately then be empty
        # This simulates the worker producing a result
        output_q.empty.side_effect = [False, True, True, True] # Not empty, then empty...
        output_q.get_nowait.return_value = {"text": "Test transcription", "is_final": False}
        
        client = TestClient(app)
        with client.websocket_connect("/ws/transcribe") as websocket:
            # 1. Send Config
            websocket.send_text('{"type": "config", "model": "zipformer"}')
            
            # 2. Send Audio (dummy bytes)
            websocket.send_bytes(b"\x00" * 100)
            
            # 3. Receive Result
            data = websocket.receive_json()
            assert data["text"] == "Test transcription"
            
            # Verify manager was called
            mock_manager.start_model.assert_called_with("zipformer")
            input_q.put.assert_called()
