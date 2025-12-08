"""
OpenAPI Response Examples

This module contains reusable OpenAPI response examples for common HTTP status codes.
These examples are used across all API endpoints to ensure consistent documentation.

Following OpenAPI 3.0 specification for response examples.
"""

from typing import Dict, Any

# ============================================================================
# Common Error Responses
# ============================================================================

RESPONSE_400_VALIDATION_ERROR: Dict[str, Any] = {
    "description": "Validation Error - Invalid request data",
    "content": {
        "application/json": {
            "examples": {
                "missing_required_field": {
                    "summary": "Missing required field",
                    "value": {
                        "type": "https://api.example.com/problems/validation-error",
                        "title": "Validation Error",
                        "status": 400,
                        "detail": "Field 'model' is required",
                        "instance": "/api/v1/models/switch",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "validation_errors": [
                            {
                                "field": "model",
                                "message": "Field required",
                                "type": "missing",
                            }
                        ],
                    },
                },
                "invalid_format": {
                    "summary": "Invalid data format",
                    "value": {
                        "type": "https://api.example.com/problems/validation-error",
                        "title": "Validation Error",
                        "status": 400,
                        "detail": "Invalid audio format",
                        "instance": "/api/v1/transcription",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "validation_errors": [
                            {
                                "field": "format",
                                "message": "Must be one of: wav, mp3, flac",
                                "type": "value_error",
                            }
                        ],
                    },
                },
            }
        }
    },
}

RESPONSE_404_NOT_FOUND: Dict[str, Any] = {
    "description": "Resource Not Found",
    "content": {
        "application/json": {
            "examples": {
                "transcription_not_found": {
                    "summary": "Transcription record not found",
                    "value": {
                        "type": "https://api.example.com/problems/entity-not-found",
                        "title": "Entity Not Found",
                        "status": 404,
                        "detail": "Transcription with ID 123 not found",
                        "instance": "/api/v1/history/123",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "entity_type": "transcription",
                        "entity_id": "123",
                    },
                },
                "model_not_found": {
                    "summary": "Model not found",
                    "value": {
                        "type": "https://api.example.com/problems/entity-not-found",
                        "title": "Entity Not Found",
                        "status": 404,
                        "detail": "Model 'unknown-model' not found",
                        "instance": "/api/v1/models/switch",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "entity_type": "model",
                        "entity_id": "unknown-model",
                    },
                },
            }
        }
    },
}

RESPONSE_422_BUSINESS_RULE_VIOLATION: Dict[str, Any] = {
    "description": "Business Rule Violation - Request is valid but violates business logic",
    "content": {
        "application/json": {
            "examples": {
                "model_not_ready": {
                    "summary": "Model not ready for use",
                    "value": {
                        "type": "https://api.example.com/problems/business-rule-violation",
                        "title": "Business Rule Violation",
                        "status": 422,
                        "detail": "Model is currently loading and not ready for transcription",
                        "instance": "/api/v1/transcription",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "rule": "model_ready",
                        "reason": "Model is still initializing",
                    },
                },
                "worker_unavailable": {
                    "summary": "Worker service unavailable",
                    "value": {
                        "type": "https://api.example.com/problems/business-rule-violation",
                        "title": "Business Rule Violation",
                        "status": 422,
                        "detail": "Transcription worker is not available",
                        "instance": "/ws/transcribe",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "rule": "worker_available",
                        "reason": "Worker process crashed",
                    },
                },
            }
        }
    },
}

RESPONSE_500_INTERNAL_ERROR: Dict[str, Any] = {
    "description": "Internal Server Error",
    "content": {
        "application/json": {
            "examples": {
                "generic_error": {
                    "summary": "Unexpected internal error",
                    "value": {
                        "type": "https://api.example.com/problems/internal-server-error",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "An unexpected error occurred. Please try again later.",
                        "instance": "/api/v1/transcription",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                    },
                }
            }
        }
    },
}

