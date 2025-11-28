from typing import Optional
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Information about an available STT model."""
    id: str
    name: str
    description: str


class ModelStatus(BaseModel):
    """Current status of the model system."""
    current_model: Optional[str] = None
    is_loaded: bool
    status: str  # "ready" | "idle" | "loading"


class SwitchModelResponse(BaseModel):
    """Response for model switch operation."""
    status: str
    current_model: str


class TranscriptionResult(BaseModel):
    """Real-time transcription result sent via WebSocket."""
    text: str
    is_final: bool
    model: str


class WebSocketConfig(BaseModel):
    """Configuration message for WebSocket connection."""
    type: str = "config"
    model: str = "zipformer"
    sample_rate: int = 16000
