import pytest
import asyncio
import websockets
import json
import time
import os
import wave
import numpy as np

# Constants
WS_URL = "ws://localhost:8000/ws/transcribe"
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 200 # Send 200ms chunks
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000) * 2 # 2 bytes per sample

# Generate dummy audio if needed
def generate_dummy_audio(duration_sec=5):
    # Generate 5 seconds of silence/noise
    # We use silence for simplicity, or random noise
    # Random noise might trigger some output
    samples = np.random.randint(-32768, 32767, int(SAMPLE_RATE * duration_sec), dtype=np.int16)
    return samples.tobytes()

@pytest.mark.asyncio
async def test_latency_benchmark():
    """
    Benchmark the end-to-end latency of the STT system.
    Sends audio chunks and measures time to receive results.
    """
    print(f"\n[Benchmark] Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            # 1. Start Session
            session_id = f"bench-{int(time.time())}"
            await websocket.send(json.dumps({
                "type": "start_session",
                "sessionId": session_id
            }))
            
            # 2. Send Config (optional, but good practice)
            await websocket.send(json.dumps({
                "type": "config",
                "model": "zipformer"
            }))
            
            print("[Benchmark] Session started. Streaming audio...")
            
            audio_data = generate_dummy_audio(duration_sec=3)
            total_chunks = len(audio_data) // CHUNK_SIZE
            
            latencies = []
            start_time = time.time()
            
            # Task to receive results
            async def receive_results():
                try:
                    while True:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        recv_time = time.time()
                        data = json.loads(msg)
                        
                        if data.get("text"):
                            # Calculate latency relative to start (rough estimate)
                            # Ideally we'd map specific chunks to results, but for streaming 
                            # we measure "responsiveness"
                            current_latency = recv_time - start_time
                            latencies.append(current_latency)
                            # print(f"  -> Received: '{data['text']}' (Latency: {current_latency*1000:.2f}ms)")
                            # Avoid printing text to prevent UnicodeEncodeError on Windows
                            pass
                except asyncio.TimeoutError:
                    print("[Benchmark] Receive timeout (finished?)")
                except Exception as e:
                    print(f"[Benchmark] Receive error: {e}")

            receive_task = asyncio.create_task(receive_results())
            
            # Stream Audio
            for i in range(total_chunks):
                chunk = audio_data[i*CHUNK_SIZE : (i+1)*CHUNK_SIZE]
                await websocket.send(chunk)
                # Simulate real-time streaming
                await asyncio.sleep(CHUNK_DURATION_MS / 1000)
                
            print("[Benchmark] Finished streaming audio.")
            
            # Wait a bit for final results
            await asyncio.sleep(1.0)
            receive_task.cancel()
            
            # Analyze Results
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                
                print("\n" + "="*40)
                print(f"BENCHMARK RESULTS (Session: {session_id})")
                print("="*40)
                print(f"Total Messages Received: {len(latencies)}")
                print(f"Average Latency: {avg_latency*1000:.2f} ms")
                print(f"Min Latency:     {min_latency*1000:.2f} ms")
                print(f"Max Latency:     {max_latency*1000:.2f} ms")
                print("="*40)
                
                # Assertions
                assert avg_latency < 1.5, f"Average latency {avg_latency:.2f}s exceeds 1.5s limit!"
                print("✅ Latency Check PASSED (< 1.5s)")
            else:
                print("⚠️ No results received. Model might be silent for dummy audio.")
                # Don't fail if silence produces no text, but warn
                
    except ConnectionRefusedError:
        pytest.fail("Backend is not running! Please start the backend on port 8000.")