RESPONSE_429_RATE_LIMIT_EXCEEDED: Dict[str, Any] = {
    "description": "Rate Limit Exceeded - Too Many Requests",
    "content": {
        "application/json": {
            "examples": {
                "rate_limit_exceeded": {
                    "summary": "Rate limit exceeded",
                    "value": {
                        "type": "https://api.example.com/problems/rate-limit-exceeded",
                        "title": "Rate Limit Exceeded",
                        "status": 429,
                        "detail": "Too many requests. Please try again later.",
                        "instance": "/api/v1/transcribe",
                        "timestamp": "2025-12-08T12:00:00Z",
                        "request_id": "abc-123-def-456",
                        "retry_after": 60,
                        "limit": 60,
                        "window": "1 minute",
                    },
                },
                "websocket_connection_limit": {
                    "summary": "WebSocket connection limit exceeded",
                    "value": {
                        "type": "https://api.example.com/problems/rate-limit-exceeded",
                        "title": "Connection Limit Exceeded",
                        "status": 429,
                        "detail": "Too many concurrent WebSocket connections. Maximum 10 connections per minute allowed.",
                        "instance": "/ws/transcribe",
                        "timestamp": "2025-12-08T12:00:00Z",
                        "request_id": "abc-123-def-456",
                        "retry_after": 60,
                        "limit": 10,
                        "window": "1 minute",
                        "connection_type": "websocket",
                    },
                },
            }
        }
    },
    "headers": {
        "X-RateLimit-Limit": {
            "description": "Maximum requests allowed per time window",
            "schema": {"type": "integer"},
            "example": 60,
        },
        "X-RateLimit-Remaining": {
            "description": "Remaining requests in current window",
            "schema": {"type": "integer"},
            "example": 0,
        },
        "X-RateLimit-Reset": {
            "description": "Unix timestamp when the rate limit resets",
            "schema": {"type": "integer"},
            "example": 1733659260,
        },
        "Retry-After": {
            "description": "Seconds to wait before retrying",
            "schema": {"type": "integer"},
            "example": 60,
        },
    },
}

RESPONSE_503_SERVICE_UNAVAILABLE: Dict[str, Any] = {
    "description": "Service Unavailable - Service is temporarily unavailable",
    "content": {
        "application/json": {
            "examples": {
                "database_down": {
                    "summary": "Database connection failed",
                    "value": {
                        "type": "https://api.example.com/problems/service-unavailable",
                        "title": "Service Unavailable",
                        "status": 503,
                        "detail": "Database is currently unavailable",
                        "instance": "/api/v1/history",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "retry_after": 30,
                    },
                },
                "model_loading": {
                    "summary": "Model is loading",
                    "value": {
                        "type": "https://api.example.com/problems/service-unavailable",
                        "title": "Service Unavailable",
                        "status": 503,
                        "detail": "Transcription service is initializing. Please wait.",
                        "instance": "/api/v1/transcription",
                        "timestamp": "2025-12-08T10:30:00Z",
                        "request_id": "abc-123-def-456",
                        "retry_after": 10,
                    },
                },
            }
        }
    },
}

# ============================================================================
# Success Response Helpers
# ============================================================================


def create_success_response(
    description: str, examples: Dict[str, Dict[str, Any]], status_code: int = 200
) -> Dict[str, Any]:
    """
    Create a success response with examples for OpenAPI documentation.

    Args:
        description: Response description
        examples: Dictionary of example name -> example data
        status_code: HTTP status code (default: 200)

    Returns:
        OpenAPI response object
    """
    return {
        "description": description,
        "content": {"application/json": {"examples": examples}},
    }


# ============================================================================
# Common Response Combinations
# ============================================================================

COMMON_RESPONSES: Dict[int, Dict[str, Any]] = {
    400: RESPONSE_400_VALIDATION_ERROR,
    404: RESPONSE_404_NOT_FOUND,
    422: RESPONSE_422_BUSINESS_RULE_VIOLATION,
    429: RESPONSE_429_RATE_LIMIT_EXCEEDED,
    500: RESPONSE_500_INTERNAL_ERROR,
    503: RESPONSE_503_SERVICE_UNAVAILABLE,
}


def get_responses(*status_codes: int) -> Dict[int, Dict[str, Any]]:
    """
    Get common responses for specified status codes.

    Args:
        *status_codes: HTTP status codes to include

    Returns:
        Dictionary of status code -> response object

    Example:
        ```python
        @router.get(
            "/example",
            responses=get_responses(400, 404, 500)
        )
        ```
    """
    return {
        code: COMMON_RESPONSES[code]
        for code in status_codes
        if code in COMMON_RESPONSES
    }
