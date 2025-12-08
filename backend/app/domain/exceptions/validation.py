"""Validation exception."""

from typing import Optional, List

from app.domain.exceptions.base import DomainException


class ValidationException(DomainException):
    """
    Exception raised when entity or value object validation fails.

    Indicates that data does not meet domain constraints
    (e.g., invalid confidence score range, unsupported audio format).
    """

    def __init__(
        self,
        field: str,
        value: any,
        constraint: str,
        details: Optional[dict] = None,
    ):
        """
        Initialize validation exception.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            constraint: Description of the constraint that was violated
            details: Optional additional context
        """
        message = (
            f"Validation failed for field '{field}': {constraint}. Got value: {value}"
        )
        super().__init__(message, details)
        self.field = field
        self.value = value
        self.constraint = constraint


class MultipleValidationException(DomainException):
    """
    Exception raised when multiple validation errors occur.

    Aggregates multiple validation failures for batch processing.
    """

    def __init__(
        self,
        errors: List[ValidationException],
        details: Optional[dict] = None,
    ):
        """
        Initialize multiple validation exception.

        Args:
            errors: List of validation exceptions
            details: Optional additional context
        """
        error_messages = [str(err) for err in errors]
        message = f"Multiple validation errors: {'; '.join(error_messages)}"
        super().__init__(message, details)
        self.errors = errors

    def __len__(self) -> int:
        return len(self.errors)
