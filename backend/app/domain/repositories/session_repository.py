"""Session repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.domain.entities.session import Session


class ISessionRepository(ABC):
    """
    Abstract repository interface for session data access.

    Defines operations for persisting and retrieving user sessions.
    """

    @abstractmethod
    async def save(self, session: Session) -> Session:
        """
        Save a session entity to storage.

        Args:
            session: Session entity to save

        Returns:
            Saved session

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def find_by_id(self, session_id: str) -> Optional[Session]:
        """
        Find session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            Session entity if found, None otherwise

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def find_active_sessions(
        self,
        model_id: Optional[str] = None,
    ) -> List[Session]:
        """
        Find all active (non-expired) sessions.

        Args:
            model_id: Optional filter by model ID

        Returns:
            List of active session entities

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        Delete session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    async def delete_expired(self) -> int:
        """
        Delete all expired sessions.

        Returns:
            Number of sessions deleted

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    async def update_transcription_count(
        self,
        session_id: str,
        increment: int = 1,
    ) -> bool:
        """
        Update session transcription count.

        Args:
            session_id: Session identifier
            increment: Amount to increment (default: 1)

        Returns:
            True if updated, False if session not found

        Raises:
            RepositoryError: If update fails
        """
        pass
