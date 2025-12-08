"""Repository layer exceptions."""

from app.domain.exceptions.base import DomainException


class RepositoryError(DomainException):
    """
    Base exception for repository layer errors.

    Raised when database operations fail or data access issues occur.
    """

    pass


class EntityNotFoundError(RepositoryError):
    """
    Exception raised when a requested entity is not found.

    Example:
        >>> raise EntityNotFoundError("Transcription with id=123 not found")
    """

    pass


class DuplicateEntityError(RepositoryError):
    """
    Exception raised when attempting to create an entity that already exists.

    Example:
        >>> raise DuplicateEntityError("Session with id=abc123 already exists")
    """

    pass


class DatabaseConnectionError(RepositoryError):
    """
    Exception raised when database connection fails.

    Example:
        >>> raise DatabaseConnectionError("Cannot connect to database")
    """

    pass


class TransactionError(RepositoryError):
    """
    Exception raised when a database transaction fails.

    Example:
        >>> raise TransactionError("Failed to commit transaction")
    """

    pass
