"""
Infrastructure Layer - Worker Manager

Orchestrates multiple ML model workers (STT and moderation).
Implements IWorkerManager protocol with async interface.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from app.application.interfaces.workers import (
    ITranscriptionWorker,
    IModerationWorker,
    IWorkerManager,
)
from app.domain.value_objects.model_config import ModelConfig
from app.infrastructure.workers.zipformer_worker import ZipformerWorker
from app.infrastructure.workers.span_detector_worker import SpanDetectorWorker


logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Multiprocessing worker manager.
    
    Manages lifecycle of STT and moderation workers using multiprocessing.
    Implements IWorkerManager protocol for Clean Architecture compliance.
    
    Features:
        - Dynamic model switching (graceful restart)
        - Optional moderation enable/disable
        - Worker health monitoring
        - Automatic cleanup on shutdown
    """

    def __init__(
        self,
        initial_model_config: Optional[ModelConfig] = None,
        enable_moderation: bool = True,
    ):
        """
        Initialize worker manager.
        
        Args:
            initial_model_config: Optional initial STT model config
            enable_moderation: Whether to enable moderation worker
        """
        self._stt_worker: Optional[ITranscriptionWorker] = None
        self._moderation_worker: Optional[IModerationWorker] = None
        self._current_model_config: Optional[ModelConfig] = initial_model_config
        self._moderation_enabled: bool = enable_moderation
        self._is_started: bool = False
        self._lock = asyncio.Lock()
        
        logger.info(
            f"WorkerManager initialized "
            f"(moderation={'enabled' if enable_moderation else 'disabled'})"
        )

    async def start_all(self) -> None:
        """
        Start all configured workers.
        
        Starts STT worker if model config provided, and moderation worker
        if enabled. This method is idempotent - calling multiple times
        has no effect.
        
        Raises:
            RuntimeError: If worker fails to start
            Exception: If model loading fails
        """
        if self._is_started:
            logger.warning("Workers already started")
            return
        
        async with self._lock:
            logger.info("Starting workers...")
            
            try:
                # Start STT worker if configured
                if self._current_model_config:
                    await self._start_stt_worker(self._current_model_config)
                else:
                    logger.warning("No STT model config provided, skipping STT worker")
                
                # Start moderation worker if enabled
                if self._moderation_enabled:
                    await self._start_moderation_worker()
                else:
                    logger.info("Moderation disabled, skipping moderation worker")
                
                self._is_started = True
                logger.info("All workers started successfully")
                
            except Exception as e:
                logger.error(f"Failed to start workers: {e}", exc_info=True)
                # Cleanup partially started workers
                await self._cleanup_workers()
                raise RuntimeError(f"Worker startup failed: {e}")

    async def stop_all(self) -> None:
        """
        Stop all workers and cleanup resources.
        
        Gracefully shuts down all worker processes and releases resources.
        Call this during application shutdown.
        
        This method is idempotent and safe to call multiple times.
        """
        if not self._is_started:
            logger.warning("Workers not started")
            return
        
        async with self._lock:
            logger.info("Stopping all workers...")
            await self._cleanup_workers()
            self._is_started = False
            logger.info("All workers stopped")

    async def get_transcription_worker(self) -> Optional[ITranscriptionWorker]:
        """
        Get the active transcription worker.
        
        Returns:
            The currently active STT worker, or None if not started
            or not ready
        
        Example:
            ```python
            worker = await manager.get_transcription_worker()
            if worker:
                async for result in worker.process_audio_stream(audio):
                    print(result.content)
            ```
        """
        if self._stt_worker and await self._stt_worker.is_ready():
            return self._stt_worker
        return None

    async def get_moderation_worker(self) -> Optional[IModerationWorker]:
        """
        Get the active moderation worker.
        
        Returns:
            The currently active moderation worker, or None if
            moderation is disabled or worker not ready
        
        Example:
            ```python
            worker = await manager.get_moderation_worker()
            if worker:
                result = await worker.moderate(text)
                print(f"Label: {result.label}")
            ```
        """
        if self._moderation_enabled and self._moderation_worker:
            if await self._moderation_worker.is_ready():
                return self._moderation_worker
        return None

    async def switch_model(self, model_config: ModelConfig) -> None:
        """
        Switch to a different STT model.
        
        Gracefully stops the current STT worker (if any) and starts
        a new worker with the specified model configuration.
        
        Args:
            model_config: Configuration for new STT model
        
        Raises:
            ValueError: If model_config is invalid
            RuntimeError: If model switch fails
        
        Example:
            ```python
            new_config = ModelConfig.for_zipformer(
                model_id="zipformer-large",
                model_path="/path/to/model"
            )
            await manager.switch_model(new_config)
            ```
        """
        if not model_config.is_stt_model():
            raise ValueError(
                f"Invalid model type: {model_config.model_type} "
                "(expected STT model)"
            )
        
        async with self._lock:
            logger.info(f"Switching to model: {model_config.model_id}")
            
            try:
                # Stop current STT worker
                if self._stt_worker:
                    logger.info("Stopping current STT worker...")
                    await self._stt_worker.stop()
                    self._stt_worker = None
                
                # Start new worker
                await self._start_stt_worker(model_config)
                self._current_model_config = model_config
                
                logger.info(f"Model switched to: {model_config.model_id}")
                
            except Exception as e:
                logger.error(f"Model switch failed: {e}", exc_info=True)
                raise RuntimeError(f"Failed to switch model: {e}")

    async def enable_moderation(self, enabled: bool) -> None:
        """
        Enable or disable content moderation.
        
        If enabling, starts the moderation worker.
        If disabling, stops the moderation worker.
        
        Args:
            enabled: True to enable moderation, False to disable
        
        Example:
            ```python
            # Enable moderation
            await manager.enable_moderation(True)
            
            # Disable moderation
            await manager.enable_moderation(False)
            ```
        """
        async with self._lock:
            if enabled == self._moderation_enabled:
                logger.info(f"Moderation already {'enabled' if enabled else 'disabled'}")
                return
            
            self._moderation_enabled = enabled
            
            if enabled:
                logger.info("Enabling moderation...")
                await self._start_moderation_worker()
            else:
                logger.info("Disabling moderation...")
                if self._moderation_worker:
                    await self._moderation_worker.stop()
                    self._moderation_worker = None

    async def get_model_status(self) -> Dict[str, Any]:
        """
        Get status of all managed workers.
        
        Returns:
            Dictionary with status information:
                - current_model: Name of active STT model (or None)
                - model_ready: Whether STT worker is ready
                - moderation_enabled: Whether moderation is enabled
                - moderation_ready: Whether moderation worker is ready
                - is_started: Whether manager has been started
        
        Example:
            ```python
            status = await manager.get_model_status()
            print(f"STT Model: {status['current_model']}")
            print(f"Ready: {status['model_ready']}")
            print(f"Moderation: {status['moderation_enabled']}")
            ```
        """
        stt_ready = False
        if self._stt_worker:
            try:
                stt_ready = await self._stt_worker.is_ready()
            except:
                pass
        
        moderation_ready = False
        if self._moderation_worker:
            try:
                moderation_ready = await self._moderation_worker.is_ready()
            except:
                pass
        
        return {
            "current_model": (
                self._current_model_config.model_id
                if self._current_model_config
                else None
            ),
            "model_ready": stt_ready,
            "moderation_enabled": self._moderation_enabled,
            "moderation_ready": moderation_ready,
            "is_started": self._is_started,
        }

    async def health_check(self) -> bool:
        """
        Check health of all active workers.
        
        Returns:
            True if all active workers are healthy, False otherwise
        
        Example:
            ```python
            if not await manager.health_check():
                logger.error("Worker health check failed!")
                await manager.restart_workers()
            ```
        """
        try:
            # Check STT worker
            if self._stt_worker:
                if not await self._stt_worker.is_ready():
                    logger.warning("STT worker not healthy")
                    return False
            
            # Check moderation worker
            if self._moderation_enabled and self._moderation_worker:
                if not await self._moderation_worker.is_ready():
                    logger.warning("Moderation worker not healthy")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            return False

    async def _start_stt_worker(self, model_config: ModelConfig) -> None:
        """
        Start STT worker with given configuration.
        
        Args:
            model_config: Model configuration
        
        Raises:
            ValueError: If unsupported model type
            RuntimeError: If worker fails to start
        """
        model_id = model_config.model_id.lower()
        
        # Determine worker type from model_id
        if "zipformer" in model_id:
            logger.info(f"Starting Zipformer worker: {model_id}")
            worker = ZipformerWorker(
                model_name=model_id,
                queue_timeout=1.0,
                stop_timeout=5.0,
            )
        else:
            raise ValueError(f"Unsupported STT model: {model_id}")
        
        # Start worker
        await worker.start()
        self._stt_worker = worker
        
        logger.info(f"STT worker started: {model_id}")

    async def _start_moderation_worker(self) -> None:
        """
        Start moderation worker.
        
        Raises:
            RuntimeError: If worker fails to start
        """
        logger.info("Starting span detector moderation worker...")
        
        worker = SpanDetectorWorker(
            model_name="visobert-hsd-span",
            queue_timeout=1.0,
            stop_timeout=5.0,
        )
        
        await worker.start()
        self._moderation_worker = worker
        
        logger.info("Moderation worker started")

    async def _cleanup_workers(self) -> None:
        """
        Stop and cleanup all workers.
        
        Gracefully shuts down all worker processes.
        Safe to call even if workers not started.
        """
        # Stop STT worker
        if self._stt_worker:
            try:
                logger.info("Stopping STT worker...")
                await self._stt_worker.stop()
            except Exception as e:
                logger.error(f"Error stopping STT worker: {e}", exc_info=True)
            finally:
                self._stt_worker = None
        
        # Stop moderation worker
        if self._moderation_worker:
            try:
                logger.info("Stopping moderation worker...")
                await self._moderation_worker.stop()
            except Exception as e:
                logger.error(f"Error stopping moderation worker: {e}", exc_info=True)
            finally:
                self._moderation_worker = None
        
        logger.debug("Worker cleanup complete")

    async def restart_workers(self) -> None:
        """
        Restart all workers.
        
        Useful for recovering from worker failures or applying
        configuration changes.
        
        Raises:
            RuntimeError: If restart fails
        """
        logger.info("Restarting workers...")
        
        async with self._lock:
            # Save current config
            model_config = self._current_model_config
            moderation_enabled = self._moderation_enabled
            
            # Stop all
            await self._cleanup_workers()
            self._is_started = False
            
            # Restore config and restart
            self._current_model_config = model_config
            self._moderation_enabled = moderation_enabled
            
            await self.start_all()
        
        logger.info("Workers restarted successfully")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"WorkerManager("
            f"model={self._current_model_config.model_id if self._current_model_config else None}, "
            f"moderation={'on' if self._moderation_enabled else 'off'}, "
            f"started={self._is_started})"
        )
