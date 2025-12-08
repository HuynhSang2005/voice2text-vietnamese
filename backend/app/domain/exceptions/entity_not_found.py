"""Entity not found exception."""

from typing import Optional

from app.domain.exceptions.base import DomainException


class EntityNotFoundException(DomainException):
    """
    Exception raised when an entity cannot be found in storage.

    Typically raised by repository implementations when a query
    for a specific entity by ID returns no results.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        details: Optional[dict] = None,
    ):
        """
        Initialize entity not found exception.

        Args:
            entity_type: Type/name of entity (e.g., "Transcription", "Session")
            entity_id: Identifier of the missing entity
            details: Optional additional context
        """
        message = f"{entity_type} with ID '{entity_id}' not found"
        super().__init__(message, details)
        self.entity_type = entity_type
        self.entity_id = entity_id
