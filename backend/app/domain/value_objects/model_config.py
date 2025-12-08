"""Model configuration value object."""

from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    """
    Immutable value object representing model configuration.

    Encapsulates all configuration needed to initialize and run
    an AI model (STT or moderation).

    Attributes:
        model_id: Unique model identifier
        model_type: Type of model ('stt' or 'moderation')
        model_path: Path to model files
        language: Target language (e.g., 'vi' for Vietnamese)
        device: Computation device ('cpu' or 'cuda')
        parameters: Additional model-specific parameters
    """

    model_id: str
    model_type: str
    model_path: str
    language: str = "vi"
    device: str = "cpu"
    parameters: Dict[str, Any] = None

    # Valid model types
    MODEL_TYPE_STT = "stt"
    MODEL_TYPE_MODERATION = "moderation"
    VALID_MODEL_TYPES = {MODEL_TYPE_STT, MODEL_TYPE_MODERATION}

    # Valid devices
    DEVICE_CPU = "cpu"
    DEVICE_CUDA = "cuda"
    VALID_DEVICES = {DEVICE_CPU, DEVICE_CUDA}

    # Supported languages
    SUPPORTED_LANGUAGES = {"vi", "en"}

    def __post_init__(self) -> None:
        """Validate model configuration after initialization."""
        # Set default parameters if None
        if self.parameters is None:
            object.__setattr__(self, "parameters", {})

        # Validate model_type
        if self.model_type not in self.VALID_MODEL_TYPES:
            raise ValueError(
                f"Invalid model_type: {self.model_type}. "
                f"Must be one of {self.VALID_MODEL_TYPES}"
            )

        # Validate device
        if self.device not in self.VALID_DEVICES:
            raise ValueError(
                f"Invalid device: {self.device}. "
                f"Must be one of {self.VALID_DEVICES}"
            )

        # Validate language
        if self.language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {self.language}. "
                f"Must be one of {self.SUPPORTED_LANGUAGES}"
            )

        # Validate model_path exists
        if not Path(self.model_path).exists():
            raise ValueError(f"Model path does not exist: {self.model_path}")

    def is_stt_model(self) -> bool:
        """Check if this is an STT model configuration."""
        return self.model_type == self.MODEL_TYPE_STT

    def is_moderation_model(self) -> bool:
        """Check if this is a moderation model configuration."""
        return self.model_type == self.MODEL_TYPE_MODERATION

    def uses_gpu(self) -> bool:
        """Check if model uses GPU acceleration."""
        return self.device == self.DEVICE_CUDA

    def is_vietnamese(self) -> bool:
        """Check if model targets Vietnamese language."""
        return self.language == "vi"

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get a model-specific parameter.

        Args:
            key: Parameter key
            default: Default value if key not found

        Returns:
            Parameter value or default.
        """
        return self.parameters.get(key, default)

    def has_parameter(self, key: str) -> bool:
        """
        Check if a parameter exists.

        Args:
            key: Parameter key

        Returns:
            True if parameter exists, False otherwise.
        """
        return key in self.parameters

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all configuration fields.
        """
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "model_path": self.model_path,
            "language": self.language,
            "device": self.device,
            "parameters": dict(self.parameters),
            "is_stt": self.is_stt_model(),
            "is_moderation": self.is_moderation_model(),
            "uses_gpu": self.uses_gpu(),
        }

    @classmethod
    def for_zipformer(
        cls,
        model_path: str,
        model_id: str = "zipformer-vi-30M",
        device: str = "cpu",
        **kwargs: Any,
    ) -> "ModelConfig":
        """
        Factory method for Zipformer STT model.

        Args:
            model_path: Path to Zipformer model files
            model_id: Model identifier
            device: Computation device
            **kwargs: Additional parameters

        Returns:
            ModelConfig for Zipformer.
        """
        default_params = {
            "sample_rate": 16000,
            "num_threads": 4,
            "decoding_method": "greedy_search",
        }
        default_params.update(kwargs)

        return cls(
            model_id=model_id,
            model_type=cls.MODEL_TYPE_STT,
            model_path=model_path,
            language="vi",
            device=device,
            parameters=default_params,
        )

    @classmethod
    def for_visobert_hsd(
        cls,
        model_path: str,
        model_id: str = "visobert-hsd-span",
        device: str = "cpu",
        **kwargs: Any,
    ) -> "ModelConfig":
        """
        Factory method for ViSoBERT-HSD moderation model.

        Args:
            model_path: Path to ViSoBERT model files
            model_id: Model identifier
            device: Computation device
            **kwargs: Additional parameters

        Returns:
            ModelConfig for ViSoBERT-HSD.
        """
        default_params = {
            "max_length": 256,
            "threshold": 0.5,
            "detect_spans": True,
        }
        default_params.update(kwargs)

        return cls(
            model_id=model_id,
            model_type=cls.MODEL_TYPE_MODERATION,
            model_path=model_path,
            language="vi",
            device=device,
            parameters=default_params,
        )
