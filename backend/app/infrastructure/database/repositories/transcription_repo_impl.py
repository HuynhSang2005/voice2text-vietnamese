"""
Transcription repository implementation using SQLModel.

This module provides the concrete implementation of ITranscriptionRepository
using SQLModel ORM for database operations.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from sqlmodel import select, func, delete as sql_delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.transcription import Transcription
from app.domain.repositories.transcription_repository import ITranscriptionRepository
from app.domain.exceptions.repository import RepositoryError
from app.infrastructure.database.models import TranscriptionModel

logger = logging.getLogger(__name__)


class TranscriptionRepositoryImpl(ITranscriptionRepository):
    """
    SQLModel implementation of transcription repository.
    
    Handles CRUD operations and complex queries for transcriptions,
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
    
    async def save(self, transcription: Transcription) -> Transcription:
        """
        Save transcription entity to database.
        
        Args:
            transcription: Transcription entity to save
        
        Returns:
            Saved transcription with generated ID
        
        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Convert entity to model
            model = self._to_model(transcription)
            
            # Add to session and commit
            self._session.add(model)
            await self._session.commit()
            await self._session.refresh(model)
            
            # Convert back to entity
            result = self._to_entity(model)
            
            logger.debug(
                f"Saved transcription: id={result.id}, "
                f"session_id={result.session_id}"
            )
            
            return result
            
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to save transcription: {e}")
            raise RepositoryError(f"Failed to save transcription: {e}") from e
    
    async def find_by_id(self, transcription_id: int) -> Optional[Transcription]:
        """
        Find transcription by ID.
        
        Args:
            transcription_id: Unique transcription ID
        
        Returns:
            Transcription entity if found, None otherwise
        
        Raises:
            RepositoryError: If query fails
        """
        try:
            statement = select(TranscriptionModel).where(
                TranscriptionModel.id == transcription_id
            )
            result = await self._session.execute(statement)
            model = result.scalar_one_or_none()
            
            if model is None:
                return None
            
            return self._to_entity(model)
            
        except Exception as e:
            logger.error(f"Failed to find transcription by id={transcription_id}: {e}")
            raise RepositoryError(
                f"Failed to find transcription by id={transcription_id}: {e}"
            ) from e
    
    async def find_by_session_id(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Transcription]:
        """
        Find all transcriptions for a session.
        
        Args:
            session_id: Session identifier
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of transcription entities
        
        Raises:
            RepositoryError: If query fails
        """
        try:
            statement = (
                select(TranscriptionModel)
                .where(TranscriptionModel.session_id == session_id)
                .order_by(TranscriptionModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            result = await self._session.execute(statement)
            models = result.scalars().all()
            
            return [self._to_entity(model) for model in models]
            
        except Exception as e:
            logger.error(
                f"Failed to find transcriptions for session_id={session_id}: {e}"
            )
            raise RepositoryError(
                f"Failed to find transcriptions for session_id={session_id}: {e}"
            ) from e
    
    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        model_id: Optional[str] = None,
        is_offensive: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Transcription]:
        """
        Find transcriptions with optional filters and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            model_id: Filter by model ID
            is_offensive: Filter by offensive status
            start_date: Filter by creation date (from)
            end_date: Filter by creation date (to)
        
        Returns:
            List of transcription entities
        
        Raises:
            RepositoryError: If query fails
        """
        try:
            statement = select(TranscriptionModel)
            
            # Apply filters
            if model_id is not None:
                statement = statement.where(TranscriptionModel.model_id == model_id)
            
            if is_offensive is not None:
                if is_offensive:
                    # Offensive: is_flagged=True OR label in (OFFENSIVE, HATE)
                    statement = statement.where(
                        (TranscriptionModel.is_flagged == True) |
                        (TranscriptionModel.moderation_label.in_(["OFFENSIVE", "HATE"]))
                    )
                else:
                    # Clean: is_flagged=False OR NULL, and label=CLEAN or NULL
                    statement = statement.where(
                        ((TranscriptionModel.is_flagged == False) | (TranscriptionModel.is_flagged.is_(None))) &
                        ((TranscriptionModel.moderation_label == "CLEAN") | (TranscriptionModel.moderation_label.is_(None)))
                    )
            
            if start_date is not None:
                statement = statement.where(TranscriptionModel.created_at >= start_date)
            
            if end_date is not None:
                statement = statement.where(TranscriptionModel.created_at <= end_date)
            
            # Order and paginate
            statement = (
                statement
                .order_by(TranscriptionModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            result = await self._session.execute(statement)
            models = result.scalars().all()
            
            return [self._to_entity(model) for model in models]
            
        except Exception as e:
            logger.error(f"Failed to find transcriptions with filters: {e}")
            raise RepositoryError(
                f"Failed to find transcriptions with filters: {e}"
            ) from e
    
    async def count(
        self,
        model_id: Optional[str] = None,
        is_offensive: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Count transcriptions with optional filters.
        
        Args:
            model_id: Filter by model ID
            is_offensive: Filter by offensive status
            start_date: Filter by creation date (from)
            end_date: Filter by creation date (to)
        
        Returns:
            Total count of matching transcriptions
        
        Raises:
            RepositoryError: If query fails
        """
        try:
            statement = select(func.count(TranscriptionModel.id))
            
            # Apply same filters as find_all
            if model_id is not None:
                statement = statement.where(TranscriptionModel.model_id == model_id)
            
            if is_offensive is not None:
                if is_offensive:
                    statement = statement.where(
                        (TranscriptionModel.is_flagged == True) |
                        (TranscriptionModel.moderation_label.in_(["OFFENSIVE", "HATE"]))
                    )
                else:
                    statement = statement.where(
                        ((TranscriptionModel.is_flagged == False) | (TranscriptionModel.is_flagged.is_(None))) &
                        ((TranscriptionModel.moderation_label == "CLEAN") | (TranscriptionModel.moderation_label.is_(None)))
                    )
            
            if start_date is not None:
                statement = statement.where(TranscriptionModel.created_at >= start_date)
            
            if end_date is not None:
                statement = statement.where(TranscriptionModel.created_at <= end_date)
            
            result = await self._session.execute(statement)
            count = result.scalar_one()
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to count transcriptions: {e}")
            raise RepositoryError(f"Failed to count transcriptions: {e}") from e
    
    async def delete(self, transcription_id: int) -> bool:
        """
        Delete transcription by ID.
        
        Args:
            transcription_id: Unique transcription ID
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            # Find the record first
            model = await self._session.get(TranscriptionModel, transcription_id)
            
            if model is None:
                return False
            
            # Delete and commit
            await self._session.delete(model)
            await self._session.commit()
            
            logger.debug(f"Deleted transcription: id={transcription_id}")
            
            return True
            
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete transcription id={transcription_id}: {e}")
            raise RepositoryError(
                f"Failed to delete transcription id={transcription_id}: {e}"
            ) from e
    
    async def delete_by_session_id(self, session_id: str) -> int:
        """
        Delete all transcriptions for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Number of transcriptions deleted
        
        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            statement = sql_delete(TranscriptionModel).where(
                TranscriptionModel.session_id == session_id
            )
            
            result = await self._session.execute(statement)
            await self._session.commit()
            
            deleted_count = result.rowcount
            
            logger.debug(
                f"Deleted {deleted_count} transcriptions for session_id={session_id}"
            )
            
            return deleted_count
            
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to delete transcriptions for session_id={session_id}: {e}"
            )
            raise RepositoryError(
                f"Failed to delete transcriptions for session_id={session_id}: {e}"
            ) from e
    
    async def delete_old(self, days: int = 30) -> int:
        """
        Delete transcriptions older than specified days.
        
        Args:
            days: Number of days to keep (default: 30)
        
        Returns:
            Number of transcriptions deleted
        
        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            statement = sql_delete(TranscriptionModel).where(
                TranscriptionModel.created_at < cutoff_date
            )
            
            result = await self._session.execute(statement)
            await self._session.commit()
            
            deleted_count = result.rowcount
            
            logger.info(
                f"Deleted {deleted_count} transcriptions older than {days} days"
            )
            
            return deleted_count
            
        except Exception as e:
            await self._session.rollback()
            logger.error(f"Failed to delete old transcriptions: {e}")
            raise RepositoryError(f"Failed to delete old transcriptions: {e}") from e
    
    def _to_entity(self, model: TranscriptionModel) -> Transcription:
        """
        Convert SQLModel model to domain entity.
        
        Args:
            model: TranscriptionModel instance
        
        Returns:
            Transcription domain entity
        """
        return Transcription(
            id=model.id,
            session_id=model.session_id,
            model_id=model.model_id,
            content=model.content,
            latency_ms=model.latency_ms,
            created_at=model.created_at,
            moderation_label=model.moderation_label,
            moderation_confidence=model.moderation_confidence,
            is_flagged=model.is_flagged,
            detected_keywords=model.detected_keywords or [],
        )
    
    def _to_model(self, entity: Transcription) -> TranscriptionModel:
        """
        Convert domain entity to SQLModel model.
        
        Args:
            entity: Transcription domain entity
        
        Returns:
            TranscriptionModel instance
        """
        return TranscriptionModel(
            id=entity.id,
            session_id=entity.session_id,
            model_id=entity.model_id,
            content=entity.content,
            latency_ms=entity.latency_ms,
            created_at=entity.created_at,
            moderation_label=entity.moderation_label,
            moderation_confidence=entity.moderation_confidence,
            is_flagged=entity.is_flagged,
            detected_keywords=entity.detected_keywords if entity.detected_keywords else None,
        )
