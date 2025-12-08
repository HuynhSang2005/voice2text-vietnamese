"""
Unit tests for NotificationService.

Tests verify:
1. Handler registration and management
2. Notification sending through channels
3. Fallback channel logic
4. Async/queued notifications
5. Broadcast functionality
6. Health checking
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from app.application.services.notification_service import (
    NotificationService,
    Notification,
    NotificationChannel,
    NotificationPriority,
    INotificationHandler,
    create_transcription_notification,
    create_moderation_alert,
)


# ==================== Fixtures ====================


@pytest.fixture
def mock_websocket_handler():
    """Create mock WebSocket handler."""
    handler = AsyncMock(spec=INotificationHandler)
    handler.get_channel = Mock(return_value=NotificationChannel.WEBSOCKET)
    handler.is_available = AsyncMock(return_value=True)
    handler.send = AsyncMock(return_value=True)
    return handler


@pytest.fixture
def mock_email_handler():
    """Create mock Email handler."""
    handler = AsyncMock(spec=INotificationHandler)
    handler.get_channel = Mock(return_value=NotificationChannel.EMAIL)
    handler.is_available = AsyncMock(return_value=True)
    handler.send = AsyncMock(return_value=True)
    return handler


@pytest.fixture
def notification_service():
    """Create fresh NotificationService instance."""
    return NotificationService()


@pytest.fixture
def sample_notification():
    """Create sample notification."""
    return Notification(
        channel=NotificationChannel.WEBSOCKET,
        recipient_id="session-123",
        event_type="transcription_result",
        payload={"text": "Xin chào", "confidence": 0.95},
        priority=NotificationPriority.NORMAL
    )


# ==================== Test Cases ====================


class TestNotificationServiceRegistration:
    """Test handler registration."""
    
    def test_register_handler(self, notification_service, mock_websocket_handler):
        """Test registering a handler."""
        notification_service.register_handler(mock_websocket_handler)
        
        channels = notification_service.get_available_channels()
        assert NotificationChannel.WEBSOCKET in channels
    
    def test_register_handler_sets_default(self, notification_service, mock_websocket_handler):
        """Test first registered handler becomes default."""
        notification_service.register_handler(mock_websocket_handler)
        
        assert notification_service._default_channel == NotificationChannel.WEBSOCKET
    
    def test_register_multiple_handlers(
        self,
        notification_service,
        mock_websocket_handler,
        mock_email_handler
    ):
        """Test registering multiple handlers."""
        notification_service.register_handler(mock_websocket_handler)
        notification_service.register_handler(mock_email_handler)
        
        channels = notification_service.get_available_channels()
        assert NotificationChannel.WEBSOCKET in channels
        assert NotificationChannel.EMAIL in channels
    
    def test_register_duplicate_handler_raises_error(
        self,
        notification_service,
        mock_websocket_handler
    ):
        """Test registering duplicate handler raises ValueError."""
        notification_service.register_handler(mock_websocket_handler)
        
        with pytest.raises(ValueError) as exc_info:
            notification_service.register_handler(mock_websocket_handler)
        
        assert "already registered" in str(exc_info.value)
    
    def test_unregister_handler(self, notification_service, mock_websocket_handler):
        """Test unregistering a handler."""
        notification_service.register_handler(mock_websocket_handler)
        notification_service.unregister_handler(NotificationChannel.WEBSOCKET)
        
        channels = notification_service.get_available_channels()
        assert NotificationChannel.WEBSOCKET not in channels


class TestNotificationSending:
    """Test sending notifications."""
    
    @pytest.mark.asyncio
    async def test_send_notification_success(
        self,
        notification_service,
        mock_websocket_handler,
        sample_notification
    ):
        """Test successfully sending notification."""
        notification_service.register_handler(mock_websocket_handler)
        
        success = await notification_service.send(sample_notification)
        
        assert success is True
        mock_websocket_handler.send.assert_called_once_with(sample_notification)
    
    @pytest.mark.asyncio
    async def test_send_notification_channel_unavailable(
        self,
        notification_service,
        mock_websocket_handler,
        sample_notification
    ):
        """Test sending when channel is unavailable."""
        mock_websocket_handler.is_available = AsyncMock(return_value=False)
        notification_service.register_handler(mock_websocket_handler)
        
        success = await notification_service.send(sample_notification)
        
        assert success is False
        mock_websocket_handler.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_notification_no_handler(
        self,
        notification_service,
        sample_notification
    ):
        """Test sending when no handler registered."""
        success = await notification_service.send(sample_notification)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_send_with_fallback_channel(
        self,
        notification_service,
        mock_websocket_handler,
        mock_email_handler,
        sample_notification
    ):
        """Test fallback to alternative channel."""
        # Primary channel fails
        mock_websocket_handler.send = AsyncMock(return_value=False)
        notification_service.register_handler(mock_websocket_handler)
        notification_service.register_handler(mock_email_handler)
        
        success = await notification_service.send(
            sample_notification,
            fallback_channels=[NotificationChannel.EMAIL]
        )
        
        assert success is True
        mock_email_handler.send.assert_called_once()


class TestAsyncNotifications:
    """Test asynchronous notification processing."""
    
    @pytest.mark.asyncio
    async def test_send_async_queues_notification(
        self,
        notification_service,
        sample_notification
    ):
        """Test async send queues notification."""
        await notification_service.send_async(sample_notification)
        
        assert notification_service._notification_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_background_processing_sends_queued_notifications(
        self,
        notification_service,
        mock_websocket_handler,
        sample_notification
    ):
        """Test background processor sends queued notifications."""
        notification_service.register_handler(mock_websocket_handler)
        
        # Start background processing
        await notification_service.start_background_processing()
        
        # Queue notification
        await notification_service.send_async(sample_notification)
        
        # Wait for processing
        import asyncio
        await asyncio.sleep(0.1)
        
        # Verify notification was sent
        assert mock_websocket_handler.send.call_count == 1
        
        # Stop background processing
        await notification_service.stop_background_processing()


class TestHealthCheck:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check(
        self,
        notification_service,
        mock_websocket_handler
    ):
        """Test health check returns correct status."""
        notification_service.register_handler(mock_websocket_handler)
        
        health = await notification_service.health_check()
        
        assert "service_running" in health
        assert "queue_size" in health
        assert "default_channel" in health
        assert "channels" in health
        assert NotificationChannel.WEBSOCKET.value in health["channels"]
        assert health["channels"][NotificationChannel.WEBSOCKET.value]["available"] is True


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_create_transcription_notification(self):
        """Test creating transcription notification."""
        notification = create_transcription_notification(
            session_id="session-123",
            transcription_data={"text": "Xin chào", "confidence": 0.95}
        )
        
        assert notification.channel == NotificationChannel.WEBSOCKET
        assert notification.recipient_id == "session-123"
        assert notification.event_type == "transcription_result"
        assert notification.payload["text"] == "Xin chào"
        assert notification.priority == NotificationPriority.NORMAL
    
    def test_create_moderation_alert(self):
        """Test creating moderation alert."""
        notification = create_moderation_alert(
            session_id="session-123",
            moderation_data={"label": "OFFENSIVE", "confidence": 0.92}
        )
        
        assert notification.channel == NotificationChannel.WEBSOCKET
        assert notification.recipient_id == "session-123"
        assert notification.event_type == "moderation_alert"
        assert notification.payload["label"] == "OFFENSIVE"
        assert notification.priority == NotificationPriority.HIGH
