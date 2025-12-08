"""
API Routes - REST Endpoints

This module exports all REST API routers for the application.
Routers are organized by feature:
- health: Health check and readiness endpoints
- models: Model management (list, switch, status)
- history: Transcription history management
- moderation: Content moderation functionality
"""

from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.api.routes.history import router as history_router
from app.api.routes.moderation import router as moderation_router

__all__ = [
    "health_router",
    "models_router",
    "history_router",
    "moderation_router",
]
