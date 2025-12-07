"""
Application Layer - Response DTOs

This module defines Data Transfer Objects for outgoing responses.
DTOs serve as the API contract boundary, structuring internal
domain data for external consumption.

Following Clean Architecture:
- DTOs convert domain entities to API-friendly formats
- They include helper methods like from_entity()
- They decouple internal domain structure from API contract
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime

from app.domain.entities.transcription import Transcription
from app.domain.entities.moderation_result import ModerationResult as ModerationResultEntity
from app.domain.entities.session import Session


class TranscriptionResponse(BaseModel):
    """
    Response containing transcription result.
    
    Used for both WebSocket streaming and HTTP batch responses.
    
    Attributes:
        id: Unique identifier for the transcription record
        text: Transcribed text content
        confidence: Confidence score (0.0-1.0)
        is_final: Whether this is a final result or intermediate
        model: Model identifier used for transcription
        workflow_type: "streaming" or "buffered"
        latency_ms: Processing latency in milliseconds
        session_id: Session identifier if applicable
        created_at: Timestamp when transcription was created
        content_moderation: Moderation result if enabled
    
    Example:
        ```python
        response = TranscriptionResponse(
            id=1,
            text="Xin chào",
            confidence=0.95,
            is_final=True,
            model="zipformer",
            workflow_type="streaming",
            latency_ms=250.5,
            created_at=datetime.utcnow()
        )
        ```
    """
    
    id: Optional[int] = Field(
        default=None,
        description="Unique identifier (None for streaming intermediate results)"
    )
    text: str = Field(
        ...,
        description="Transcribed text content"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    is_final: bool = Field(
        ...,
        description="Whether this is a final result"
    )
    model: str = Field(
        ...,
        description="Model identifier used"
    )
    workflow_type: Literal["streaming", "buffered"] = Field(
        default="streaming",
        description="Processing workflow type"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Processing latency in milliseconds"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    content_moderation: Optional["ContentModerationResponse"] = Field(
        default=None,
        description="Moderation result if enabled"
    )
    
    @classmethod
    def from_entity(
        cls,
        entity: Transcription,
        include_moderation: bool = False
    ) -> "TranscriptionResponse":
        """
        Create response DTO from domain entity.
        
        Args:
            entity: Transcription domain entity
            include_moderation: Whether to include moderation data
        
        Returns:
            TranscriptionResponse: DTO ready for API response
        
        Example:
            ```python
            entity = Transcription(text="Hello", confidence=0.95, ...)
            response = TranscriptionResponse.from_entity(entity)
            ```
        """
        moderation_response = None
        if include_moderation and entity.moderation_label:
            moderation_response = ContentModerationResponse(
                label=entity.moderation_label,
                confidence=entity.moderation_confidence or 0.0,
                is_flagged=(entity.moderation_label != "CLEAN")
            )
        
        return cls(
            id=entity.id,
            text=entity.text,
            confidence=entity.confidence.value,
            is_final=entity.is_final,
            model=entity.model_id,
            workflow_type=entity.workflow_type,
            latency_ms=entity.latency_ms,
            session_id=entity.session_id,
            created_at=entity.created_at,
            content_moderation=moderation_response
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "text": "Xin chào, tôi là trợ lý AI",
                "confidence": 0.95,
                "is_final": True,
                "model": "zipformer",
                "workflow_type": "streaming",
                "latency_ms": 245.5,
                "session_id": "session-abc-123",
                "created_at": "2025-12-07T10:30:00Z",
                "content_moderation": {
                    "label": "CLEAN",
                    "confidence": 0.98,
                    "is_flagged": False
                }
            }
        }


class ContentModerationResponse(BaseModel):
    """
    Content moderation result embedded in transcription response.
    
    Attributes:
        label: Classification label (CLEAN, OFFENSIVE, HATE)
        confidence: Confidence score (0.0-1.0)
        is_flagged: Whether content was flagged
        detected_keywords: List of detected offensive keywords
    
    Example:
        ```python
        moderation = ContentModerationResponse(
            label="CLEAN",
            confidence=0.98,
            is_flagged=False,
            detected_keywords=[]
        )
        ```
    """
    
    label: Literal["CLEAN", "OFFENSIVE", "HATE"] = Field(
        ...,
        description="Classification label"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    is_flagged: bool = Field(
        ...,
        description="Whether content is flagged"
    )
    detected_keywords: List[str] = Field(
        default_factory=list,
        description="Detected offensive keywords"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "label": "CLEAN",
                "confidence": 0.98,
                "is_flagged": False,
                "detected_keywords": []
            }
        }


class ModerationResponse(BaseModel):
    """
    Full moderation response for standalone moderation requests.
    
    Attributes:
        type: Response type ("moderation")
        label: Classification label
        label_id: Numeric label ID (0=CLEAN, 1=OFFENSIVE, 2=HATE)
        confidence: Confidence score
        is_flagged: Whether content is flagged
        latency_ms: Processing latency
        detected_keywords: Detected offensive keywords
        request_id: Optional request identifier
    
    Example:
        ```python
        response = ModerationResponse(
            type="moderation",
            label="CLEAN",
            label_id=0,
            confidence=0.98,
            is_flagged=False,
            latency_ms=15.5,
            detected_keywords=[]
        )
        ```
    """
    
    type: Literal["moderation"] = Field(
        default="moderation",
        description="Response type identifier"
    )
    label: Literal["CLEAN", "OFFENSIVE", "HATE"] = Field(
        ...,
        description="Classification label"
    )
    label_id: int = Field(
        ...,
        ge=0,
        le=2,
        description="Numeric label (0=CLEAN, 1=OFFENSIVE, 2=HATE)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    is_flagged: bool = Field(
        ...,
        description="Whether content is flagged"
    )
    latency_ms: float = Field(
        ...,
        ge=0,
        description="Processing latency in milliseconds"
    )
    detected_keywords: List[str] = Field(
        default_factory=list,
        description="Detected offensive keywords"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier"
    )
    
    @classmethod
    def from_entity(
        cls,
        entity: ModerationResultEntity,
        latency_ms: float = 0.0,
        request_id: Optional[str] = None
    ) -> "ModerationResponse":
        """
        Create response from domain entity.
        
        Args:
            entity: ModerationResult domain entity
            latency_ms: Processing latency
            request_id: Optional request identifier
        
        Returns:
            ModerationResponse: DTO ready for API response
        """
        return cls(
            label=entity.label,
            label_id=entity.label_id,
            confidence=entity.confidence.value,
            is_flagged=entity.is_flagged,
            latency_ms=latency_ms,
            detected_keywords=entity.detected_spans or [],
            request_id=request_id
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "moderation",
                "label": "OFFENSIVE",
                "label_id": 1,
                "confidence": 0.87,
                "is_flagged": True,
                "latency_ms": 15.5,
                "detected_keywords": ["badword1", "badword2"],
                "request_id": "req-123"
            }
        }


class HistoryResponse(BaseModel):
    """
    Paginated history response.
    
    Contains list of transcriptions with pagination metadata.
    
    Attributes:
        items: List of transcription responses
        total: Total number of items matching query
        skip: Number of items skipped
        limit: Maximum items per page
        has_more: Whether more pages are available
    
    Example:
        ```python
        response = HistoryResponse(
            items=[...],
            total=150,
            skip=0,
            limit=20,
            has_more=True
        )
        ```
    """
    
    items: List[TranscriptionResponse] = Field(
        ...,
        description="List of transcriptions"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items"
    )
    skip: int = Field(
        ...,
        ge=0,
        description="Number of items skipped"
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum items per page"
    )
    has_more: bool = Field(
        ...,
        description="Whether more pages available"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 123,
                        "text": "Xin chào",
                        "confidence": 0.95,
                        "is_final": True,
                        "model": "zipformer",
                        "workflow_type": "streaming",
                        "created_at": "2025-12-07T10:30:00Z"
                    }
                ],
                "total": 150,
                "skip": 0,
                "limit": 20,
                "has_more": True
            }
        }


class ModelStatusResponse(BaseModel):
    """
    Current status of the model system.
    
    Attributes:
        current_model: Current active model identifier
        is_loaded: Whether model is loaded and ready
        status: Status string ("ready", "loading", "idle", "error")
        moderation_enabled: Whether moderation is enabled
        moderation_ready: Whether moderation worker is ready
    
    Example:
        ```python
        status = ModelStatusResponse(
            current_model="zipformer",
            is_loaded=True,
            status="ready",
            moderation_enabled=True,
            moderation_ready=True
        )
        ```
    """
    
    current_model: Optional[str] = Field(
        default=None,
        description="Current active model"
    )
    is_loaded: bool = Field(
        ...,
        description="Whether model is loaded"
    )
    status: Literal["ready", "loading", "idle", "error"] = Field(
        ...,
        description="Model status"
    )
    moderation_enabled: bool = Field(
        default=False,
        description="Whether moderation is enabled"
    )
    moderation_ready: bool = Field(
        default=False,
        description="Whether moderation worker is ready"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_model": "zipformer",
                "is_loaded": True,
                "status": "ready",
                "moderation_enabled": True,
                "moderation_ready": True
            }
        }


class ModelSwitchResponse(BaseModel):
    """
    Response after model switch operation.
    
    Attributes:
        success: Whether switch was successful
        message: Status message
        previous_model: Previous model identifier
        new_model: New model identifier
    
    Example:
        ```python
        response = ModelSwitchResponse(
            success=True,
            message="Model switched successfully",
            previous_model="zipformer-small",
            new_model="zipformer-large"
        )
        ```
    """
    
    success: bool = Field(
        ...,
        description="Whether switch was successful"
    )
    message: str = Field(
        ...,
        description="Status message"
    )
    previous_model: Optional[str] = Field(
        default=None,
        description="Previous model identifier"
    )
    new_model: str = Field(
        ...,
        description="New model identifier"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Model switched successfully",
                "previous_model": "zipformer-small",
                "new_model": "zipformer-large"
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Health check response.
    
    Attributes:
        status: Overall status ("healthy", "degraded", "unhealthy")
        version: API version
        timestamp: Current server timestamp
        components: Status of individual components
    
    Example:
        ```python
        health = HealthCheckResponse(
            status="healthy",
            version="2.0.0",
            timestamp=datetime.utcnow(),
            components={
                "database": "healthy",
                "workers": "healthy",
                "cache": "healthy"
            }
        )
        ```
    """
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall system status"
    )
    version: str = Field(
        ...,
        description="API version"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Current server timestamp"
    )
    components: dict = Field(
        default_factory=dict,
        description="Status of individual components"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "2.0.0",
                "timestamp": "2025-12-07T10:30:00Z",
                "components": {
                    "database": "healthy",
                    "stt_worker": "healthy",
                    "moderation_worker": "healthy",
                    "cache": "not_configured"
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response following RFC 7807.
    
    Attributes:
        type: Error type URI
        title: Short error description
        status: HTTP status code
        detail: Detailed error message
        instance: Request instance identifier
    
    Example:
        ```python
        error = ErrorResponse(
            type="https://api.example.com/errors/validation",
            title="Validation Error",
            status=400,
            detail="Invalid audio format",
            instance="/api/v1/transcribe"
        )
        ```
    """
    
    type: str = Field(
        ...,
        description="Error type URI"
    )
    title: str = Field(
        ...,
        description="Short error description"
    )
    status: int = Field(
        ...,
        ge=400,
        le=599,
        description="HTTP status code"
    )
    detail: str = Field(
        ...,
        description="Detailed error message"
    )
    instance: Optional[str] = Field(
        default=None,
        description="Request instance identifier"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "https://api.example.com/errors/validation",
                "title": "Validation Error",
                "status": 400,
                "detail": "Audio sample rate must be 16000 Hz",
                "instance": "/api/v1/transcribe"
            }
        }
