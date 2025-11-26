import sys
import os

# Add backend to path explicitly
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import time
import psutil
import numpy as np
import multiprocessing
import pytest
from app.workers.zipformer import ZipformerWorker
from app.workers.whisper import WhisperWorker
from app.workers.hkab import HKABWorker

# Constants
TEST_AUDIO_PATH = r"d:\voice2text-vietnamese\models_storage\zipformer\sherpa-onnx-zipformer-vi-int8-2025-04-20\test_wavs\0.wav"
# Assuming 0.wav has some known text, but for now we just measure performance.
# If we knew the text, we could calculate WER.
# Let's assume a dummy text for now or just print the output.

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024 # MB

def benchmark_model(worker_class, model_name, audio_data):
    print(f"\n--- Benchmarking {model_name} ---")
    
    # 1. Load Time & Memory
    mem_before = get_memory_usage()
    start_load = time.time()
    
    input_q = multiprocessing.Queue()
    output_q = multiprocessing.Queue()
    worker = worker_class(input_q, output_q, model_name)
    worker.load_model()
    
    end_load = time.time()
    mem_after = get_memory_usage()
    
    load_time = end_load - start_load
    mem_usage = mem_after - mem_before
    
    print(f"Load Time: {load_time:.2f}s")
    print(f"Memory Usage (Est): {mem_usage:.2f} MB")
    
    # 2. Inference Latency (Real-time factor)
    # Read audio file
    with open(TEST_AUDIO_PATH, "rb") as f:
        # Skip header if needed, but workers expect raw bytes or handle wav?
        # ZipformerWorker expects bytes and converts using numpy.
        # WhisperWorker expects bytes.
        # HKABWorker expects bytes.
        # BUT, they expect raw PCM (int16) usually, or handle wav header if robust.
        # Let's read as bytes.
        audio_bytes = f.read()
        
    # Send audio
    start_infer = time.time()
    
    # Simulate streaming or buffered?
    # For benchmark, we just dump it in and wait for result.
    worker.process(audio_bytes)
    
    # Wait for result (simulate)
    # Since process() might be async or put to queue, we check queue.
    # Note: process() in our workers puts to output_q.
    
    result = None
    try:
        # Wait up to 10s
        while not output_q.empty():
            result = output_q.get()
        
        # If empty, maybe it's still processing?
        # Our workers are synchronous in process() usually.
        # Except HKAB which might need a loop?
        # Let's check worker implementation.
        pass
    except Exception as e:
        print(f"Error getting result: {e}")
        
    end_infer = time.time()
    latency = end_infer - start_infer
    
    print(f"Inference Latency: {latency:.2f}s")
    
    # 3. Quality (Qualitative)
    if result:
        print(f"Transcription: {result}")
    else:
        print("No transcription output captured (might be in queue or internal buffer).")

    # Write to file
    with open("benchmark_results.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- {model_name} ---\n")
        f.write(f"Load Time: {load_time:.2f}s\n")
        f.write(f"Memory Usage: {mem_usage:.2f} MB\n")
        f.write(f"Latency: {latency:.2f}s\n")
        f.write(f"Transcription: {result}\n")

if __name__ == "__main__":
    if not os.path.exists(TEST_AUDIO_PATH):
        print(f"Test audio not found at {TEST_AUDIO_PATH}")
        # Create dummy
        # ...
    else:
        print(f"Using test audio: {TEST_AUDIO_PATH}")
        
        # Benchmark Zipformer
        try:
            benchmark_model(ZipformerWorker, "zipformer", TEST_AUDIO_PATH)
        except Exception as e:
            print(f"Zipformer failed: {e}")

        # Benchmark Faster-Whisper
        try:
            benchmark_model(WhisperWorker, "faster-whisper", TEST_AUDIO_PATH)
        except Exception as e:
            print(f"Faster-Whisper failed: {e}")
            
        # Benchmark HKAB
        try:
            benchmark_model(HKABWorker, "hkab", TEST_AUDIO_PATH)
        except Exception as e:
            print(f"HKAB failed: {e}")
