"""
Application Layer - Request DTOs

This module defines Data Transfer Objects for incoming requests.
DTOs serve as the API contract boundary, validating and structuring
data from external sources (HTTP requests, WebSocket messages).

Following Clean Architecture:
- DTOs are part of the Application layer
- They validate input before passing to Use Cases
- They decouple external API format from internal domain models
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class TranscriptionRequest(BaseModel):
    """
    Request for audio transcription.
    
    Used for both WebSocket streaming and HTTP batch transcription.
    
    Attributes:
        model: Model identifier (e.g., "zipformer", "whisper")
        sample_rate: Audio sample rate in Hz (default: 16000)
        enable_moderation: Whether to enable content moderation
        session_id: Optional session identifier for grouping transcriptions
        language: Target language code (default: "vi" for Vietnamese)
    
    Example:
        ```python
        request = TranscriptionRequest(
            model="zipformer",
            sample_rate=16000,
            enable_moderation=True,
            session_id="abc-123",
            language="vi"
        )
        ```
    """
    
    model: str = Field(
        default="zipformer",
        description="Model identifier for transcription"
    )
    sample_rate: int = Field(
        default=16000,
        ge=8000,
        le=48000,
        description="Audio sample rate in Hz"
    )
    enable_moderation: bool = Field(
        default=True,
        description="Enable content moderation for transcribed text"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for grouping related transcriptions"
    )
    language: str = Field(
        default="vi",
        description="Target language code (vi=Vietnamese, en=English)"
    )
    
    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """Validate sample rate is standard."""
        standard_rates = [8000, 16000, 22050, 32000, 44100, 48000]
        if v not in standard_rates:
            raise ValueError(
                f"Sample rate must be one of {standard_rates}, got {v}"
            )
        return v
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language is supported."""
        supported = ["vi", "en"]
        if v not in supported:
            raise ValueError(
                f"Language must be one of {supported}, got {v}"
            )
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "zipformer",
                "sample_rate": 16000,
                "enable_moderation": True,
                "session_id": "session-abc-123",
                "language": "vi"
            }
        }


class HistoryQueryRequest(BaseModel):
    """
    Request for querying transcription history.
    
    Supports pagination, filtering, and searching through
    historical transcription records.
    
    Attributes:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        search: Optional text search query
        model_filter: Filter by specific model
        session_id: Filter by session ID
        start_date: Filter records after this date
        end_date: Filter records before this date
        order_by: Field to order results by
        order_direction: Sort direction (asc/desc)
    
    Example:
        ```python
        query = HistoryQueryRequest(
            skip=0,
            limit=20,
            search="xin chào",
            model_filter="zipformer",
            order_by="created_at",
            order_direction="desc"
        )
        ```
    """
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip for pagination"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of records to return"
    )
    search: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Text search query"
    )
    model_filter: Optional[str] = Field(
        default=None,
        description="Filter by model identifier"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Filter by session ID"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter records created after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter records created before this date"
    )
    order_by: str = Field(
        default="created_at",
        description="Field to order results by"
    )
    order_direction: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort direction"
    )
    
    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, v: str) -> str:
        """Validate order_by field exists."""
        allowed_fields = ["created_at", "confidence", "text", "model_id"]
        if v not in allowed_fields:
            raise ValueError(
                f"order_by must be one of {allowed_fields}, got {v}"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "skip": 0,
                "limit": 20,
                "search": "xin chào",
                "model_filter": "zipformer",
                "order_by": "created_at",
                "order_direction": "desc"
            }
        }


class ModelSwitchRequest(BaseModel):
    """
    Request to switch the active transcription model.
    
    Triggers graceful shutdown of current model and startup
    of the requested model.
    
    Attributes:
        model_id: Target model identifier
        force: Force switch even if current model is busy
    
    Example:
        ```python
        request = ModelSwitchRequest(
            model_id="zipformer-large",
            force=False
        )
        ```
    """
    
    model_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target model identifier"
    )
    force: bool = Field(
        default=False,
        description="Force switch even if model is busy"
    )
    
    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID format."""
        # Basic validation - actual model existence checked in use case
        if not v or v.isspace():
            raise ValueError("model_id cannot be empty or whitespace")
        return v.strip().lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "zipformer",
                "force": False
            }
        }


class ModerationToggleRequest(BaseModel):
    """
    Request to enable or disable content moderation.
    
    Attributes:
        enabled: True to enable moderation, False to disable
    
    Example:
        ```python
        request = ModerationToggleRequest(enabled=True)
        ```
    """
    
    enabled: bool = Field(
        ...,
        description="Enable or disable content moderation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True
            }
        }


class StandaloneModerateRequest(BaseModel):
    """
    Request for standalone text moderation (not tied to transcription).
    
    Used for moderating text that's already been transcribed or
    entered manually.
    
    Attributes:
        text: Text content to moderate
        threshold: Confidence threshold for flagging (0.0-1.0)
    
    Example:
        ```python
        request = StandaloneModerateRequest(
            text="Sample text to check",
            threshold=0.5
        )
        ```
    """
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text content to moderate"
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for flagging content"
    )
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty or whitespace only."""
        if not v or v.isspace():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Xin chào, đây là văn bản cần kiểm duyệt",
                "threshold": 0.5
            }
        }


class WebSocketConfigMessage(BaseModel):
    """
    WebSocket configuration message sent at connection start.
    
    This is the first message sent after WebSocket connection
    to configure the transcription session.
    
    Attributes:
        type: Message type (always "config")
        model: Model identifier to use
        sample_rate: Audio sample rate in Hz
        moderation: Enable moderation for this session
        session_id: Optional session identifier
    
    Example:
        ```python
        config = WebSocketConfigMessage(
            type="config",
            model="zipformer",
            sample_rate=16000,
            moderation=True,
            session_id="ws-session-123"
        )
        ```
    """
    
    type: Literal["config"] = Field(
        default="config",
        description="Message type identifier"
    )
    model: str = Field(
        default="zipformer",
        description="Model identifier"
    )
    sample_rate: int = Field(
        default=16000,
        ge=8000,
        le=48000,
        description="Audio sample rate in Hz"
    )
    moderation: bool = Field(
        default=True,
        description="Enable content moderation"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    
    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """Validate sample rate is standard."""
        standard_rates = [8000, 16000, 22050, 32000, 44100, 48000]
        if v not in standard_rates:
            raise ValueError(
                f"Sample rate must be one of {standard_rates}"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "config",
                "model": "zipformer",
                "sample_rate": 16000,
                "moderation": True,
                "session_id": "ws-session-abc"
            }
        }
