"""
WebSocket Notification Handler - Infrastructure Layer.

Implements INotificationHandler for WebSocket channel.
Manages WebSocket connections and broadcasts events to connected clients.
"""

from typing import Dict, Set, Any, Optional
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect

from app.application.services.notification_service import (
    INotificationHandler,
    Notification,
    NotificationChannel,
)

logger = logging.getLogger(__name__)


# ==================== Connection Manager ====================


class WebSocketConnectionManager:
    """
    Manages WebSocket connections for notification broadcasting.

    Maintains active connections grouped by session/user ID.
    """

    def __init__(self):
        """Initialize connection manager."""
        # Map session_id -> Set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()

            self._connections[session_id].add(websocket)

        logger.info(f"WebSocket connected for session: {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(websocket)

                # Remove empty session entry
                if not self._connections[session_id]:
                    del self._connections[session_id]

        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_to_session(self, session_id: str, message: Dict[str, Any]) -> int:
        """
        Send message to all connections for a session.

        Args:
            session_id: Target session
            message: JSON-serializable message

        Returns:
            Number of connections message was sent to
        """
        if session_id not in self._connections:
            logger.debug(f"No active connections for session: {session_id}")
            return 0

        connections = list(
            self._connections[session_id]
        )  # Copy to avoid modification during iteration
        sent_count = 0
        failed_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected during send: {session_id}")
                failed_connections.append(websocket)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                failed_connections.append(websocket)

        # Clean up failed connections
        if failed_connections:
            async with self._lock:
                for ws in failed_connections:
                    self._connections[session_id].discard(ws)

                if not self._connections[session_id]:
                    del self._connections[session_id]

        return sent_count

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast message to all active connections.

        Args:
            message: JSON-serializable message

        Returns:
            Number of connections message was sent to
        """
        total_sent = 0

        for session_id in list(self._connections.keys()):
            count = await self.send_to_session(session_id, message)
            total_sent += count

        return total_sent

    def get_active_sessions(self) -> Set[str]:
        """
        Get set of all active session IDs.

        Returns:
            Set of session IDs with active connections
        """
        return set(self._connections.keys())

    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """
        Get count of active connections.

        Args:
            session_id: Optional session to count connections for.
                       If None, returns total count across all sessions.

        Returns:
            Number of active connections
        """
        if session_id is not None:
            return len(self._connections.get(session_id, set()))

        return sum(len(conns) for conns in self._connections.values())


# ==================== WebSocket Notification Handler ====================


class WebSocketNotificationHandler(INotificationHandler):
    """
    WebSocket notification handler.

    Sends notifications to connected WebSocket clients.
    """

    def __init__(self, connection_manager: WebSocketConnectionManager):
        """
        Initialize handler.

        Args:
            connection_manager: WebSocket connection manager
        """
        self._connection_manager = connection_manager
        self._is_available = True

    async def send(self, notification: Notification) -> bool:
        """
        Send notification via WebSocket.

        Args:
            notification: Notification to send

        Returns:
            True if sent to at least one connection, False otherwise
        """
        # Build WebSocket message
        message = {
            "type": notification.event_type,
            "data": notification.payload,
            "priority": notification.priority.value,
            "timestamp": notification.timestamp.isoformat(),
        }

        if notification.metadata:
            message["metadata"] = notification.metadata

        # Send to session
        sent_count = await self._connection_manager.send_to_session(
            session_id=notification.recipient_id, message=message
        )

        return sent_count > 0

    async def is_available(self) -> bool:
        """
        Check if WebSocket channel is available.

        Returns:
            True if available, False otherwise
        """
        return self._is_available

    def get_channel(self) -> NotificationChannel:
        """
        Get the channel this handler manages.

        Returns:
            NotificationChannel.WEBSOCKET
        """
        return NotificationChannel.WEBSOCKET

    async def broadcast(self, notification: Notification) -> int:
        """
        Broadcast notification to all connected clients.

        Args:
            notification: Notification to broadcast

        Returns:
            Number of clients notified
        """
        message = {
            "type": notification.event_type,
            "data": notification.payload,
            "priority": notification.priority.value,
            "timestamp": notification.timestamp.isoformat(),
        }

        if notification.metadata:
            message["metadata"] = notification.metadata

        return await self._connection_manager.broadcast(message)

    def get_connection_manager(self) -> WebSocketConnectionManager:
        """
        Get the connection manager.

        Returns:
            WebSocketConnectionManager instance
        """
        return self._connection_manager


# ==================== Global Instance ====================

# Global connection manager instance
# Should be initialized during application startup
_global_connection_manager: Optional[WebSocketConnectionManager] = None


def get_connection_manager() -> WebSocketConnectionManager:
    """
    Get global WebSocket connection manager.

    Returns:
        WebSocketConnectionManager instance

    Raises:
        RuntimeError: If connection manager not initialized
    """
    global _global_connection_manager

    if _global_connection_manager is None:
        _global_connection_manager = WebSocketConnectionManager()

    return _global_connection_manager


def create_websocket_handler() -> WebSocketNotificationHandler:
    """
    Create WebSocket notification handler.

    Returns:
        WebSocketNotificationHandler instance
    """
    manager = get_connection_manager()
    return WebSocketNotificationHandler(connection_manager=manager)
