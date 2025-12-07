"""
Application Layer - DTOs (Data Transfer Objects)

Central module for importing all request and response DTOs.

Usage:
    ```python
    from app.application.dtos import (
        TranscriptionRequest,
        TranscriptionResponse,
        HistoryQueryRequest,
        HistoryResponse
    )
    ```
"""

# Request DTOs
from app.application.dtos.requests import (
    TranscriptionRequest,
    HistoryQueryRequest,
    ModelSwitchRequest,
    ModerationToggleRequest,
    StandaloneModerateRequest,
    WebSocketConfigMessage,
)

# Response DTOs
from app.application.dtos.responses import (
    TranscriptionResponse,
    ContentModerationResponse,
    ModerationResponse,
    HistoryResponse,
    ModelStatusResponse,
    ModelSwitchResponse,
    HealthCheckResponse,
    ErrorResponse,
)

__all__ = [
    # Request DTOs
    "TranscriptionRequest",
    "HistoryQueryRequest",
    "ModelSwitchRequest",
    "ModerationToggleRequest",
    "StandaloneModerateRequest",
    "WebSocketConfigMessage",
    # Response DTOs
    "TranscriptionResponse",
    "ContentModerationResponse",
    "ModerationResponse",
    "HistoryResponse",
    "ModelStatusResponse",
    "ModelSwitchResponse",
    "HealthCheckResponse",
    "ErrorResponse",
]
