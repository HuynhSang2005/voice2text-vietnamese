"""Base domain exception."""


class DomainException(Exception):
    """
    Base exception for all domain layer errors.

    All domain-specific exceptions should inherit from this class.
    """

    def __init__(self, message: str, details: dict = None):
        """
        Initialize domain exception.

        Args:
            message: Human-readable error message
            details: Optional dict with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"
