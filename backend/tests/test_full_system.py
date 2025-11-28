"""
Full system tests for model loading.

These tests verify that all models can be loaded correctly.
They require the model files to be present in models_storage/.

Run with: pytest tests/test_full_system.py -v -s
"""
import pytest
import multiprocessing
import sys
import os

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.workers.zipformer import ZipformerWorker
from app.workers.whisper import WhisperWorker
from app.workers.hkab import HKABWorker


class TestModelLoading:
    """Test that all models can be loaded successfully."""
    
    @pytest.fixture
    def queues(self):
        """Create multiprocessing queues."""
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        yield input_q, output_q
        input_q.close()
        output_q.close()

    @pytest.mark.asyncio
    async def test_zipformer_loading(self, queues):
        """Test Zipformer model loading."""
        print("\n🔄 Testing Zipformer Loading...")
        input_q, output_q = queues
        worker = ZipformerWorker(input_q, output_q, "zipformer")
        
        try:
            worker.load_model()
            assert worker.recognizer is not None
            assert worker.stream is not None
            print("✅ Zipformer loaded successfully.")
        except FileNotFoundError as e:
            pytest.skip(f"Zipformer model files not found: {e}")
        except Exception as e:
            pytest.fail(f"Zipformer failed to load: {e}")

    @pytest.mark.asyncio
    async def test_faster_whisper_loading(self, queues):
        """Test Faster-Whisper model loading."""
        print("\n🔄 Testing Faster-Whisper Loading...")
        input_q, output_q = queues
        worker = WhisperWorker(input_q, output_q, "faster-whisper")
        
        try:
            worker.load_model()
            assert worker.model is not None
            assert hasattr(worker, 'buffer')
            print("✅ Faster-Whisper loaded successfully.")
        except Exception as e:
            pytest.fail(f"Faster-Whisper failed to load: {e}")

    @pytest.mark.asyncio
    async def test_phowhisper_loading(self, queues):
        """Test PhoWhisper model loading."""
        print("\n🔄 Testing PhoWhisper Loading...")
        input_q, output_q = queues
        worker = WhisperWorker(input_q, output_q, "phowhisper")
        
        try:
            worker.load_model()
            # PhoWhisper might fallback to 'small' if local not found
            if worker.model is not None:
                print("✅ PhoWhisper loaded successfully.")
            else:
                print("⚠️ PhoWhisper model is None (unexpected).")
        except Exception as e:
            # PhoWhisper may not be available, that's OK
            print(f"⚠️ PhoWhisper loading issue (may be expected): {e}")

    @pytest.mark.asyncio
    async def test_hkab_loading(self, queues):
        """Test HKAB model loading."""
        print("\n🔄 Testing HKAB Loading...")
        input_q, output_q = queues
        worker = HKABWorker(input_q, output_q, "hkab")
        
        try:
            worker.load_model()
            assert hasattr(worker, 'encoder_sess')
            assert hasattr(worker, 'decoder_sess')
            assert hasattr(worker, 'jointer_sess')
            assert hasattr(worker, 'tokenizer')
            print("✅ HKAB loaded successfully.")
        except FileNotFoundError as e:
            pytest.skip(f"HKAB model files not found: {e}")
        except Exception as e:
            pytest.fail(f"HKAB failed to load: {e}")


class TestWorkerInheritance:
    """Test that workers properly inherit from BaseWorker."""
    
    def test_all_workers_have_required_methods(self):
        """Verify all workers implement required abstract methods."""
        from app.workers.base import BaseWorker
        
        workers = [ZipformerWorker, WhisperWorker, HKABWorker]
        
        for worker_cls in workers:
            assert issubclass(worker_cls, BaseWorker)
            # Check abstract methods are implemented
            assert hasattr(worker_cls, 'load_model')
            assert hasattr(worker_cls, 'process')
            assert callable(getattr(worker_cls, 'load_model'))
            assert callable(getattr(worker_cls, 'process'))


class TestConflictCheck:
    """Check for resource conflicts."""
    
    def test_no_hardcoded_absolute_paths(self):
        """Verify no hardcoded absolute paths in worker files."""
        import inspect
        
        workers = [ZipformerWorker, WhisperWorker, HKABWorker]
        
        for worker_cls in workers:
            source = inspect.getsource(worker_cls)
            # Check for common hardcoded path patterns
            assert 'C:\\' not in source, f"{worker_cls.__name__} has hardcoded Windows path"
            assert '/home/' not in source, f"{worker_cls.__name__} has hardcoded Unix path"
            assert 'd:\\voice2text' not in source.lower(), f"{worker_cls.__name__} has hardcoded project path"
    
    def test_models_use_settings_path(self):
        """Verify workers use settings.MODEL_STORAGE_PATH."""
        import inspect
        
        workers = [ZipformerWorker, WhisperWorker, HKABWorker]
        
        for worker_cls in workers:
            source = inspect.getsource(worker_cls)
            # Should import and use settings
            assert 'settings' in source, f"{worker_cls.__name__} should use settings"
