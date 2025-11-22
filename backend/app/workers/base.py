import multiprocessing
from abc import ABC, abstractmethod
from typing import Any

class BaseWorker(ABC):
    def __init__(self, input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue, model_path: str):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.model_path = model_path
        self.is_running = True

    @abstractmethod
    def load_model(self):
        """Load the AI model into memory."""
        pass

    @abstractmethod
    def process(self, audio_data: bytes):
        """Process audio data and put result in output_queue."""
        pass

    def run(self):
        """Main loop for the worker process."""
        print(f"Worker {self.__class__.__name__} starting...")
        try:
            self.load_model()
            print(f"Worker {self.__class__.__name__} model loaded.")
            
            while self.is_running:
                try:
                    # Get data from input queue with timeout to allow checking is_running
                    item = self.input_queue.get(timeout=1.0)
                    
                    if item == "STOP":
                        self.is_running = False
                        break
                        
                    self.process(item)
                    
                except multiprocessing.queues.Empty:
                    continue
                except Exception as e:
                    print(f"Error in worker {self.__class__.__name__}: {e}")
                    # Send error to output queue if needed
                    self.output_queue.put({"error": str(e)})
                    
        except Exception as e:
            print(f"Fatal error in worker {self.__class__.__name__}: {e}")
        finally:
            print(f"Worker {self.__class__.__name__} stopped.")
