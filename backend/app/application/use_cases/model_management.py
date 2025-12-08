"""
Model Management Use Cases.

This module contains use cases for managing AI models including
model switching and status retrieval.
"""

from typing import Dict
from app.application.interfaces.workers import IWorkerManager
from app.domain.value_objects.model_config import ModelConfig
from app.domain.exceptions import (
    ValidationException,
    BusinessRuleViolationException,
    WorkerException,
)


class SwitchModelUseCase:
    """
    Use case for switching between different AI models.

    This use case handles graceful model transitions, ensuring the old
    model is properly shut down before the new model is started. It validates
    the target model configuration and manages the worker lifecycle.

    Example:
        ```python
        use_case = SwitchModelUseCase(worker_manager=manager)

        new_config = ModelConfig.for_zipformer(
            model_path="/path/to/model",
            model_id="zipformer-vi-30M"
        )

        success = await use_case.execute(model_config=new_config)
        if success:
            print("Model switched successfully!")
        ```
    """

    def __init__(self, worker_manager: IWorkerManager):
        """
        Initialize use case.

        Args:
            worker_manager: Worker manager interface for managing models

        Raises:
            ValidationException: If worker_manager is None
        """
        if worker_manager is None:
            raise ValidationException(
                field="worker_manager", value=None, constraint="must not be None"
            )

        self._worker_manager = worker_manager

    async def execute(self, model_config: ModelConfig) -> bool:
        """
        Switch to a new model configuration.

        This method validates the model configuration, gracefully shuts down
        the current model, and starts the new model. The process includes:
        1. Validate model configuration (exists, supported type)
        2. Stop current worker (if any)
        3. Start new worker with new configuration
        4. Verify new worker is ready

        Args:
            model_config: Configuration for the new model to activate

        Returns:
            bool: True if switch successful, False otherwise

        Raises:
            ValidationException: If model_config is None or invalid
            BusinessRuleViolationException: If model type not supported
            WorkerException: If model switch fails

        Example:
            ```python
            config = ModelConfig.for_zipformer(
                model_path="/models/zipformer/",
                device="cpu"
            )
            success = await use_case.execute(config)
            ```
        """
        # Validate input
        if model_config is None:
            raise ValidationException(
                field="model_config", value=None, constraint="must not be None"
            )

        # Validate model type (must be STT model for transcription)
        if not model_config.is_stt_model():
            raise BusinessRuleViolationException(
                rule="model_type_must_be_stt",
                reason=f"Can only switch STT models, got: {model_config.model_type}",
            )

        try:
            # Delegate to worker manager for actual switching
            await self._worker_manager.switch_model(model_config)

            # Verify new worker is ready
            status = await self._worker_manager.get_model_status()
            if not status.get("model_ready", False):
                raise WorkerException(
                    worker_type="transcription",
                    message="New model failed to start after switch",
                )

            return True

        except Exception as e:
            # Re-raise domain exceptions as-is
            if isinstance(
                e,
                (ValidationException, BusinessRuleViolationException, WorkerException),
            ):
                raise

            # Wrap other exceptions as WorkerException
            raise WorkerException(
                worker_type="transcription", message=f"Model switch failed: {str(e)}"
            ) from e


class GetModelStatusUseCase:
    """
    Use case for retrieving current model status.

    This use case queries the worker manager for the status of all
    active workers and returns information about which models are
    running and their readiness state.

    Example:
        ```python
        use_case = GetModelStatusUseCase(worker_manager=manager)

        status = await use_case.execute()
        print(f"Current model: {status['current_model']}")
        print(f"Model ready: {status['model_ready']}")
        print(f"Moderation enabled: {status['moderation_enabled']}")
        ```
    """

    def __init__(self, worker_manager: IWorkerManager):
        """
        Initialize use case.

        Args:
            worker_manager: Worker manager interface for querying status

        Raises:
            ValidationException: If worker_manager is None
        """
        if worker_manager is None:
            raise ValidationException(
                field="worker_manager", value=None, constraint="must not be None"
            )

        self._worker_manager = worker_manager

    async def execute(self) -> Dict[str, any]:
        """
        Get status of all managed workers.

        Retrieves comprehensive status information including:
        - current_model: ID of active STT model
        - model_ready: Whether STT worker is ready for inference
        - moderation_enabled: Whether content moderation is active
        - moderation_ready: Whether moderation worker is ready

        Returns:
            dict: Status dictionary with fields described above

        Raises:
            WorkerException: If status retrieval fails

        Example:
            ```python
            status = await use_case.execute()

            if status["model_ready"]:
                print(f"Ready to transcribe with {status['current_model']}")
            else:
                print("Model not ready")
            ```
        """
        try:
            status = await self._worker_manager.get_model_status()
            return status

        except Exception as e:
            # Wrap exceptions as WorkerException
            raise WorkerException(
                worker_type="status", message=f"Failed to get model status: {str(e)}"
            ) from e


class ListAvailableModelsUseCase:
    """
    Use case for listing all available models.

    This use case returns information about all models that can be
    loaded, including their paths, types, and supported features.
    Currently returns a static list of models available in the system.

    Future Enhancement: Could integrate with model repository to
    dynamically discover models from filesystem or registry.

    Example:
        ```python
        use_case = ListAvailableModelsUseCase()

        models = await use_case.execute()
        for model in models:
            print(f"{model['model_id']}: {model['model_type']}")
        ```
    """

    # Hardcoded model configurations for now
    # TODO: Move to configuration file or database
    AVAILABLE_MODELS = [
        {
            "model_id": "zipformer-vi-30M",
            "model_type": "stt",
            "name": "Zipformer Vietnamese 30M",
            "description": "Vietnamese speech-to-text model (30M parameters, 6000h training data)",
            "language": "vi",
            "default_path": "models_storage/zipformer/hynt-zipformer-30M-6000h/",
            "parameters": {
                "sample_rate": 16000,
                "num_threads": 4,
                "decoding_method": "greedy_search",
            },
        },
        {
            "model_id": "visobert-hsd-span",
            "model_type": "moderation",
            "name": "ViSoBERT Hate Speech Detection",
            "description": "Vietnamese hate speech detection with span extraction",
            "language": "vi",
            "default_path": "models_storage/visobert-hsd-span/onnx/",
            "parameters": {"max_length": 256, "threshold": 0.5, "detect_spans": True},
        },
    ]

    async def execute(self) -> list:
        """
        List all available models.

        Returns a list of model configurations that can be loaded.
        Each model entry contains:
        - model_id: Unique model identifier
        - model_type: Type ('stt' or 'moderation')
        - name: Human-readable name
        - description: Model description
        - language: Target language
        - default_path: Default filesystem path
        - parameters: Default parameters

        Returns:
            list: List of available model dictionaries

        Example:
            ```python
            models = await use_case.execute()

            stt_models = [m for m in models if m['model_type'] == 'stt']
            print(f"Found {len(stt_models)} STT models")
            ```
        """
        # Return copy to prevent mutation
        return [dict(model) for model in self.AVAILABLE_MODELS]
