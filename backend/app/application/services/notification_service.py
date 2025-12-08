"""
Notification Service - Application Layer.

Provides abstraction for real-time notifications across different channels.
Supports WebSocket push, future email/SMS/push notifications.

This service decouples notification logic from specific implementations,
making it easy to add new notification channels without changing use cases.
"""

from typing import Dict, Any, Optional, List, Protocol
from datetime import datetime, timezone
from enum import Enum
import asyncio
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ==================== Notification Types ====================


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    WEBSOCKET = "websocket"
    EMAIL = "email"  # Future
    SMS = "sms"  # Future
    PUSH = "push"  # Future
    WEBHOOK = "webhook"  # Future


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ==================== Notification Models ====================


@dataclass
class Notification:
    """
    Notification message model.

    Attributes:
        channel: Target notification channel
        recipient_id: Recipient identifier (session_id for WebSocket, email for EMAIL, etc.)
        event_type: Type of event (transcription_result, moderation_alert, etc.)
        payload: Event-specific data
        priority: Notification priority
        timestamp: When notification was created
        metadata: Additional metadata
    """

    channel: NotificationChannel
    recipient_id: str
    event_type: str
    payload: Dict[str, Any]
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


# ==================== Notification Handler Protocol ====================


class INotificationHandler(Protocol):
    """
    Protocol for notification channel handlers.

    Each channel (WebSocket, Email, SMS, etc.) should implement this protocol.
    """

    async def send(self, notification: Notification) -> bool:
        """
        Send notification through this channel.

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        ...

    async def is_available(self) -> bool:
        """
        Check if this channel is currently available.

        Returns:
            True if available, False otherwise
        """
        ...

    def get_channel(self) -> NotificationChannel:
        """
        Get the channel this handler manages.

        Returns:
            NotificationChannel enum value
        """
        ...


# ==================== Notification Service ====================


class NotificationService:
    """
    Centralized notification service.

    Manages multiple notification channels and provides unified API
    for sending notifications regardless of the underlying channel.

    Example:
        ```python
        # Register handlers
        service = NotificationService()
        service.register_handler(websocket_handler)
        service.register_handler(email_handler)

        # Send notification
        notification = Notification(
            channel=NotificationChannel.WEBSOCKET,
            recipient_id="session-123",
            event_type="transcription_result",
            payload={"text": "Xin chào", "confidence": 0.95}
        )

        await service.send(notification)
        ```
    """

    def __init__(self):
        """Initialize notification service."""
        self._handlers: Dict[NotificationChannel, INotificationHandler] = {}
        self._default_channel: Optional[NotificationChannel] = None
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running = False

    def register_handler(
        self, handler: INotificationHandler, set_as_default: bool = False
    ) -> None:
        """
        Register a notification channel handler.

        Args:
            handler: Handler implementing INotificationHandler protocol
            set_as_default: If True, set this channel as default

        Raises:
            ValueError: If handler for channel already registered
        """
        channel = handler.get_channel()

        if channel in self._handlers:
            raise ValueError(f"Handler for channel {channel} already registered")

        self._handlers[channel] = handler
        logger.info(f"Registered notification handler for channel: {channel}")

        if set_as_default or self._default_channel is None:
            self._default_channel = channel
            logger.info(f"Set default notification channel: {channel}")

    def unregister_handler(self, channel: NotificationChannel) -> None:
        """
        Unregister a notification channel handler.

        Args:
            channel: Channel to unregister
        """
        if channel in self._handlers:
            del self._handlers[channel]
            logger.info(f"Unregistered notification handler for channel: {channel}")

            if self._default_channel == channel:
                # Set new default if available
                if self._handlers:
                    self._default_channel = next(iter(self._handlers.keys()))
                else:
                    self._default_channel = None

    async def send(
        self,
        notification: Notification,
        fallback_channels: Optional[List[NotificationChannel]] = None,
    ) -> bool:
        """
        Send notification through specified channel.

        If the primary channel fails, tries fallback channels in order.

        Args:
            notification: Notification to send
            fallback_channels: Optional list of fallback channels

        Returns:
            True if sent successfully through any channel, False otherwise
        """
        # Try primary channel
        if notification.channel in self._handlers:
            handler = self._handlers[notification.channel]

            if await handler.is_available():
                try:
                    success = await handler.send(notification)
                    if success:
                        logger.debug(
                            f"Sent notification via {notification.channel}: "
                            f"{notification.event_type} to {notification.recipient_id}"
                        )
                        return True
                except Exception as e:
                    logger.error(
                        f"Error sending notification via {notification.channel}: {e}"
                    )

        # Try fallback channels
        if fallback_channels:
            for fallback_channel in fallback_channels:
                if fallback_channel in self._handlers:
                    handler = self._handlers[fallback_channel]

                    if await handler.is_available():
                        try:
                            # Create copy with fallback channel
                            fallback_notification = Notification(
                                channel=fallback_channel,
                                recipient_id=notification.recipient_id,
                                event_type=notification.event_type,
                                payload=notification.payload,
                                priority=notification.priority,
                                timestamp=notification.timestamp,
                                metadata=notification.metadata,
                            )

                            success = await handler.send(fallback_notification)
                            if success:
                                logger.info(
                                    f"Sent notification via fallback {fallback_channel}: "
                                    f"{notification.event_type} to {notification.recipient_id}"
                                )
                                return True
                        except Exception as e:
                            logger.error(
                                f"Error sending notification via fallback {fallback_channel}: {e}"
                            )

        logger.warning(
            f"Failed to send notification {notification.event_type} "
            f"to {notification.recipient_id} via any channel"
        )
        return False

    async def broadcast(
        self,
        event_type: str,
        payload: Dict[str, Any],
        channel: Optional[NotificationChannel] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> int:
        """
        Broadcast notification to all recipients on a channel.

        Args:
            event_type: Type of event
            payload: Event data
            channel: Target channel (uses default if None)
            priority: Notification priority

        Returns:
            Number of recipients notification was sent to
        """
        target_channel = channel or self._default_channel

        if target_channel is None:
            logger.warning("No channel specified and no default channel set")
            return 0

        if target_channel not in self._handlers:
            logger.warning(f"No handler registered for channel {target_channel}")
            return 0

        # For broadcast, we need handler-specific logic
        # For now, log warning that broadcast needs handler implementation
        logger.warning(
            f"Broadcast not yet implemented for {target_channel}. "
            "Handler must implement broadcast support."
        )
        return 0

    async def send_async(self, notification: Notification) -> None:
        """
        Send notification asynchronously (queued).

        Notification is added to queue and processed by background task.
        Useful for fire-and-forget notifications.

        Args:
            notification: Notification to send
        """
        await self._notification_queue.put(notification)

    async def start_background_processing(self) -> None:
        """
        Start background task for processing queued notifications.

        Should be called during application startup.
        """
        if self._is_running:
            logger.warning("Background processing already running")
            return

        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_queue())
        logger.info("Started notification background processing")

    async def stop_background_processing(self) -> None:
        """
        Stop background processing.

        Should be called during application shutdown.
        """
        self._is_running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        logger.info("Stopped notification background processing")

    async def _process_queue(self) -> None:
        """Background task to process notification queue."""
        logger.info("Notification queue processor started")

        while self._is_running:
            try:
                # Wait for notification with timeout
                notification = await asyncio.wait_for(
                    self._notification_queue.get(), timeout=1.0
                )

                # Process notification
                await self.send(notification)

            except asyncio.TimeoutError:
                # No notifications in queue, continue
                continue
            except asyncio.CancelledError:
                logger.info("Notification queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued notification: {e}")

        logger.info("Notification queue processor stopped")

    def get_available_channels(self) -> List[NotificationChannel]:
        """
        Get list of all registered channels.

        Returns:
            List of registered NotificationChannel values
        """
        return list(self._handlers.keys())

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health status of all notification channels.

        Returns:
            Dictionary with health status of each channel
        """
        health_status = {
            "service_running": self._is_running,
            "queue_size": self._notification_queue.qsize(),
            "default_channel": (
                self._default_channel.value if self._default_channel else None
            ),
            "channels": {},
        }

        for channel, handler in self._handlers.items():
            try:
                is_available = await handler.is_available()
                health_status["channels"][channel.value] = {
                    "available": is_available,
                    "error": None,
                }
            except Exception as e:
                health_status["channels"][channel.value] = {
                    "available": False,
                    "error": str(e),
                }

        return health_status


# ==================== Helper Functions ====================


def create_transcription_notification(
    session_id: str,
    transcription_data: Dict[str, Any],
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Notification:
    """
    Create notification for transcription result.

    Args:
        session_id: Session identifier (WebSocket recipient)
        transcription_data: Transcription result data
        priority: Notification priority

    Returns:
        Notification instance
    """
    return Notification(
        channel=NotificationChannel.WEBSOCKET,
        recipient_id=session_id,
        event_type="transcription_result",
        payload=transcription_data,
        priority=priority,
    )


def create_moderation_alert(
    session_id: str,
    moderation_data: Dict[str, Any],
    priority: NotificationPriority = NotificationPriority.HIGH,
) -> Notification:
    """
    Create notification for moderation alert.

    Args:
        session_id: Session identifier
        moderation_data: Moderation result data
        priority: Notification priority (default: HIGH)

    Returns:
        Notification instance
    """
    return Notification(
        channel=NotificationChannel.WEBSOCKET,
        recipient_id=session_id,
        event_type="moderation_alert",
        payload=moderation_data,
        priority=priority,
    )
