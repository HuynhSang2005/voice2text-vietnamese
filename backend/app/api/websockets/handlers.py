"""
Presentation Layer - WebSocket Message Handlers

This module provides a centralized message routing and handling system
for WebSocket connections following Clean Architecture principles.

Key Features:
- Type-safe message routing
- Handler registration pattern
- Standardized error formatting
- Clean separation of concerns

Design Pattern: Strategy + Registry
- Each message type has its own handler (Strategy)
- Handlers are registered in a central registry
- Router delegates to appropriate handler based on message type
"""

from typing import Dict, Callable, Any, Awaitable, Optional
import logging
from enum import Enum
from datetime import datetime

from fastapi import WebSocket
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# Message Types Enum
class MessageType(str, Enum):
    """WebSocket message types."""
    CONFIG = "config"
    AUDIO = "audio"
    PING = "ping"
    PONG = "pong"
    FLUSH = "flush"
    RESET = "reset"
    TRANSCRIPTION = "transcription"
    MODERATION = "moderation"
    ERROR = "error"


# Message Models
class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: MessageType
    timestamp: Optional[float] = Field(default_factory=lambda: datetime.now().timestamp())


class ConfigMessage(WebSocketMessage):
    """Configuration message from client."""
    type: MessageType = MessageType.CONFIG
    model: str = "zipformer"
    sample_rate: int = 16000
    enable_moderation: bool = True
    session_id: Optional[str] = None
    language: str = "vi"


class PingMessage(WebSocketMessage):
    """Heartbeat ping message."""
    type: MessageType = MessageType.PING


class PongMessage(WebSocketMessage):
    """Heartbeat pong response."""
    type: MessageType = MessageType.PONG


class FlushMessage(WebSocketMessage):
    """Flush signal to force transcription of remaining buffer."""
    type: MessageType = MessageType.FLUSH


class ResetMessage(WebSocketMessage):
    """Reset signal to clear transcription state."""
    type: MessageType = MessageType.RESET


class TranscriptionMessage(WebSocketMessage):
    """Transcription result message to client."""
    type: MessageType = MessageType.TRANSCRIPTION
    text: str
    is_final: bool
    model: str
    latency_ms: float
    confidence: Optional[float] = None


class ModerationMessage(WebSocketMessage):
    """Content moderation result message to client."""
    type: MessageType = MessageType.MODERATION
    label: str
    confidence: float
    is_flagged: bool
    detected_keywords: list[str] = Field(default_factory=list)


class ErrorMessage(WebSocketMessage):
    """Error message to client."""
    type: MessageType = MessageType.ERROR
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Handler Type Alias
MessageHandler = Callable[[WebSocket, Dict[str, Any]], Awaitable[None]]


class WebSocketMessageRouter:
    """
    Routes WebSocket messages to appropriate handlers.
    
    This class implements the Registry pattern for message handling,
    allowing clean separation of message routing logic from business logic.
    
    Example:
        ```python
        router = WebSocketMessageRouter()
        
        async def handle_config(ws: WebSocket, data: dict):
            config = ConfigMessage(**data)
            # Handle config...
        
        router.register(MessageType.CONFIG, handle_config)
        
        # Route incoming message
        await router.route(websocket, {"type": "config", "model": "zipformer"})
        ```
    """
    
    def __init__(self):
        """Initialize the message router."""
        self._handlers: Dict[MessageType, MessageHandler] = {}
        self._default_handler: Optional[MessageHandler] = None
    
    def register(
        self,
        message_type: MessageType,
        handler: MessageHandler
    ) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        
        Example:
            ```python
            async def handle_ping(ws: WebSocket, data: dict):
                await ws.send_json({"type": "pong", "timestamp": data["timestamp"]})
            
            router.register(MessageType.PING, handle_ping)
            ```
        """
        if message_type in self._handlers:
            logger.warning(f"Overwriting existing handler for {message_type}")
        
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}")
    
    def register_default(self, handler: MessageHandler) -> None:
        """
        Register a default handler for unrecognized message types.
        
        Args:
            handler: Async function to handle unknown messages
        """
        self._default_handler = handler
        logger.debug("Registered default handler")
    
    async def route(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ) -> None:
        """
        Route a message to the appropriate handler.
        
        Args:
            websocket: WebSocket connection
            message: Message data (must contain "type" field)
        
        Raises:
            ValueError: If message has no "type" field
        """
        # Extract message type
        msg_type_str = message.get("type")
        if not msg_type_str:
            await self._send_error(
                websocket,
                code="MISSING_TYPE",
                message="Message must have a 'type' field"
            )
            return
        
        # Convert to MessageType enum
        try:
            msg_type = MessageType(msg_type_str)
        except ValueError:
            logger.warning(f"Unknown message type: {msg_type_str}")
            if self._default_handler:
                await self._default_handler(websocket, message)
            else:
                await self._send_error(
                    websocket,
                    code="UNKNOWN_TYPE",
                    message=f"Unknown message type: {msg_type_str}"
                )
            return
        
        # Get handler
        handler = self._handlers.get(msg_type)
        if not handler:
            logger.warning(f"No handler registered for {msg_type}")
            if self._default_handler:
                await self._default_handler(websocket, message)
            else:
                await self._send_error(
                    websocket,
                    code="NO_HANDLER",
                    message=f"No handler available for message type: {msg_type}"
                )
            return
        
        # Execute handler
        try:
            await handler(websocket, message)
        except Exception as e:
            logger.error(f"Error handling {msg_type}: {e}", exc_info=True)
            await self._send_error(
                websocket,
                code="HANDLER_ERROR",
                message=f"Error processing {msg_type} message",
                details={"error": str(e)}
            )
    
    async def _send_error(
        self,
        websocket: WebSocket,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send error message to client."""
        error = ErrorMessage(
            code=code,
            message=message,
            details=details
        )
        try:
            await websocket.send_json(error.model_dump())
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    def list_handlers(self) -> Dict[str, str]:
        """
        List all registered handlers.
        
        Returns:
            Dictionary mapping message types to handler names
        """
        return {
            msg_type.value: handler.__name__
            for msg_type, handler in self._handlers.items()
        }


