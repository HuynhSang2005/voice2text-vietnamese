import multiprocessing
from typing import Dict, Optional
from app.workers.base import BaseWorker
# Import specific workers here to register them or map them
# from app.workers.zipformer import ZipformerWorker
# from app.workers.whisper import WhisperWorker

class ModelManager:
    def __init__(self):
        self.active_processes: Dict[str, multiprocessing.Process] = {}
        self.input_queues: Dict[str, multiprocessing.Queue] = {}
        self.output_queues: Dict[str, multiprocessing.Queue] = {}
        self.current_model: Optional[str] = None

    def start_model(self, model_name: str):
        if self.current_model == model_name and model_name in self.active_processes:
            return # Already running

        self.stop_current_model()

        print(f"Starting model: {model_name}")
        input_q = multiprocessing.Queue()
        output_q = multiprocessing.Queue()
        
        worker_class = self._get_worker_class(model_name)
        if not worker_class:
            raise ValueError(f"Unknown model: {model_name}")
            
        # Instantiate worker
        # Note: We need to pass the class and arguments to the process target
        # But BaseWorker.run is an instance method. 
        # Strategy: Create a wrapper function or use the instance's run method if pickleable.
        # Better: Instantiate worker inside the process target to avoid pickling large objects?
        # Actually, BaseWorker init just stores paths and queues, so it's lightweight.
        # The heavy loading happens in load_model() called inside run().
        
        worker = worker_class(input_q, output_q, model_name) # Pass model_name or path
        
        process = multiprocessing.Process(target=worker.run)
        process.start()
        
        self.active_processes[model_name] = process
        self.input_queues[model_name] = input_q
        self.output_queues[model_name] = output_q
        self.current_model = model_name

    def stop_current_model(self):
        if self.current_model and self.current_model in self.active_processes:
            print(f"Stopping model: {self.current_model}")
            # Send stop signal
            if self.current_model in self.input_queues:
                self.input_queues[self.current_model].put("STOP")
            
            # Wait for join
            process = self.active_processes[self.current_model]
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
            
            del self.active_processes[self.current_model]
            del self.input_queues[self.current_model]
            del self.output_queues[self.current_model]
            self.current_model = None

    def get_queues(self, model_name: str):
        if model_name != self.current_model:
            return None, None
        return self.input_queues.get(model_name), self.output_queues.get(model_name)

    def _get_worker_class(self, model_name: str):
        # Lazy import to avoid circular deps or early init
        if model_name == "zipformer":
            from app.workers.zipformer import ZipformerWorker
            return ZipformerWorker
        elif model_name in ["faster-whisper", "phowhisper"]:
            from app.workers.whisper import WhisperWorker
            return WhisperWorker
        return None

manager = ModelManager()
