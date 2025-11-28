"""
End-to-End tests for real model loading and WebSocket communication.

These tests:
- Load actual models from disk
- Test real WebSocket communication with running backend
- Require models to be downloaded and backend to be running

Mark: @pytest.mark.e2e - skipped if backend not running
Mark: @pytest.mark.slow - skipped by default, run with -m slow
"""
import pytest
import multiprocessing
import os
import sys
import wave
import time
import json
import asyncio

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.workers.zipformer import ZipformerWorker
from app.workers.whisper import WhisperWorker
from app.workers.hkab import HKABWorker


# =============================================================================
# Test Data Setup
# =============================================================================

SAMPLE_WAV = os.path.join(os.path.dirname(__file__), "../data/sample_vn.wav")
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")


def create_dummy_wav(filename: str, duration_sec: float = 1.0) -> None:
    """Create a dummy WAV file for testing."""
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    if not os.path.exists(filename):
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # int16
            wav_file.setframerate(16000)
            # Generate random audio data
            import numpy as np
            samples = np.random.randint(-32768, 32767, int(16000 * duration_sec), dtype=np.int16)
            wav_file.writeframes(samples.tobytes())


@pytest.fixture(scope="module")
def sample_audio() -> str:
    """Ensure sample audio file exists and return path."""
    create_dummy_wav(SAMPLE_WAV, duration_sec=2.0)
    return SAMPLE_WAV


# =============================================================================
# Real Model Loading Tests
# =============================================================================

class TestRealModelLoading:
    """Test loading actual models from disk."""
    
    @pytest.mark.slow
    def test_zipformer_worker_real_load(self):
        """Test loading the REAL Zipformer model from disk."""
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        
        worker = ZipformerWorker(input_q, output_q, "zipformer")
        
        try:
            worker.load_model()
            assert worker.recognizer is not None
            assert worker.stream is not None
            print("✅ Real Zipformer model loaded successfully!")
        except FileNotFoundError as e:
            pytest.skip(f"Zipformer model files not found: {e}")
        except Exception as e:
            pytest.fail(f"Failed to load real Zipformer model: {e}")
        finally:
            input_q.close()
            output_q.close()
    
    @pytest.mark.slow
    def test_whisper_worker_real_load(self):
        """Test loading the REAL faster-whisper model."""
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        
        worker = WhisperWorker(input_q, output_q, "faster-whisper")
        
        try:
            worker.load_model()
            assert worker.model is not None
            print("✅ Real Faster-Whisper model loaded successfully!")
        except Exception as e:
            pytest.fail(f"Failed to load real Whisper model: {e}")
        finally:
            input_q.close()
            output_q.close()
    
    @pytest.mark.slow
    def test_hkab_worker_real_load(self):
        """Test loading the REAL HKAB model from disk."""
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        
        worker = HKABWorker(input_q, output_q, "hkab")
        
        try:
            worker.load_model()
            assert hasattr(worker, 'encoder_sess')
            assert hasattr(worker, 'decoder_sess')
            assert hasattr(worker, 'jointer_sess')
            print("✅ Real HKAB model loaded successfully!")
        except FileNotFoundError as e:
            pytest.skip(f"HKAB model files not found: {e}")
        except Exception as e:
            pytest.fail(f"Failed to load real HKAB model: {e}")
        finally:
            input_q.close()
            output_q.close()


# =============================================================================
# Real Transcription Tests
# =============================================================================

