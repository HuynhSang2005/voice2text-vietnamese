"""
Unit tests for WebSocket message handlers.

Tests the message routing and handler registration system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from app.api.websockets.handlers import (
    WebSocketMessageRouter,
    MessageType,
    ConfigMessage,
    PingMessage,
    PongMessage,
    ErrorMessage,
    handle_ping,
    handle_unknown,
    create_default_router,
    format_validation_error,
    format_business_error,
    format_internal_error,
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def router():
    """Create a WebSocketMessageRouter instance."""
    return WebSocketMessageRouter()


class TestWebSocketMessageRouter:
    """Test WebSocketMessageRouter class."""
    
    def test_register_handler(self, router):
        """Test registering a message handler."""
        async def test_handler(ws, data):
            pass
        
        router.register(MessageType.CONFIG, test_handler)
        
        assert MessageType.CONFIG in router._handlers
        assert router._handlers[MessageType.CONFIG] == test_handler
    
    def test_register_default_handler(self, router):
        """Test registering a default handler."""
        async def default_handler(ws, data):
            pass
        
        router.register_default(default_handler)
        
        assert router._default_handler == default_handler
    
    @pytest.mark.asyncio
    async def test_route_to_registered_handler(self, router, mock_websocket):
        """Test routing message to registered handler."""
        handler_called = False
        
        async def test_handler(ws, data):
            nonlocal handler_called
            handler_called = True
            assert ws == mock_websocket
            assert data["type"] == "config"
        
        router.register(MessageType.CONFIG, test_handler)
        
        await router.route(mock_websocket, {"type": "config", "model": "zipformer"})
        
        assert handler_called
    
    @pytest.mark.asyncio
    async def test_route_unknown_message_type_with_default(self, router, mock_websocket):
        """Test routing unknown message type to default handler."""
        default_called = False
        
        async def default_handler(ws, data):
            nonlocal default_called
            default_called = True
        
        router.register_default(default_handler)
        
        await router.route(mock_websocket, {"type": "unknown_type"})
        
        assert default_called
    
    @pytest.mark.asyncio
    async def test_route_unknown_message_type_without_default(self, router, mock_websocket):
        """Test routing unknown message type without default handler."""
        await router.route(mock_websocket, {"type": "unknown_type"})
        
        # Should send error message
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"
        assert "UNKNOWN_TYPE" in sent_message["code"]
    
    @pytest.mark.asyncio
    async def test_route_message_without_type(self, router, mock_websocket):
        """Test routing message without 'type' field."""
        await router.route(mock_websocket, {"data": "some data"})
        
        # Should send error message
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"
        assert "MISSING_TYPE" in sent_message["code"]
    
    @pytest.mark.asyncio
    async def test_route_handler_exception(self, router, mock_websocket):
        """Test handling exception in message handler."""
        async def failing_handler(ws, data):
            raise ValueError("Test error")
        
        router.register(MessageType.CONFIG, failing_handler)
        
        await router.route(mock_websocket, {"type": "config"})
        
        # Should send error message
        mock_websocket.send_json.assert_called()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"
        assert "HANDLER_ERROR" in sent_message["code"]
    
    def test_list_handlers(self, router):
        """Test listing registered handlers."""
        async def handler1(ws, data):
            pass
        
        async def handler2(ws, data):
            pass
        
        router.register(MessageType.CONFIG, handler1)
        router.register(MessageType.PING, handler2)
        
        handlers = router.list_handlers()
        
        assert "config" in handlers
        assert "ping" in handlers
        assert handlers["config"] == "handler1"
        assert handlers["ping"] == "handler2"


class TestMessageModels:
    """Test WebSocket message models."""
    
    def test_config_message(self):
        """Test ConfigMessage model."""
        msg = ConfigMessage(
            model="zipformer",
            sample_rate=16000,
            enable_moderation=True,
            session_id="test-123",
            language="vi"
        )
        
        assert msg.type == MessageType.CONFIG
        assert msg.model == "zipformer"
        assert msg.sample_rate == 16000
        assert msg.enable_moderation is True
    
    def test_ping_message(self):
        """Test PingMessage model."""
        msg = PingMessage(timestamp=1234567890.0)
        
        assert msg.type == MessageType.PING
        assert msg.timestamp == 1234567890.0
    
    def test_pong_message(self):
        """Test PongMessage model."""
        msg = PongMessage(timestamp=1234567890.0)
        
        assert msg.type == MessageType.PONG
        assert msg.timestamp == 1234567890.0
    
    def test_error_message(self):
        """Test ErrorMessage model."""
        msg = ErrorMessage(
            code="TEST_ERROR",
            message="Test error message",
            details={"key": "value"}
        )
        
        assert msg.type == MessageType.ERROR
        assert msg.code == "TEST_ERROR"
        assert msg.message == "Test error message"
        assert msg.details["key"] == "value"


class TestDefaultHandlers:
    """Test default handler implementations."""
    
    @pytest.mark.asyncio
    async def test_handle_ping(self, mock_websocket):
        """Test ping handler sends pong."""
        data = {"type": "ping", "timestamp": 1234567890.0}
        
        await handle_ping(mock_websocket, data)
        
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "pong"
        assert sent_message["timestamp"] == 1234567890.0
    
    @pytest.mark.asyncio
    async def test_handle_unknown(self, mock_websocket):
        """Test unknown handler sends error."""
        data = {"type": "unknown_type", "data": "test"}
        
        await handle_unknown(mock_websocket, data)
        
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"
        assert "UNKNOWN_MESSAGE" in sent_message["code"]


class TestErrorFormatting:
    """Test error formatting utilities."""
    
    def test_format_validation_error(self):
        """Test formatting validation errors."""
        error = ValueError("Invalid input")
        
        msg = format_validation_error(error)
        
        assert msg.type == MessageType.ERROR
        assert msg.code == "VALIDATION_ERROR"
        assert "Invalid message format" in msg.message
    
    def test_format_business_error(self):
        """Test formatting business errors."""
        msg = format_business_error(
            rule="worker_not_ready",
            reason="Transcription worker is not ready",
            details={"worker": "zipformer"}
        )
        
        assert msg.type == MessageType.ERROR
        assert msg.code == "WORKER_NOT_READY"
        assert "not ready" in msg.message
        assert msg.details["worker"] == "zipformer"
    
    def test_format_internal_error(self):
        """Test formatting internal errors."""
        error = RuntimeError("Database connection failed")
        
        msg = format_internal_error(error)
        
        assert msg.type == MessageType.ERROR
        assert msg.code == "INTERNAL_ERROR"
        assert msg.details is None  # Should hide internal details


class TestCreateDefaultRouter:
    """Test factory function for creating default router."""
    
    def test_create_default_router(self):
        """Test creating router with default handlers."""
        router = create_default_router()
        
        assert isinstance(router, WebSocketMessageRouter)
        assert MessageType.PING in router._handlers
        assert router._default_handler is not None
    
    @pytest.mark.asyncio
    async def test_default_router_ping_handler(self, mock_websocket):
        """Test default router handles ping messages."""
        router = create_default_router()
        
        await router.route(mock_websocket, {"type": "ping", "timestamp": 12345})
        
        # Should send pong
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "pong"
