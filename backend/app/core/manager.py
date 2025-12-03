import logging
import multiprocessing
import threading
from typing import Dict, Optional, Tuple
from app.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages AI model worker processes using multiprocessing.
    
    Each model runs in a separate process to avoid GIL limitations
    and ensure CPU-bound inference doesn't block the event loop.
    
    Supports two types of workers:
    - STT models (zipformer): Speech-to-text transcription
    - Detector models (visobert-hsd): Content moderation / hate speech detection
    """
    
    VALID_MODELS = ["zipformer"]
    VALID_DETECTORS = ["visobert-hsd"]
    
    def __init__(self):
        # STT model resources
        self.active_processes: Dict[str, multiprocessing.Process] = {}
        self.input_queues: Dict[str, multiprocessing.Queue] = {}
        self.output_queues: Dict[str, multiprocessing.Queue] = {}
        self.current_model: Optional[str] = None
        
        # Detector resources (separate from STT)
        self.detector_processes: Dict[str, multiprocessing.Process] = {}
        self.detector_input_queues: Dict[str, multiprocessing.Queue] = {}
        self.detector_output_queues: Dict[str, multiprocessing.Queue] = {}
        self.current_detector: Optional[str] = None
        self._moderation_enabled: bool = False
        
        # Track loading state
        self._loading_model: Optional[str] = None
        self._loading_detector: Optional[str] = None
        self._loading_lock = threading.Lock()

    @property
    def is_loading(self) -> bool:
        """Check if a model or detector is currently being loaded."""
        with self._loading_lock:
            return self._loading_model is not None or self._loading_detector is not None

    @property
    def loading_model(self) -> Optional[str]:
        """Get the name of the model currently being loaded."""
        with self._loading_lock:
            return self._loading_model

    @property
    def loading_detector(self) -> Optional[str]:
        """Get the name of the detector currently being loaded."""
        with self._loading_lock:
            return self._loading_detector

    @property
    def moderation_enabled(self) -> bool:
        """Check if content moderation is currently enabled and running."""
        return self._moderation_enabled and self.current_detector is not None

    def get_status(self) -> str:
        """Get the current status of the model manager."""
        with self._loading_lock:
            if self._loading_model or self._loading_detector:
                return "loading"
            elif self.current_model and self.current_model in self.active_processes:
                return "ready"
            else:
                return "idle"

    def start_model(self, model_name: str) -> None:
        """Start a model worker process."""
        if model_name not in self.VALID_MODELS:
            raise ValueError(f"Unknown model: {model_name}. Valid options: {self.VALID_MODELS}")
            
        if self.current_model == model_name and model_name in self.active_processes:
            logger.debug(f"Model {model_name} already running")
            return

        # Set loading state
        with self._loading_lock:
            self._loading_model = model_name

        try:
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
        finally:
            # Clear loading state
            with self._loading_lock:
                self._loading_model = None

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
        """Stop all running model workers and detectors."""
        # Stop STT models
        for model_name in list(self.active_processes.keys()):
            self.current_model = model_name
            self.stop_current_model()
        # Stop detectors
        self.stop_detector()

    def get_queues(self, model_name: str) -> Tuple[Optional[multiprocessing.Queue], Optional[multiprocessing.Queue]]:
        """Get input and output queues for a model."""
        if model_name != self.current_model:
            return None, None
        return self.input_queues.get(model_name), self.output_queues.get(model_name)

    # ========== Detector Management Methods ==========
    
    def start_detector(self, detector_name: str = "visobert-hsd") -> None:
        """Start a detector worker process for content moderation."""
        if detector_name not in self.VALID_DETECTORS:
            raise ValueError(f"Unknown detector: {detector_name}. Valid options: {self.VALID_DETECTORS}")
        
        if self.current_detector == detector_name and detector_name in self.detector_processes:
            logger.debug(f"Detector {detector_name} already running")
            self._moderation_enabled = True
            return
        
        # Set loading state
        with self._loading_lock:
            self._loading_detector = detector_name
        
        try:
            # Stop any existing detector first
            self.stop_detector()
            
            logger.info(f"Starting detector: {detector_name}")
            input_q = multiprocessing.Queue(maxsize=100)
            output_q = multiprocessing.Queue(maxsize=100)
            
            detector_class = self._get_detector_class(detector_name)
            if not detector_class:
                raise ValueError(f"No worker implementation for detector: {detector_name}")
            
            worker = detector_class(input_q, output_q, detector_name)
            
            process = multiprocessing.Process(target=worker.run, daemon=True)
            process.start()
            
            self.detector_processes[detector_name] = process
            self.detector_input_queues[detector_name] = input_q
            self.detector_output_queues[detector_name] = output_q
            self.current_detector = detector_name
            self._moderation_enabled = True
            
            logger.info(f"Detector {detector_name} started (PID: {process.pid})")
        finally:
            # Clear loading state
            with self._loading_lock:
                self._loading_detector = None

    def stop_detector(self) -> None:
        """Stop the currently running detector worker."""
        if not self.current_detector or self.current_detector not in self.detector_processes:
            self._moderation_enabled = False
            return
        
        detector_name = self.current_detector
        logger.info(f"Stopping detector: {detector_name}")
        
        # Send stop signal
        if detector_name in self.detector_input_queues:
            try:
                self.detector_input_queues[detector_name].put_nowait("STOP")
            except Exception as e:
                logger.warning(f"Could not send stop signal to detector: {e}")
        
        # Wait for graceful shutdown
        process = self.detector_processes[detector_name]
        process.join(timeout=10)
        
        if process.is_alive():
            logger.warning(f"Detector {detector_name} did not stop gracefully, terminating")
            process.terminate()
            process.join(timeout=5)
            
            if process.is_alive():
                logger.error(f"Detector {detector_name} still alive after terminate, killing")
                process.kill()
        
        # Cleanup
        self._cleanup_detector(detector_name)
        self.current_detector = None
        self._moderation_enabled = False
        logger.info(f"Detector {detector_name} stopped")

    def get_detector_queues(self) -> Tuple[Optional[multiprocessing.Queue], Optional[multiprocessing.Queue]]:
        """Get input and output queues for the current detector."""
        if not self.current_detector:
            return None, None
        return (
            self.detector_input_queues.get(self.current_detector),
            self.detector_output_queues.get(self.current_detector)
        )

    def set_moderation_enabled(self, enabled: bool) -> None:
        """Enable or disable content moderation without stopping the detector."""
        self._moderation_enabled = enabled
        logger.info(f"Content moderation {'enabled' if enabled else 'disabled'}")

    def _cleanup_detector(self, detector_name: str) -> None:
        """Clean up resources for a detector."""
        if detector_name in self.detector_processes:
            del self.detector_processes[detector_name]
        if detector_name in self.detector_input_queues:
            try:
                self.detector_input_queues[detector_name].close()
            except Exception:
                pass
            del self.detector_input_queues[detector_name]
        if detector_name in self.detector_output_queues:
            try:
                self.detector_output_queues[detector_name].close()
            except Exception:
                pass
            del self.detector_output_queues[detector_name]

    def _get_detector_class(self, detector_name: str):
        """Get the detector worker class for a detector name (lazy import)."""
        if detector_name == "visobert-hsd":
            from app.workers.hate_detector import HateDetectorWorker
            return HateDetectorWorker
        return None

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
        return None


# Global manager instance
manager = ModelManager()
