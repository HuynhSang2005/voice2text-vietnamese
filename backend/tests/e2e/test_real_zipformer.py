import pytest
import multiprocessing
import os
import sys
import wave
import time
import json
import asyncio
import websockets

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../backend"))

from app.workers.zipformer import ZipformerWorker

# Path to a sample wav file
SAMPLE_WAV = os.path.join(os.path.dirname(__file__), "../data/sample_vn.wav")

def create_dummy_wav(filename):
    # Create a 1-second dummy wav file if not exists
    if not os.path.exists(filename):
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # Generate silence/noise
            data = os.urandom(32000)
            wav_file.writeframes(data)

@pytest.fixture(scope="module")
def sample_audio():
    # Ensure sample file exists
    if not os.path.exists(os.path.dirname(SAMPLE_WAV)):
        os.makedirs(os.path.dirname(SAMPLE_WAV))
    
    # In a real scenario, we should download a real VN audio file
    # For now, create a dummy one to test the pipeline flow (not accuracy)
    create_dummy_wav(SAMPLE_WAV)
    return SAMPLE_WAV

def test_zipformer_worker_real_load():
    """Test loading the REAL Zipformer model from disk."""
    input_q = multiprocessing.Queue()
    output_q = multiprocessing.Queue()
    
    worker = ZipformerWorker(input_q, output_q, "zipformer")
    
    try:
        worker.load_model()
        assert worker.recognizer is not None
        print("Real Zipformer model loaded successfully!")
    except Exception as e:
        pytest.fail(f"Failed to load real Zipformer model: {e}")

@pytest.mark.asyncio
async def test_websocket_e2e_flow():
    """Test the full WebSocket flow with a running backend."""
    # This test assumes the backend is running on localhost:8000
    # We can skip it if connection fails
    uri = "ws://localhost:8000/ws/transcribe"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send config
            await websocket.send(json.dumps({"type": "config", "model": "zipformer"}))
            
            # Send audio data (dummy silence)
            audio_data = bytes(8000) # 0.5s
            await websocket.send(audio_data)
            
            # Wait for response (might be empty for silence, but shouldn't error)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received (expected for silence)")
                
    except ConnectionRefusedError:
        pytest.skip("Backend not running on localhost:8000")