class TestRealTranscription:
    """Test actual transcription with real models."""
    
    @pytest.mark.slow
    def test_zipformer_real_transcription(self, sample_audio):
        """Test Zipformer transcribes real audio."""
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        
        worker = ZipformerWorker(input_q, output_q, "zipformer")
        
        try:
            worker.load_model()
            
            # Read audio file
            with wave.open(sample_audio, 'rb') as wav:
                audio_data = wav.readframes(wav.getnframes())
            
            # Process audio
            worker.process(audio_data)
            
            # Check output queue
            if not output_q.empty():
                result = output_q.get_nowait()
                print(f"Zipformer transcription: {result}")
                assert "text" in result
                assert "model" in result
                assert result["model"] == "zipformer"
            else:
                # May not have output for random noise
                print("No transcription output (expected for random audio)")
                
        except FileNotFoundError:
            pytest.skip("Zipformer model files not found")
        finally:
            input_q.close()
            output_q.close()


# =============================================================================
# WebSocket E2E Tests
# =============================================================================

class TestWebSocketE2E:
    """Test full WebSocket flow with running backend."""
    
    @pytest.fixture
    def ws_uri(self):
        """WebSocket URI for local backend."""
        return "ws://localhost:8000/ws/transcribe"
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_connection(self, ws_uri):
        """Test WebSocket connection to running backend."""
        import websockets
        
        try:
            async with websockets.connect(ws_uri, close_timeout=5) as websocket:
                # Send config
                await websocket.send(json.dumps({
                    "type": "config",
                    "model": "zipformer"
                }))
                
                # Send dummy audio
                audio_data = bytes(8000)  # 0.25 seconds at 16kHz
                await websocket.send(audio_data)
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    print(f"Received: {data}")
                    assert "text" in data or "error" in data
                except asyncio.TimeoutError:
                    print("No response received (expected for short audio)")
                    
        except ConnectionRefusedError:
            pytest.skip("Backend not running on localhost:8000")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_model_switch(self, ws_uri):
        """Test switching models via WebSocket."""
        import websockets
        
        try:
            async with websockets.connect(ws_uri, close_timeout=5) as websocket:
                # Start with zipformer
                await websocket.send(json.dumps({
                    "type": "config",
                    "model": "zipformer"
                }))
                
                # Switch to hkab
                await websocket.send(json.dumps({
                    "type": "config",
                    "model": "hkab"
                }))
                
                # Send audio
                await websocket.send(bytes(8000))
                
                # Should not error
                print("Model switch completed without error")
                
        except ConnectionRefusedError:
            pytest.skip("Backend not running on localhost:8000")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_session_management(self, ws_uri):
        """Test session management via WebSocket."""
        import websockets
        
        try:
            async with websockets.connect(ws_uri, close_timeout=5) as websocket:
                # Start session
                session_id = f"test-{int(time.time())}"
                await websocket.send(json.dumps({
                    "type": "start_session",
                    "sessionId": session_id
                }))
                
                # Send some audio
                await websocket.send(bytes(16000))
                
                # Start new session (should reset worker state)
                await websocket.send(json.dumps({
                    "type": "start_session",
                    "sessionId": f"test-{int(time.time()) + 1}"
                }))
                
                print("Session management completed without error")
                
        except ConnectionRefusedError:
            pytest.skip("Backend not running on localhost:8000")


# =============================================================================
# Integration Smoke Tests
# =============================================================================

class TestSmoke:
    """Quick smoke tests for basic functionality."""
    
    def test_imports(self):
        """Test all workers can be imported."""
        from app.workers.zipformer import ZipformerWorker
        from app.workers.whisper import WhisperWorker
        from app.workers.hkab import HKABWorker
        from app.core.manager import ModelManager, manager
        
        assert ZipformerWorker is not None
        assert WhisperWorker is not None
        assert HKABWorker is not None
        assert ModelManager is not None
        assert manager is not None
    
    def test_worker_inheritance(self):
        """Test workers inherit from BaseWorker."""
        from app.workers.base import BaseWorker
        from app.workers.zipformer import ZipformerWorker
        from app.workers.whisper import WhisperWorker
        from app.workers.hkab import HKABWorker
        
        assert issubclass(ZipformerWorker, BaseWorker)
        assert issubclass(WhisperWorker, BaseWorker)
        assert issubclass(HKABWorker, BaseWorker)