# Utility Functions for Error Formatting
def format_validation_error(error: Exception) -> ErrorMessage:
    """
    Format a Pydantic validation error as ErrorMessage.
    
    Args:
        error: Pydantic ValidationError
    
    Returns:
        ErrorMessage with validation details
    """
    return ErrorMessage(
        code="VALIDATION_ERROR",
        message="Invalid message format",
        details={"error": str(error)}
    )


def format_business_error(
    rule: str,
    reason: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorMessage:
    """
    Format a business rule violation as ErrorMessage.
    
    Args:
        rule: Business rule identifier
        reason: Human-readable explanation
        details: Additional context
    
    Returns:
        ErrorMessage with business error details
    """
    return ErrorMessage(
        code=rule.upper(),
        message=reason,
        details=details
    )


def format_internal_error(error: Exception) -> ErrorMessage:
    """
    Format an internal error as ErrorMessage.
    
    Args:
        error: Exception that occurred
    
    Returns:
        ErrorMessage with generic error message (hides internal details)
    """
    # Don't expose internal error details to client for security
    return ErrorMessage(
        code="INTERNAL_ERROR",
        message="An internal error occurred. Please try again.",
        details=None  # Intentionally hidden
    )


# Example Handler Implementations
async def handle_ping(websocket: WebSocket, data: Dict[str, Any]) -> None:
    """
    Handle ping message - respond with pong.
    
    This is the default ping/pong handler implementation.
    """
    timestamp = data.get("timestamp", datetime.now().timestamp())
    pong = PongMessage(timestamp=timestamp)
    await websocket.send_json(pong.model_dump())
    logger.debug(f"Ping-pong: {timestamp}")


async def handle_unknown(websocket: WebSocket, data: Dict[str, Any]) -> None:
    """
    Default handler for unknown message types.
    
    Logs the unknown message and sends error to client.
    """
    msg_type = data.get("type", "UNKNOWN")
    logger.warning(f"Received unknown message type: {msg_type}")
    
    error = ErrorMessage(
        code="UNKNOWN_MESSAGE",
        message=f"Unknown message type: {msg_type}",
        details={"received_type": msg_type}
    )
    await websocket.send_json(error.model_dump())


# Factory Function
def create_default_router() -> WebSocketMessageRouter:
    """
    Create a WebSocket message router with default handlers.
    
    Returns:
        WebSocketMessageRouter with ping/pong handler registered
    
    Example:
        ```python
        router = create_default_router()
        
        # Add custom handlers
        router.register(MessageType.CONFIG, my_config_handler)
        
        # Use in WebSocket endpoint
        async for message in websocket:
            await router.route(websocket, message)
        ```
    """
    router = WebSocketMessageRouter()
    
    # Register default handlers
    router.register(MessageType.PING, handle_ping)
    router.register_default(handle_unknown)
    
    logger.info("Created default WebSocket message router")
    return router
