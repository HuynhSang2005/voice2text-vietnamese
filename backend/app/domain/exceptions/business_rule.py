"""Business rule violation exception."""
from typing import Optional

from app.domain.exceptions.base import DomainException


class BusinessRuleViolationException(DomainException):
    """
    Exception raised when a business rule is violated.
    
    Indicates that an operation cannot proceed because it would
    violate domain business logic (e.g., extending an expired session,
    processing audio with zero duration).
    """
    
    def __init__(
        self,
        rule: str,
        reason: str,
        details: Optional[dict] = None,
    ):
        """
        Initialize business rule violation exception.
        
        Args:
            rule: Name or description of the business rule
            reason: Explanation of why the rule was violated
            details: Optional additional context
        """
        message = f"Business rule violation: {rule}. Reason: {reason}"
        super().__init__(message, details)
        self.rule = rule
        self.reason = reason
