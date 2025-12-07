"""Transcription repository interface."""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from app.domain.entities.transcription import Transcription


class ITranscriptionRepository(ABC):
    """
    Abstract repository interface for transcription data access.
    
    Defines all operations for persisting and retrieving transcriptions.
    Implementations handle the actual data storage (SQLite, PostgreSQL, etc.).
    """
    
    @abstractmethod
    async def save(self, transcription: Transcription) -> Transcription:
        """
        Save a transcription entity to storage.
        
        Args:
            transcription: Transcription entity to save
        
        Returns:
            Saved transcription with generated ID
        
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
