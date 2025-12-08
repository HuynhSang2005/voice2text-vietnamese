"""
Presentation Layer - RFC 7807 Error Handler Middleware

This module implements RFC 7807 (Problem Details for HTTP APIs) compliant
error handling for the FastAPI application.

RFC 7807 Standard: https://tools.ietf.org/html/rfc7807

Key Features:
- Standardized error response format
- Domain exception to HTTP status mapping
- Detailed error information for debugging
- Security-conscious error messages (no internal details leaked)

Response Format:
{
    "type": "https://example.com/probs/out-of-credit",
    "title": "You do not have enough credit",
    "status": 403,
    "detail": "Your current balance is 30, but that costs 50",
    "instance": "/account/12345/transactions/abc"
}

Following Clean Architecture:
- Maps domain exceptions to HTTP status codes
- Presentation layer concern (HTTP protocol)
- Hides internal implementation details from clients
"""

import logging
import traceback
from typing import Dict
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import (
    DomainException,
    ValidationException,
    BusinessRuleViolationException,
    EntityNotFoundException,  # Changed from ResourceNotFoundException
)
from app.core.config import settings


logger = logging.getLogger(__name__)


# RFC 7807 Problem Details Type
class ProblemDetails:
    """
    RFC 7807 Problem Details structure.

    Attributes:
        type: URI reference identifying the problem type
        title: Short, human-readable summary
        status: HTTP status code
        detail: Human-readable explanation specific to this occurrence
        instance: URI reference identifying this specific occurrence
    """

    def __init__(
        self, type: str, title: str, status: int, detail: str, instance: str, **kwargs
    ):
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance
        self.extensions = kwargs  # Additional members

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response."""
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
        }
        # Add extension members
        result.update(self.extensions)
        return result


# Exception to HTTP Status Mapping
EXCEPTION_STATUS_MAP: Dict[type, int] = {
    ValidationException: status.HTTP_400_BAD_REQUEST,
    BusinessRuleViolationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    EntityNotFoundException: status.HTTP_404_NOT_FOUND,
}


# Problem Type URIs (can be actual URLs to documentation)
PROBLEM_TYPE_BASE = f"{settings.API_BASE_URL}/problems"


def get_problem_type_uri(exception: Exception) -> str:
    """
    Get RFC 7807 problem type URI for an exception.

    Args:
        exception: The exception to map

    Returns:
        URI identifying the problem type

    Example:
        >>> get_problem_type_uri(ValidationException("Invalid input"))
        "https://api.example.com/problems/validation-error"
    """
    exception_name = type(exception).__name__
    # Convert CamelCase to kebab-case
    problem_type = "".join(
        ["-" + c.lower() if c.isupper() else c for c in exception_name]
    ).lstrip("-")

    return f"{PROBLEM_TYPE_BASE}/{problem_type}"


def get_status_code(exception: Exception) -> int:
    """
    Get HTTP status code for an exception.

    Args:
        exception: The exception to map

    Returns:
        HTTP status code
    """
    # Check explicit mapping first
    for exc_type, status_code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exception, exc_type):
            return status_code

    # Default to 500 for unmapped exceptions
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def create_problem_details(
    exception: Exception, request: Request, include_traceback: bool = False
) -> ProblemDetails:
    """
    Create RFC 7807 Problem Details from an exception.

    Args:
        exception: The exception that occurred
        request: FastAPI request object
        include_traceback: Whether to include traceback (dev only)

    Returns:
        ProblemDetails object
    """
    status_code = get_status_code(exception)
    problem_type = get_problem_type_uri(exception)

    # Get title from exception type
    title = type(exception).__name__.replace("Exception", "").replace("_", " ").title()

    # Get detail from exception message
    detail = str(exception)

    # Get instance (request path)
    instance = str(request.url.path)

    # Extension members
    extensions = {
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Add request ID if available
    if hasattr(request.state, "request_id"):
        extensions["request_id"] = request.state.request_id

    # Add traceback in development (security: never in production)
    if include_traceback and settings.ENVIRONMENT == "development":
        extensions["traceback"] = traceback.format_exc()

    # Add domain-specific details for domain exceptions
    if isinstance(exception, BusinessRuleViolationException):
        extensions["rule"] = exception.rule
        extensions["reason"] = exception.reason

    if isinstance(exception, EntityNotFoundException):
        extensions["entity_type"] = getattr(exception, "entity_type", "entity")
        extensions["entity_id"] = getattr(exception, "entity_id", None)

    return ProblemDetails(
        type=problem_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
        **extensions,
    )


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """
    Handle domain exceptions with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: Domain exception

    Returns:
        JSONResponse with problem details
    """
    problem = create_problem_details(
        exception=exc,
        request=request,
        include_traceback=False,  # Never include traceback for domain exceptions
    )

    # Log exception
    logger.warning(
        f"Domain exception: {type(exc).__name__} - {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "status_code": problem.status,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=problem.status,
        content=problem.to_dict(),
        headers={"Content-Type": "application/problem+json"},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: Validation error from Pydantic

    Returns:
        JSONResponse with problem details
    """
    # Extract validation errors
    errors = exc.errors()

    problem = ProblemDetails(
        type=f"{PROBLEM_TYPE_BASE}/validation-error",
        title="Request Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="The request contains invalid parameters",
        instance=str(request.url.path),
        errors=errors,  # Extension: validation error details
        timestamp=datetime.utcnow().isoformat(),
    )

    logger.warning(
        f"Validation error: {len(errors)} errors in {request.url.path}",
        extra={"errors": errors},
    )

    return JSONResponse(
        status_code=problem.status,
        content=problem.to_dict(),
        headers={"Content-Type": "application/problem+json"},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: HTTP exception from Starlette

    Returns:
        JSONResponse with problem details
    """
    problem = ProblemDetails(
        type=f"{PROBLEM_TYPE_BASE}/http-error",
        title=f"HTTP {exc.status_code}",
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        timestamp=datetime.utcnow().isoformat(),
    )

    logger.info(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"status_code": exc.status_code, "path": request.url.path},
    )

    return JSONResponse(
        status_code=problem.status,
        content=problem.to_dict(),
        headers={"Content-Type": "application/problem+json"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with RFC 7807 format.

    Args:
        request: FastAPI request
        exc: Any unhandled exception

    Returns:
        JSONResponse with generic error (hides internal details)
    """
    # Log full exception with traceback
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {exc}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
        },
    )

    # Create generic problem details (security: don't expose internal errors)
    problem = ProblemDetails(
        type=f"{PROBLEM_TYPE_BASE}/internal-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later.",
        instance=str(request.url.path),
        timestamp=datetime.utcnow().isoformat(),
    )

    # Add request ID if available (for support/debugging)
    if hasattr(request.state, "request_id"):
        problem.extensions["request_id"] = request.state.request_id

    # Include exception details ONLY in development
    if settings.ENVIRONMENT == "development":
        problem.extensions["error"] = str(exc)
        problem.extensions["error_type"] = type(exc).__name__
        problem.extensions["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=problem.status,
        content=problem.to_dict(),
        headers={"Content-Type": "application/problem+json"},
    )


def configure_error_handlers(app) -> None:
    """
    Configure RFC 7807 error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance

    Registers handlers for:
        - Domain exceptions (ValidationException, BusinessRuleViolationException, etc.)
        - Pydantic validation errors
        - HTTP exceptions
        - Generic unexpected exceptions

    Example:
        ```python
        from fastapi import FastAPI
        from app.api.middleware.error_handler import configure_error_handlers

        app = FastAPI()
        configure_error_handlers(app)
        ```
    """
    # Domain exceptions
    app.add_exception_handler(DomainException, domain_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Configured RFC 7807 error handlers")
