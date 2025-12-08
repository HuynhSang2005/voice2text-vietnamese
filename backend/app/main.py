"""
FastAPI Application Entry Point - Clean Architecture

This module initializes the FastAPI application with Clean Architecture principles:
- Dependency Injection (DI) container setup
- Middleware configuration (CORS, Logging, Error Handling)
- Route registration (Health, Models, History, Moderation, WebSocket)
- Lifespan management (startup/shutdown)
- OpenAPI customization

Architecture:
- Presentation Layer: API routes and WebSocket endpoints
- Application Layer: Use cases and business logic
- Infrastructure Layer: Database, workers, cache
- Domain Layer: Business entities and rules
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.infrastructure.config.container import Container

# Import middleware configuration functions
from app.api.middleware.cors import configure_cors, validate_cors_config
from app.api.middleware.error_handler import configure_error_handlers
from app.api.middleware.logging import (
    StructuredLoggingMiddleware,
    configure_logging,
)

# Import routers
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.api.routes.history import router as history_router
from app.api.routes.moderation import router as moderation_router
from app.api.websockets.transcription import router as websocket_router

# Configure logging
configure_logging(log_level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager for startup and shutdown.

    Startup:
    - Initialize database tables
    - Wire DI container to modules
    - Start worker manager
    - Preload models (background)
    - Validate CORS configuration

    Shutdown:
    - Stop worker manager
    - Close database connections
    - Cleanup resources
    """
    logger.info(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}...")

    # Startup phase
    try:
        # 1. Initialize database
        logger.info("📊 Initializing database...")
        await create_db_and_tables()

        # 2. Wire DI container
        logger.info("🔌 Wiring dependency injection container...")
        container = Container()
        container.config.from_dict(
            {
                "database_url": settings.DATABASE_URL,
                "redis_url": settings.REDIS_URL,
                "zipformer_model_path": str(settings.ZIPFORMER_MODEL_PATH),
                "span_detector_model_path": str(settings.SPAN_DETECTOR_MODEL_PATH),
            }
        )

        # Wire container to application modules
        container.wire(
            modules=[
                "app.api.deps",
                "app.api.routes.health",
                "app.api.routes.models",
                "app.api.routes.history",
                "app.api.routes.moderation",
                "app.api.websockets.transcription",
            ]
        )

        # Store container in app state for access in dependencies
        app.state.container = container

        # 3. Start worker manager
        logger.info("⚙️ Starting worker manager...")
        worker_manager = container.worker_manager()
        worker_manager.start_all()

        # 4. Preload models in background (non-blocking)
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, worker_manager.preload_all_models)

        # 5. Validate CORS configuration
        if not validate_cors_config():
            logger.warning("⚠️ CORS configuration validation failed - check logs")

        logger.info("✅ Application started successfully")
        logger.info(f"📡 API available at: http://{settings.HOST}:{settings.PORT}")
        logger.info(
            f"📚 Docs available at: http://{settings.HOST}:{settings.PORT}/docs"
        )

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise

    # Application is running
    yield

    # Shutdown phase
    logger.info("🛑 Shutting down application...")

    try:
        # Stop worker manager
        if hasattr(app.state, "container"):
            worker_manager = app.state.container.worker_manager()
            worker_manager.stop_all()
            logger.info("⚙️ Worker manager stopped")

        # Unwire container
        if hasattr(app.state, "container"):
            app.state.container.unwire()
            logger.info("🔌 DI container unwired")

        logger.info("✅ Application shutdown complete")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}", exc_info=True)


def create_application() -> FastAPI:
    """
    Factory function to create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    )

    # 1. Configure CORS middleware (must be first)
    configure_cors(app)

    # 2. Add structured logging middleware
    app.add_middleware(
        StructuredLoggingMiddleware,
        exclude_paths=[
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
    )

    # 3. Configure error handlers (domain, validation, HTTP, generic)
    configure_error_handlers(app)

    # 4. Include routers (order matters for matching)
    # Health check routes (no prefix)
    app.include_router(health_router)

    # API v1 routes
    app.include_router(models_router)
    app.include_router(history_router)
    app.include_router(moderation_router)

    # WebSocket routes
    app.include_router(websocket_router)

    # 5. Customize OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    return app


def custom_openapi(app: FastAPI):
    """
    Generate custom OpenAPI schema with simplified operation IDs.

    This function:
    - Uses function names as operation IDs for cleaner client generation
    - Sets server URL for frontend client generation
    - Caches the schema to avoid regeneration

    Args:
        app: FastAPI application instance

    Returns:
        dict: OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Simplify operation IDs
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name

    # Generate OpenAPI schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        routes=app.routes,
    )

    # Set server URL for client generation
    openapi_schema["servers"] = [
        {
            "url": f"http://{settings.HOST}:{settings.PORT}",
            "description": "Development server",
        },
        {
            "url": "https://api.voice2text.example.com",
            "description": "Production server (future)",
        },
    ]

    # Add security schemes (placeholder for future auth)
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication (future implementation). Include your API key in the X-API-Key header.",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT bearer token authentication (future implementation). Include your JWT token in the Authorization header as 'Bearer <token>'.",
        },
    }

    # Add rate limiting information to OpenAPI schema
    if "info" not in openapi_schema:
        openapi_schema["info"] = {}

    # Add rate limiting documentation in schema description
    rate_limit_info = """

## Rate Limiting

This API implements rate limiting to ensure fair usage and service stability.

### Rate Limit Headers

All responses include the following rate limit headers:

- `X-RateLimit-Limit`: Maximum requests allowed per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets

### Rate Limit Policies

| Endpoint Type | Rate Limit | Window |
|--------------|------------|--------|
| Authentication | 10 requests | 1 minute |
| Transcription (REST) | 60 requests | 1 minute |
| Transcription (WebSocket) | 10 connections | 1 minute |
| History & Models | 100 requests | 1 minute |
| Health Checks | Unlimited | - |

### Rate Limit Exceeded Response

When rate limit is exceeded, the API returns a `429 Too Many Requests` response:

```json
{
  "type": "https://api.voice2text.example.com/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Please try again later.",
  "instance": "/api/v1/transcribe",
  "timestamp": "2024-12-08T12:00:00Z",
  "request_id": "abc-123-def-456",
  "retry_after": 60
}
```

**Note**: Rate limiting is planned for future implementation. Current version does not enforce limits.
"""

    openapi_schema["info"]["description"] = (
        openapi_schema["info"].get("description", "") + rate_limit_info
    )

    # Cache schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Create application instance
app = create_application()


# Root endpoint (for backward compatibility)
@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    """
    Root endpoint - redirects to API documentation.

    Returns:
        dict: Welcome message with links
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": f"http://{settings.HOST}:{settings.PORT}/docs",
        "health": f"http://{settings.HOST}:{settings.PORT}/health",
    }


if __name__ == "__main__":
    # For development: run with `python -m app.main`
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
