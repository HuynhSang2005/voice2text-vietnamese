"""Domain exceptions - Business rule violations."""
from app.domain.exceptions.base import DomainException
from app.domain.exceptions.entity_not_found import EntityNotFoundException
from app.domain.exceptions.validation import (
    ValidationException,
    MultipleValidationException,
)
from app.domain.exceptions.business_rule import BusinessRuleViolationException

__all__ = [
    "DomainException",
    "EntityNotFoundException",
    "ValidationException",
    "MultipleValidationException",
    "BusinessRuleViolationException",
]
