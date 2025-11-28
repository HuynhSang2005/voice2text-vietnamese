import logging
import multiprocessing
from typing import Dict, Optional, Tuple
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages AI model worker processes using multiprocessing.
    
    Each model runs in a separate process to avoid GIL limitations
    and ensure CPU-bound inference doesn't block the event loop.
    """
    
    VALID_MODELS = ["zipformer", "faster-whisper", "phowhisper", "hkab"]
    
    def __init__(self):
        self.active_processes: Dict[str, multiprocessing.Process] = {}
        self.input_queues: Dict[str, multiprocessing.Queue] = {}
        self.output_queues: Dict[str, multiprocessing.Queue] = {}
        self.current_model: Optional[str] = None

    def start_model(self, model_name: str) -> None:
        """Start a model worker process."""
        if model_name not in self.VALID_MODELS:
            raise ValueError(f"Unknown model: {model_name}. Valid options: {self.VALID_MODELS}")
            
        if self.current_model == model_name and model_name in self.active_processes:
            logger.debug(f"Model {model_name} already running")
            return

        self.stop_current_model()

        logger.info(f"Starting model: {model_name}")
        input_q = multiprocessing.Queue(maxsize=100)  # Limit queue size
        output_q = multiprocessing.Queue(maxsize=100)
        
        worker_class = self._get_worker_class(model_name)
        if not worker_class:
            raise ValueError(f"No worker implementation for model: {model_name}")
        
        worker = worker_class(input_q, output_q, model_name)
        
        process = multiprocessing.Process(target=worker.run, daemon=True)
        process.start()
        
        self.active_processes[model_name] = process
        self.input_queues[model_name] = input_q
        self.output_queues[model_name] = output_q
        self.current_model = model_name
        
        logger.info(f"Model {model_name} started (PID: {process.pid})")

    def stop_current_model(self) -> None:
        """Stop the currently running model worker."""
        if not self.current_model or self.current_model not in self.active_processes:
            return
            
        model_name = self.current_model
        logger.info(f"Stopping model: {model_name}")
        
        # Send stop signal
        if model_name in self.input_queues:
            try:
                self.input_queues[model_name].put_nowait("STOP")
            except Exception as e:
                logger.warning(f"Could not send stop signal: {e}")
        
        # Wait for graceful shutdown
        process = self.active_processes[model_name]
        process.join(timeout=10)
        
        if process.is_alive():
            logger.warning(f"Model {model_name} did not stop gracefully, terminating")
            process.terminate()
            process.join(timeout=5)
            
            if process.is_alive():
                logger.error(f"Model {model_name} still alive after terminate, killing")
                process.kill()
        
        # Cleanup
        self._cleanup_model(model_name)
        self.current_model = None
        logger.info(f"Model {model_name} stopped")

    def stop_all_models(self) -> None:
        """Stop all running model workers."""
        for model_name in list(self.active_processes.keys()):
            self.current_model = model_name
            self.stop_current_model()

    def get_queues(self, model_name: str) -> Tuple[Optional[multiprocessing.Queue], Optional[multiprocessing.Queue]]:
        """Get input and output queues for a model."""
        if model_name != self.current_model:
            return None, None
        return self.input_queues.get(model_name), self.output_queues.get(model_name)

    def _cleanup_model(self, model_name: str) -> None:
        """Clean up resources for a model."""
        if model_name in self.active_processes:
            del self.active_processes[model_name]
        if model_name in self.input_queues:
            try:
                self.input_queues[model_name].close()
            except Exception:
                pass
            del self.input_queues[model_name]
        if model_name in self.output_queues:
            try:
                self.output_queues[model_name].close()
            except Exception:
                pass
            del self.output_queues[model_name]

    def _get_worker_class(self, model_name: str):
        """Get the worker class for a model name (lazy import)."""
        if model_name == "zipformer":
            from app.workers.zipformer import ZipformerWorker
            return ZipformerWorker
        elif model_name in ["faster-whisper", "phowhisper"]:
            from app.workers.whisper import WhisperWorker
            return WhisperWorker
        elif model_name == "hkab":
            from app.workers.hkab import HKABWorker
            return HKABWorker
        return None


# Global manager instance
manager = ModelManager()
