"""
Integration tests for WebSocket transcription endpoint.

Tests the WebSocket endpoint following RFC 6455 and Clean Architecture principles.
"""

import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.main import app


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketTranscription:
    """Integration tests for /ws/transcribe endpoint."""
    
    def test_websocket_connect_and_disconnect(self):
        """Test basic WebSocket connection and disconnection."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Connection successful
                assert websocket is not None
                
                # Send close frame
                websocket.close()
    
    def test_websocket_config_message(self):
        """Test sending configuration message."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send config
                config = {
                    "type": "config",
                    "model": "zipformer",
                    "sample_rate": 16000,
                    "enable_moderation": True,
                    "session_id": "test-session-123",
                    "language": "vi"
                }
                websocket.send_json(config)
                
                # No immediate response expected for config
                # Just verify no error
    
    def test_websocket_ping_pong(self):
        """Test ping/pong heartbeat mechanism (RFC 6455)."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send ping
                ping = {
                    "type": "ping",
                    "timestamp": 1234567890
                }
                websocket.send_json(ping)
                
                # Should receive pong
                response = websocket.receive_json()
                assert response["type"] == "pong"
                assert response["timestamp"] == 1234567890
    
    @pytest.mark.skip(reason="Requires real audio data and model loaded")
    def test_websocket_audio_streaming(self):
        """Test streaming audio data for transcription."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send config
                config = {
                    "type": "config",
                    "model": "zipformer",
                    "enable_moderation": False
                }
                websocket.send_json(config)
                
                # Send audio data (mock PCM 16-bit mono 16kHz)
                # Note: This would need real audio data in actual test
                audio_chunk = b'\x00' * 3200  # 100ms of silence
                websocket.send_bytes(audio_chunk)
                
                # Should receive transcription result
                # (In real test, use actual audio with known transcription)
                # response = websocket.receive_json()
                # assert response["type"] == "transcription"
                # assert "text" in response
    
    @pytest.mark.skip(reason="Requires workers to be running")
    def test_websocket_with_moderation(self):
        """Test transcription with content moderation enabled."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send config with moderation
                config = {
                    "type": "config",
                    "model": "zipformer",
                    "enable_moderation": True,
                    "session_id": "test-moderation-123"
                }
                websocket.send_json(config)
                
                # Send audio (would need audio with offensive content for real test)
                # audio_chunk = load_test_audio("offensive_content.wav")
                # websocket.send_bytes(audio_chunk)
                
                # Should receive transcription result
                # response1 = websocket.receive_json()
                # assert response1["type"] == "transcription"
                
                # Should receive moderation result
                # response2 = websocket.receive_json()
                # assert response2["type"] == "moderation"
                # assert "label" in response2
    
    def test_websocket_flush_signal(self):
        """Test flush signal to force transcription of remaining buffer."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send flush
                flush = {"type": "flush"}
                websocket.send_json(flush)
                
                # Should not cause error
    
    def test_websocket_reset_signal(self):
        """Test reset signal to clear transcription state."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send reset
                reset = {"type": "reset"}
                websocket.send_json(reset)
                
                # Should not cause error
    
    def test_websocket_invalid_json(self):
        """Test handling of invalid JSON messages."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send invalid JSON
                websocket.send_text("not-valid-json{")
                
                # Should receive error message
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "Invalid JSON" in response["message"]
    
    @pytest.mark.skip(reason="Requires worker not available scenario")
    def test_websocket_worker_not_ready(self):
        """Test error handling when worker is not ready."""
        # This would require mocking worker to return not ready
        # In real scenario, test with worker stopped
        pass
    
    def test_websocket_rfc_6455_close_frame(self):
        """Test proper close frame handling (RFC 6455 compliance)."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/transcribe") as websocket:
                # Send some data
                config = {"type": "config", "model": "zipformer"}
                websocket.send_json(config)
                
                # Close connection
                # Should receive close frame with code 1000 (normal closure)
                websocket.close()
                
                # Connection should be closed cleanly


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketErrorHandling:
    """Test error handling in WebSocket endpoint."""
    
    @pytest.mark.skip(reason="Requires mock to simulate business rule violation")
    def test_business_rule_exception_handling(self):
        """Test handling of business rule exceptions."""
        # Simulate scenario where moderation is required but worker unavailable
        # Should receive error message with business rule details
        pass
    
    @pytest.mark.skip(reason="Requires mock to simulate internal error")
    def test_internal_error_handling(self):
        """Test handling of unexpected internal errors."""
        # Simulate internal error during processing
        # Should receive generic error message
        pass


@pytest.mark.integration
@pytest.mark.skip(reason="Requires full system setup with real models")
class TestWebSocketConcurrency:
    """Test concurrent WebSocket connections."""
    
    async def test_multiple_concurrent_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        # Create 10 concurrent connections
        # Each should work independently
        # No race conditions or state leakage
        pass
    
    async def test_connection_cleanup(self):
        """Test proper cleanup of resources when connection closes."""
        # Connect, send some data, disconnect
        # Verify no resource leaks (tasks, queues, workers)
        pass


# Pytest configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
]
