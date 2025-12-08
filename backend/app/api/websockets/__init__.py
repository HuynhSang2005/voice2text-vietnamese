"""
WebSocket Endpoints - Real-time Communication

This module exports WebSocket routers for real-time functionality:
- transcription: Real-time speech-to-text WebSocket endpoint
- handlers: WebSocket message routing and handler system
"""

from app.api.websockets.transcription import router as transcription_router
from app.api.websockets.handlers import (
    WebSocketMessageRouter,
    create_default_router,
    MessageType,
)

__all__ = [
    "transcription_router",
    "WebSocketMessageRouter",
    "create_default_router",
    "MessageType",
]
