"""
Session repository implementation using SQLModel.

This module provides the concrete implementation of ISessionRepository
using SQLModel ORM for database operations.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from sqlmodel import select, delete as sql_delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.session import Session
from app.domain.repositories.session_repository import ISessionRepository
from app.domain.exceptions.repository import RepositoryError
from app.infrastructure.database.models import SessionModel

logger = logging.getLogger(__name__)


class SessionRepositoryImpl(ISessionRepository):
    """
    SQLModel implementation of session repository.

    Handles CRUD operations for sessions with expiration logic,
    including entity-model mapping and error handling.

    Attributes:
        session: Async SQLModel session for database operations
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLModel session
        """
        self._session = session

    async def save(self, session: Session) -> Session:
        """
        Save session entity to database.

        Args:
            session: Session entity to save

        Returns:
            Saved session entity

        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Convert entity to model
            model = self._to_model(session)

            # Merge (insert or update)
            self._session.add(model)
            await self._session.commit()
            await self._session.refresh(model)

            # Convert back to entity
            result = self._to_entity(model)

            logger.debug(f"Saved session: id={result.id}, model_id={result.model_id}")

            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to save session: {e}")
            raise RepositoryError(f"Failed to save session: {e}") from e

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
        try:
            model = await self._session.get(SessionModel, session_id)

            if model is None:
                return None

            return self._to_entity(model)

        except Exception as e:
            logger.error(f"Failed to find session by id={session_id}: {e}")
            raise RepositoryError(
                f"Failed to find session by id={session_id}: {e}"
            ) from e

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
        try:
            now = datetime.now(timezone.utc)

            statement = select(SessionModel).where(
                SessionModel.is_active.is_(True), SessionModel.expires_at > now
            )

            # Apply optional filter
            if model_id is not None:
                statement = statement.where(SessionModel.model_id == model_id)

            # Order by most recent first
            statement = statement.order_by(SessionModel.created_at.desc())

            result = await self._session.execute(statement)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]

        except Exception as e:
            logger.error(f"Failed to find active sessions: {e}")
            raise RepositoryError(f"Failed to find active sessions: {e}") from e

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
        try:
            model = await self._session.get(SessionModel, session_id)

            if model is None:
                return False

            await self._session.delete(model)
            await self._session.commit()

            logger.debug(f"Deleted session: id={session_id}")

            return True

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete session id={session_id}: {e}")
            raise RepositoryError(
                f"Failed to delete session id={session_id}: {e}"
            ) from e

    async def delete_expired(self) -> int:
        """
        Delete all expired sessions.

        Returns:
            Number of sessions deleted

        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            now = datetime.now(timezone.utc)

            statement = sql_delete(SessionModel).where(SessionModel.expires_at < now)

            result = await self._session.execute(statement)
            await self._session.commit()

            deleted_count = result.rowcount

            logger.info(f"Deleted {deleted_count} expired sessions")

            return deleted_count

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete expired sessions: {e}")
            raise RepositoryError(f"Failed to delete expired sessions: {e}") from e

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
        try:
            model = await self._session.get(SessionModel, session_id)

            if model is None:
                return False

            # Update count
            model.transcription_count += increment

            await self._session.commit()

            logger.debug(
                f"Updated session {session_id} transcription_count to "
                f"{model.transcription_count}"
            )

            return True

        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to update transcription count for session {session_id}: {e}"
            )
            raise RepositoryError(
                f"Failed to update transcription count for session {session_id}: {e}"
            ) from e

    def _to_entity(self, model: SessionModel) -> Session:
        """
        Convert SQLModel model to domain entity.

        Args:
            model: SessionModel instance

        Returns:
            Session domain entity
        """
        return Session(
            id=model.id,
            model_id=model.model_id,
            created_at=model.created_at,
            expires_at=model.expires_at,
            is_active=model.is_active,
            transcription_count=model.transcription_count,
        )

    def _to_model(self, entity: Session) -> SessionModel:
        """
        Convert domain entity to SQLModel model.

        Args:
            entity: Session domain entity

        Returns:
            SessionModel instance
        """
        return SessionModel(
            id=entity.id,
            model_id=entity.model_id,
            created_at=entity.created_at,
            expires_at=entity.expires_at,
            is_active=entity.is_active,
            transcription_count=entity.transcription_count,
        )
