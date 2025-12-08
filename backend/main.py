"""
FastAPI Application Entry Point - Clean Architecture

This module serves as the root-level entry point for the FastAPI application.
It imports the application instance from app.main where the actual configuration
and initialization occurs.

For direct execution (development), use: python -m backend.main
For production deployment, use: uvicorn backend.main:app
"""

# Import the configured application from app.main
from app.main import app

# Re-export for convenience
__all__ = ["app"]
