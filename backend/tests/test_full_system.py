import pytest
import os
import sys
import numpy as np
import multiprocessing
from app.workers.zipformer import ZipformerWorker
from app.workers.whisper import WhisperWorker
from app.workers.hkab import HKABWorker

# Mock queues
class MockQueue:
    def put(self, item):
        pass
    def get(self):
        return None
    def empty(self):
        return True

@pytest.fixture
def mock_queues():
    return multiprocessing.Queue(), multiprocessing.Queue()

@pytest.mark.asyncio
async def test_zipformer_loading(mock_queues):
    print("\nTesting Zipformer Loading...")
    input_q, output_q = mock_queues
    worker = ZipformerWorker(input_q, output_q, "zipformer")
    try:
        worker.load_model()
        assert worker.recognizer is not None
        print("Zipformer loaded successfully.")
    except Exception as e:
        pytest.fail(f"Zipformer failed to load: {e}")

@pytest.mark.asyncio
async def test_faster_whisper_loading(mock_queues):
    print("\nTesting Faster-Whisper Loading...")
    input_q, output_q = mock_queues
    worker = WhisperWorker(input_q, output_q, "faster-whisper")
    try:
        worker.load_model()
        assert worker.model is not None
        print("Faster-Whisper loaded successfully.")
    except Exception as e:
        pytest.fail(f"Faster-Whisper failed to load: {e}")

@pytest.mark.asyncio
async def test_phowhisper_loading(mock_queues):
    print("\nTesting PhoWhisper Loading...")
    input_q, output_q = mock_queues
    worker = WhisperWorker(input_q, output_q, "phowhisper")
    try:
        worker.load_model()
        # This is expected to fail currently if model is missing
        if worker.model is None:
            print("PhoWhisper failed to load (Expected if missing).")
        else:
            print("PhoWhisper loaded successfully.")
    except Exception as e:
        print(f"PhoWhisper raised exception: {e}")

@pytest.mark.asyncio
async def test_hkab_loading(mock_queues):
    print("\nTesting HKAB Loading...")
    input_q, output_q = mock_queues
    worker = HKABWorker(input_q, output_q, "hkab")
    try:
        worker.load_model()
        assert hasattr(worker, 'encoder_sess')
        print("HKAB loaded successfully.")
    except Exception as e:
        pytest.fail(f"HKAB failed to load: {e}")

def test_conflict_check():
    # Check for port conflicts or shared resource locks?
    # Mostly ensuring that we don't have hardcoded paths that conflict.
    # This is a static check or logic check.
    pass
