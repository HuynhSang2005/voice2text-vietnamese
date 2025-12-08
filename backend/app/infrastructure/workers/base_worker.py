"""
Infrastructure Layer - Base Worker Implementation

Async wrapper around multiprocessing-based AI model workers.
Provides Protocol-compliant interface while maintaining multiprocessing
for CPU-bound ML inference.
"""

import asyncio
import logging
import multiprocessing
from abc import ABC, abstractmethod
from typing import Any, Optional
from multiprocessing import Queue, Process, Event


class BaseWorker(ABC):
    """
    Abstract base class for AI model workers using multiprocessing.

    Workers run ML models in separate processes to avoid GIL contention.
    This class provides the infrastructure for process management and
    queue-based communication.

    Subclasses must implement:
        - load_model(): Load ML model into memory
        - process(): Process input data and produce results
    """

    def __init__(
        self,
        model_name: str,
        queue_timeout: float = 1.0,
        stop_timeout: float = 5.0,
    ):
        """
        Initialize worker with multiprocessing infrastructure.

        Args:
            model_name: Name of the model for logging
            queue_timeout: Timeout for queue.get() operations (seconds)
            stop_timeout: Timeout for graceful shutdown (seconds)
        """
        self.model_name = model_name
        self.queue_timeout = queue_timeout
        self.stop_timeout = stop_timeout

        # Multiprocessing components
        self.input_queue: Optional[Queue] = None
        self.output_queue: Optional[Queue] = None
        self.stop_event: Optional[Event] = None
        self.process: Optional[Process] = None

        # State tracking
        self._is_running = False
        self._is_ready = False

        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load_model(self) -> None:
        """
        Load the AI model into memory.

        This method runs in the worker process and should initialize
        the ML model. Must be implemented by subclasses.

        Raises:
            Exception: If model fails to load
        """
        pass

    @abstractmethod
    def process(self, item: Any) -> None:
        """
        Process input data and put result in output_queue.

        This method runs in the worker process and handles the actual
        ML inference. Must be implemented by subclasses.

        Args:
            item: Input data to process
        """
        pass

    def _worker_loop(self) -> None:
        """
        Main loop for the worker process.

        Loads the model, then continuously processes items from the
        input queue until a stop signal is received.
        """
        self.logger.info(f"{self.model_name} worker starting...")

        try:
            # Load model in worker process
            self.load_model()
            self.logger.info(f"{self.model_name} model loaded successfully")

            # Process items until stop signal
            while not self.stop_event.is_set():
                try:
                    # Get item with timeout to check stop_event periodically
                    item = self.input_queue.get(timeout=self.queue_timeout)

                    # Check for stop signal
                    if item == "STOP":
                        self.logger.info("Received STOP signal")
                        break

                    # Process item
                    self.process(item)

                except multiprocessing.queues.Empty:
                    # Timeout - check stop_event and continue
                    continue

                except Exception as e:
                    self.logger.error(f"Error processing item: {e}", exc_info=True)
                    # Send error to output queue
                    try:
                        self.output_queue.put(
                            {"error": str(e), "model": self.model_name},
                            timeout=self.queue_timeout,
                        )
                    except:
                        pass  # Queue full or other error

        except Exception as e:
            self.logger.error(f"Fatal error in worker: {e}", exc_info=True)

        finally:
            self.logger.info(f"{self.model_name} worker stopped")

    async def start(self) -> None:
        """
        Start the worker process and initialize queues.

        Creates multiprocessing queues and spawns the worker process.
        Waits briefly to ensure the process starts successfully.

        Raises:
            RuntimeError: If worker is already running
            Exception: If worker process fails to start
        """
        if self._is_running:
            raise RuntimeError(f"{self.model_name} worker already running")

        self.logger.info(f"Starting {self.model_name} worker...")

        # Create multiprocessing components
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.stop_event = Event()

        # Start worker process
        self.process = Process(
            target=self._worker_loop, name=f"{self.model_name}_worker"
        )
        self.process.start()

        # Wait for process to start
        await asyncio.sleep(0.1)

        if not self.process.is_alive():
            raise RuntimeError(f"{self.model_name} worker failed to start")

        self._is_running = True
        self._is_ready = True

        self.logger.info(f"{self.model_name} worker started (PID: {self.process.pid})")

    async def stop(self) -> None:
        """
        Stop the worker process and cleanup resources.

        Sends stop signal, waits for graceful shutdown, then forcefully
        terminates if needed. Cleans up queues and resets state.

        Raises:
            TimeoutError: If worker doesn't stop within timeout
        """
        if not self._is_running:
            self.logger.warning(f"{self.model_name} worker not running")
            return

        self.logger.info(f"Stopping {self.model_name} worker...")

        try:
            # Send stop signal
            self.stop_event.set()

            try:
                self.input_queue.put("STOP", timeout=1.0)
            except:
                pass  # Queue full or closed

            # Wait for graceful shutdown
            await asyncio.to_thread(self.process.join, timeout=self.stop_timeout)

            # Force terminate if still alive
            if self.process.is_alive():
                self.logger.warning(
                    f"{self.model_name} worker did not stop gracefully, "
                    "terminating..."
                )
                self.process.terminate()
                await asyncio.sleep(0.5)

                if self.process.is_alive():
                    self.logger.error(
                        f"{self.model_name} worker still alive, killing..."
                    )
                    self.process.kill()

            # Drain queues to prevent deadlock
            await self._drain_queue(self.input_queue)
            await self._drain_queue(self.output_queue)

            # Close queues
            self.input_queue.close()
            self.output_queue.close()

            self.input_queue.join_thread()
            self.output_queue.join_thread()

        except Exception as e:
            self.logger.error(f"Error stopping worker: {e}", exc_info=True)

        finally:
            self._is_running = False
            self._is_ready = False
            self.process = None
            self.input_queue = None
            self.output_queue = None
            self.stop_event = None

            self.logger.info(f"{self.model_name} worker stopped and cleaned up")

    async def _drain_queue(self, queue: Queue, timeout: float = 2.0) -> None:
        """
        Drain remaining items from queue with timeout.

        Prevents deadlock by emptying queues before closing them.
        Uses timeout to avoid hanging on full/broken queues.

        Args:
            queue: Queue to drain
            timeout: Maximum time to spend draining (seconds)
        """
        if queue is None:
            return

        drained_count = 0
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    self.logger.warning(
                        f"Queue drain timeout after {drained_count} items"
                    )
                    break

                # Try to get item
                try:
                    await asyncio.to_thread(queue.get, timeout=0.1)
                    drained_count += 1
                except multiprocessing.queues.Empty:
                    break  # Queue empty
                except:
                    break  # Queue closed or error

        except Exception as e:
            self.logger.error(f"Error draining queue: {e}")

        if drained_count > 0:
            self.logger.debug(f"Drained {drained_count} items from queue")

    async def is_ready(self) -> bool:
        """
        Check if worker is ready to process requests.

        Returns:
            True if worker process is running and model is loaded
        """
        return self._is_ready and self._is_running and self.process.is_alive()

    async def put_input(self, item: Any, timeout: float = 5.0) -> None:
        """
        Put item in input queue (async wrapper).

        Args:
            item: Data to send to worker
            timeout: Queue put timeout (seconds)

        Raises:
            RuntimeError: If worker not ready
            TimeoutError: If queue put times out
        """
        if not await self.is_ready():
            raise RuntimeError(f"{self.model_name} worker not ready")

        try:
            await asyncio.to_thread(self.input_queue.put, item, timeout=timeout)
        except multiprocessing.queues.Full:
            raise TimeoutError(f"Input queue full after {timeout}s")

    async def get_output(self, timeout: float = 5.0) -> Any:
        """
        Get item from output queue (async wrapper).

        Args:
            timeout: Queue get timeout (seconds)

        Returns:
            Item from output queue

        Raises:
            RuntimeError: If worker not ready
            TimeoutError: If no output within timeout
        """
        if not await self.is_ready():
            raise RuntimeError(f"{self.model_name} worker not ready")

        try:
            return await asyncio.to_thread(self.output_queue.get, timeout=timeout)
        except multiprocessing.queues.Empty:
            raise TimeoutError(f"No output after {timeout}s")
