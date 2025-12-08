"""
Presentation Layer - CORS Middleware

This module configures Cross-Origin Resource Sharing (CORS) for the API
following security best practices and FastAPI patterns.

Key Features:
- Environment-based origin configuration
- Secure defaults for production
- Preflight request handling
- Credentials support for authenticated requests

Security Considerations:
- NEVER use wildcard (*) in production
- Restrict origins to trusted domains
- Enable credentials only when necessary
- Use HTTPS in production

Following Clean Architecture:
- Presentation layer concern (HTTP protocol)
- Configuration externalized to settings
- No business logic dependencies
"""

import logging
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


logger = logging.getLogger(__name__)


def get_allowed_origins() -> List[str]:
    """
    Get list of allowed CORS origins based on environment.

    Returns:
        List of allowed origin URLs

    Environment Variables:
        ALLOWED_ORIGINS: Comma-separated list of origins (e.g., "http://localhost:3000,https://app.example.com")
        ENVIRONMENT: "development", "staging", or "production"

    Example:
        ```python
        # Development
        origins = get_allowed_origins()
        # ["http://localhost:3000", "http://localhost:5173"]

        # Production
        origins = get_allowed_origins()
        # ["https://app.example.com", "https://www.example.com"]
        ```
    """
    # Get origins from settings
    origins_value = settings.ALLOWED_ORIGINS

    # Handle both list and comma-separated string
    if isinstance(origins_value, list):
        origins_list = origins_value
    elif isinstance(origins_value, str):
        if not origins_value or origins_value.strip() == "":
            origins_list = []
        else:
            origins_list = [
                origin.strip() for origin in origins_value.split(",") if origin.strip()
            ]
    else:
        origins_list = []

    if not origins_list:
        # Default to localhost in development
        if settings.ENVIRONMENT == "development":
            default_origins = [
                "http://localhost:3000",  # Frontend dev server
                "http://localhost:5173",  # Vite dev server
                "http://localhost:8000",  # Backend (for testing)
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8000",
            ]
            logger.warning(
                "ALLOWED_ORIGINS not set, using development defaults. "
                "This is NOT secure for production!"
            )
            return default_origins
        else:
            # Production should ALWAYS have explicit origins
            logger.error(
                "ALLOWED_ORIGINS not set in production! "
                "CORS will be restrictive. Set ALLOWED_ORIGINS in .env"
            )
            return []

    # Validate origins (basic check)
    for origin in origins_list:
        if origin == "*":
            if getattr(settings, "ENVIRONMENT", "development") == "production":
                logger.error(
                    "Wildcard (*) CORS origin detected in production! "
                    "This is a SECURITY RISK. Use explicit origins."
                )
                raise ValueError("Wildcard CORS origin not allowed in production")
            else:
                logger.warning(
                    "Wildcard (*) CORS origin detected in development. "
                    "This should NEVER be used in production."
                )

        if not origin.startswith(("http://", "https://", "*")):
            logger.warning(f"Invalid origin format: {origin}")

    logger.info(f"Configured CORS origins: {origins_list}")
    return origins_list


def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.

    This function adds CORS middleware with appropriate settings based on
    the environment. It follows security best practices:
    - Explicit origin list (no wildcards in production)
    - Restricted methods (only necessary HTTP methods)
    - Credentials support for authenticated requests
    - Proper preflight handling

    Args:
        app: FastAPI application instance

    Example:
        ```python
        from fastapi import FastAPI
        from app.api.middleware.cors import configure_cors

        app = FastAPI()
        configure_cors(app)
        ```

    CORS Configuration:
        - allow_origins: List of allowed origins (environment-specific)
        - allow_credentials: True (for cookie-based auth)
        - allow_methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        - allow_headers: ["*"] (allows all headers, can be restricted)
        - expose_headers: ["Content-Length", "X-Request-ID"]
        - max_age: 600 seconds (10 minutes) for preflight caching

    Security Notes:
        - Origins are validated at startup
        - Wildcard (*) blocked in production
        - HTTPS enforced in production (via origin validation)
        - Preflight requests cached for 10 minutes
    """
    origins = get_allowed_origins()

    # Determine if credentials should be allowed
    # Note: If using wildcard origin, credentials MUST be False
    allow_credentials = "*" not in origins

    # Allowed HTTP methods
    # Only include methods actually used by the API
    allowed_methods = [
        "GET",  # Read operations
        "POST",  # Create operations, transcription
        "PUT",  # Update operations
        "DELETE",  # Delete operations
        "PATCH",  # Partial updates
        "OPTIONS",  # Preflight requests
    ]

    # Allowed headers
    # Use ["*"] to allow all headers, or specify explicitly:
    # ["Content-Type", "Authorization", "X-Request-ID"]
    allowed_headers = ["*"]

    # Exposed headers (headers that client can access)
    # These headers are exposed to JavaScript via XMLHttpRequest/fetch
    exposed_headers = [
        "Content-Length",
        "X-Request-ID",  # For request tracking
        "X-RateLimit-Limit",  # Rate limiting info
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ]

    # Preflight cache duration (in seconds)
    # How long browser should cache preflight OPTIONS response
    max_age = 600  # 10 minutes

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
        expose_headers=exposed_headers,
        max_age=max_age,
    )

    logger.info(
        f"CORS middleware configured: "
        f"origins={len(origins)}, "
        f"credentials={allow_credentials}, "
        f"methods={allowed_methods}"
    )

    # Log warning if using permissive settings
    if "*" in origins:
        logger.warning(
            "⚠️  CORS configured with wildcard origin. "
            "This allows requests from ANY domain. "
            "This is OK for development but DANGEROUS in production!"
        )

    if allow_credentials and len(origins) > 10:
        logger.warning(
            f"CORS configured with {len(origins)} origins and credentials enabled. "
            "Consider reducing the number of allowed origins for better security."
        )


# Validation function for deployment checks
def validate_cors_config() -> bool:
    """
    Validate CORS configuration for production readiness.

    Returns:
        True if configuration is secure, False otherwise

    Checks:
        - No wildcard origins in production
        - HTTPS origins in production
        - Reasonable number of allowed origins

    Example:
        ```python
        if not validate_cors_config():
            raise RuntimeError("Insecure CORS configuration detected")
        ```
    """
    if settings.ENVIRONMENT != "production":
        # Skip validation in non-production environments
        return True

    origins = get_allowed_origins()

    # Check for wildcard
    if "*" in origins:
        logger.error("❌ CORS validation failed: Wildcard origin in production")
        return False

    # Check for HTTPS
    http_origins = [o for o in origins if o.startswith("http://")]
    if http_origins:
        logger.error(
            f"❌ CORS validation failed: HTTP origins in production: {http_origins}"
        )
        return False

    # Check number of origins (too many might indicate misconfiguration)
    if len(origins) > 20:
        logger.warning(
            f"⚠️  CORS warning: {len(origins)} origins configured. "
            "This might indicate misconfiguration."
        )

    # Check for localhost/127.0.0.1 in production
    localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
    if localhost_origins:
        logger.error(
            f"❌ CORS validation failed: Localhost origins in production: {localhost_origins}"
        )
        return False

    logger.info("✅ CORS configuration validated successfully")
    return True
