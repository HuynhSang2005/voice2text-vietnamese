"""
API Middleware - Request/Response Processing

This module exports middleware components for request/response processing:
- cors: CORS configuration with security validation
- error_handler: RFC 7807 compliant error handling
- logging: Structured logging with request tracing
"""

from app.api.middleware.cors import (
    configure_cors,
    get_allowed_origins,
    validate_cors_config,
)
from app.api.middleware.error_handler import (
    configure_error_handlers,
    ProblemDetails,
)
from app.api.middleware.logging import (
    StructuredLoggingMiddleware,
    configure_logging,
    get_request_id,
    get_performance_metrics,
)

__all__ = [
    # CORS
    "configure_cors",
    "get_allowed_origins",
    "validate_cors_config",
    # Error handling
    "configure_error_handlers",
    "ProblemDetails",
    # Logging
    "StructuredLoggingMiddleware",
    "configure_logging",
    "get_request_id",
    "get_performance_metrics",
]
