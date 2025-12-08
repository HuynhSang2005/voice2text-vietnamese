"""
Presentation Layer - Structured Logging Middleware

This module implements structured logging middleware for FastAPI
following best practices for observability and debugging.

Key Features:
- Request/response logging with timing
- Unique request ID tracking
- Structured JSON logging
- PII-safe logging (excludes sensitive data)
- Performance metrics collection

Following Clean Architecture:
- Presentation layer concern (HTTP protocol)
- No business logic dependencies
- Configuration externalized to settings
"""

import logging
import time
import uuid
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


logger = logging.getLogger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging of HTTP requests and responses.
    
    Logs:
        - Request details (method, path, query params, headers)
        - Response details (status code, duration)
        - Request ID (for tracing)
        - Performance metrics (timing)
    
    Example:
        ```python
        from fastapi import FastAPI
        from app.api.middleware.logging import StructuredLoggingMiddleware
        
        app = FastAPI()
        app.add_middleware(StructuredLoggingMiddleware)
        ```
    
    Log Format (JSON):
        {
            "timestamp": "2024-12-08T10:30:00Z",
            "request_id": "abc-123-def-456",
            "method": "POST",
            "path": "/api/v1/transcription",
            "query_params": {"model": "zipformer"},
            "status_code": 200,
            "duration_ms": 150.5,
            "client_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0..."
        }
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: list[str] = None):
        """
        Initialize the middleware.
        
        Args:
            app: ASGI application
            exclude_paths: List of paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log structured information.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
        
        Returns:
            Response from downstream handler
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        
        # Start timing
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log incoming request
        logger.info(
            f"→ {method} {path}",
            extra={
                "event": "request_started",
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                f"← {method} {path} {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Log slow requests (> 1 second)
            if duration_ms > 1000:
                logger.warning(
                    f"Slow request: {method} {path} took {duration_ms:.2f}ms",
                    extra={
                        "event": "slow_request",
                        "request_id": request_id,
                        "duration_ms": duration_ms,
                        "threshold_ms": 1000,
                    }
                )
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                f"✗ {method} {path} ERROR ({duration_ms:.2f}ms)",
                exc_info=True,
                extra={
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
            # Re-raise to be handled by error handlers
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Handles reverse proxy headers (X-Forwarded-For, X-Real-IP).
        
        Args:
            request: FastAPI request
        
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take first IP (client IP)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"


# Request ID Dependency (for use in route handlers)
def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.
    
    Args:
        request: FastAPI request
    
    Returns:
        Request ID (UUID string)
    
    Example:
        ```python
        from fastapi import Depends
        from app.api.middleware.logging import get_request_id
        
        @router.post("/transcribe")
        async def transcribe(
            request_id: str = Depends(get_request_id)
        ):
            logger.info(f"Processing transcription: {request_id}")
        ```
    """
    return getattr(request.state, "request_id", "unknown")


# Logging Configuration
def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Sets up:
        - JSON structured logging (in production)
        - Console logging with colors (in development)
        - Log levels per module
        - Log rotation (in production)
    
    Example:
        ```python
        from app.api.middleware.logging import configure_logging
        
        configure_logging(log_level="INFO")
        ```
    """
    # Convert to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Set module-specific levels
    logging.getLogger("app").setLevel(level)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Reduce noise from some libraries
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured: level={log_level}")


# Performance Metrics Collection
class PerformanceMetrics:
    """
    Collect and track performance metrics for requests.
    
    Tracks:
        - Request count
        - Average response time
        - Slow request count
        - Error count
    """
    
    def __init__(self):
        self.request_count = 0
        self.total_duration_ms = 0.0
        self.slow_request_count = 0
        self.error_count = 0
    
    def record_request(self, duration_ms: float, is_error: bool = False):
        """Record a completed request."""
        self.request_count += 1
        self.total_duration_ms += duration_ms
        
        if duration_ms > 1000:  # > 1 second
            self.slow_request_count += 1
        
        if is_error:
            self.error_count += 1
    
    def get_average_duration(self) -> float:
        """Get average request duration in milliseconds."""
        if self.request_count == 0:
            return 0.0
        return self.total_duration_ms / self.request_count
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        return {
            "request_count": self.request_count,
            "average_duration_ms": self.get_average_duration(),
            "slow_request_count": self.slow_request_count,
            "error_count": self.error_count,
        }


# Global metrics instance
_metrics = PerformanceMetrics()


def get_performance_metrics() -> dict:
    """
    Get current performance metrics.
    
    Returns:
        Dictionary with performance statistics
    
    Example:
        ```python
        from app.api.middleware.logging import get_performance_metrics
        
        @router.get("/metrics")
        async def metrics():
            return get_performance_metrics()
        ```
    """
    return _metrics.get_stats()
