"""
Health Check Routes

Provides health check and readiness endpoints for monitoring and orchestration.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, status

from app.api.deps import get_di_container
from app.infrastructure.config.container import Container
from app.application.dtos.responses import HealthCheckResponse
from app.core.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Check the health status of the application and its dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "checks": {
                            "database": "healthy",
                            "transcription_worker": "healthy",
                            "moderation_worker": "healthy",
                            "cache": "healthy",
                        },
                    }
                }
            },
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "checks": {
                            "database": "unhealthy",
                            "transcription_worker": "healthy",
                            "moderation_worker": "unhealthy",
                            "cache": "disabled",
                        },
                    }
                }
            },
        },
    },
)
async def health_check(
    container: Container = Depends(get_di_container),
) -> HealthCheckResponse:
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connectivity
    - Transcription worker status
    - Moderation worker status
    - Redis cache status (if enabled)

    Returns:
        HealthCheckResponse: Overall health status with individual component checks

    Status Codes:
        - 200: All components healthy
        - 503: One or more components unhealthy
    """
    checks: Dict[str, str] = {}
    overall_healthy = True

    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"
        overall_healthy = False

    # Check transcription worker
    try:
        transcription_worker = container.transcription_worker()

        if await transcription_worker.is_ready():
            checks["transcription_worker"] = "healthy"
        else:
            checks["transcription_worker"] = "not_ready"
            overall_healthy = False
    except Exception as e:
        logger.error(f"Transcription worker health check failed: {e}")
        checks["transcription_worker"] = "unhealthy"
        overall_healthy = False

    # Check moderation worker
    try:
        moderation_worker = container.moderation_worker()

        if await moderation_worker.is_ready():
            checks["moderation_worker"] = "healthy"
        else:
            checks["moderation_worker"] = "not_ready"
            overall_healthy = False
    except Exception as e:
        logger.error(f"Moderation worker health check failed: {e}")
        checks["moderation_worker"] = "unhealthy"
        overall_healthy = False

    # Check Redis cache (if enabled)
    try:
        cache = container.cache()
        if cache is not None:
            # Simple cache test
            test_key = "_health_check"
            await cache.set(test_key, "ok", ttl=1)
            result = await cache.get(test_key)

            if result == "ok":
                checks["cache"] = "healthy"
            else:
                checks["cache"] = "unhealthy"
                overall_healthy = False
        else:
            checks["cache"] = "disabled"
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks["cache"] = "unhealthy"
        overall_healthy = False

    response_status = "healthy" if overall_healthy else "unhealthy"

    return HealthCheckResponse(status=response_status, checks=checks)


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Check if the application is ready to accept requests (for Kubernetes)",
    responses={
        200: {
            "description": "Application is ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": True,
                        "message": "Application is ready to accept requests",
                    }
                }
            },
        },
        503: {
            "description": "Application is not ready",
            "content": {
                "application/json": {
                    "example": {"ready": False, "message": "Workers are initializing"}
                }
            },
        },
    },
)
async def readiness_probe(
    container: Container = Depends(get_di_container),
) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.

    Checks if the application is ready to accept traffic.
    This is a lighter check than /health, focusing on critical components.

    Returns:
        dict: Readiness status

    Status Codes:
        - 200: Application ready
        - 503: Application not ready
    """
    try:
        # Check database connectivity
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")

        # Check if at least one worker is ready
        transcription_worker = container.transcription_worker()

        if not await transcription_worker.is_ready():
            return {"ready": False, "message": "Transcription worker is not ready"}

        return {"ready": True, "message": "Application is ready to accept requests"}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False, "message": f"Readiness check failed: {str(e)}"}
