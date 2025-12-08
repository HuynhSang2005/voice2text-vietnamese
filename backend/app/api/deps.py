"""
FastAPI Dependency Injection

This module provides all dependencies needed by API endpoints.
Uses dependency-injector Container for service resolution.
"""
import logging
from typing import AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.infrastructure.config.container import Container, get_container
from app.application.services.session_service import SessionService
from app.application.services.audio_service import AudioService

# Use Cases - Import from actual module structure
from app.application.use_cases.transcribe_audio import (
    TranscribeAudioUseCase,
    TranscribeAudioBatchUseCase,
)
from app.application.use_cases.get_history import (
    GetHistoryUseCase,
    GetHistoryItemUseCase,
)
from app.application.use_cases.delete_history import (
    DeleteHistoryItemUseCase,
    DeleteAllHistoryUseCase,
    DeleteHistoryByDateRangeUseCase,
)
from app.application.use_cases.model_management import (
    GetModelStatusUseCase,
    SwitchModelUseCase,
    ListAvailableModelsUseCase,
)
from app.application.use_cases.moderate_content import (
    ModerateContentUseCase,
    GetModerationStatusUseCase,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Core Dependencies
# ============================================================================

def get_di_container() -> Container:
    """
    Get the Dependency Injection container.
    
    Returns:
        Container: The application DI container with all providers configured
    """
    return get_container()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.
    
    Yields:
        AsyncSession: SQLModel async session for database operations
        
    Note:
        Session is automatically committed/rolled back and closed after use.
    """
    async for session in get_session():
        yield session


# ============================================================================
# Service Dependencies
# ============================================================================

def get_session_service(
    container: Container = Depends(get_di_container)
) -> SessionService:
    """
    Get SessionService dependency.
    
    Args:
        container: DI container
        
    Returns:
        SessionService: Service for managing user sessions
    """
    return container.session_service()


def get_audio_service(
    container: Container = Depends(get_di_container)
) -> AudioService:
    """
    Get AudioService dependency.
    
    Args:
        container: DI container
        
    Returns:
        AudioService: Service for audio processing and validation
    """
    return container.audio_service()


# ============================================================================
# Use Case Dependencies - Transcription
# ============================================================================

def get_transcribe_audio_use_case(
    container: Container = Depends(get_di_container)
) -> TranscribeAudioUseCase:
    """Get TranscribeAudioUseCase dependency"""
    return container.transcribe_audio_use_case()


# ============================================================================
# Use Case Dependencies - History Management
# ============================================================================

def get_get_history_use_case(
    container: Container = Depends(get_di_container)
) -> GetHistoryUseCase:
    """Get GetHistoryUseCase dependency"""
    return container.get_history_use_case()


def get_get_history_item_use_case(
    container: Container = Depends(get_di_container)
) -> GetHistoryItemUseCase:
    """Get GetHistoryItemUseCase dependency"""
    return container.get_history_item_use_case()


def get_delete_history_item_use_case(
    container: Container = Depends(get_di_container)
) -> DeleteHistoryItemUseCase:
    """Get DeleteHistoryItemUseCase dependency"""
    return container.delete_history_item_use_case()


def get_delete_all_history_use_case(
    container: Container = Depends(get_di_container)
) -> DeleteAllHistoryUseCase:
    """Get DeleteAllHistoryUseCase dependency"""
    return container.delete_all_history_use_case()


# ============================================================================
# Use Case Dependencies - Model Management
# ============================================================================

def get_get_model_status_use_case(
    container: Container = Depends(get_di_container)
) -> GetModelStatusUseCase:
    """Get GetModelStatusUseCase dependency"""
    return container.get_model_status_use_case()


def get_switch_model_use_case(
    container: Container = Depends(get_di_container)
) -> SwitchModelUseCase:
    """Get SwitchModelUseCase dependency"""
    return container.switch_model_use_case()


def get_list_available_models_use_case(
    container: Container = Depends(get_di_container)
) -> ListAvailableModelsUseCase:
    """Get ListAvailableModelsUseCase dependency"""
    return container.list_available_models_use_case()


# ============================================================================
# Use Case Dependencies - Moderation
# ============================================================================

def get_moderate_content_use_case(
    container: Container = Depends(get_di_container)
) -> ModerateContentUseCase:
    """Get ModerateContentUseCase dependency"""
    return container.moderate_content_use_case()


def get_get_moderation_status_use_case(
    container: Container = Depends(get_di_container)
) -> GetModerationStatusUseCase:
    """Get GetModerationStatusUseCase dependency"""
    return container.get_moderation_status_use_case()


# ============================================================================
# Session Validation (for future authenticated endpoints)
# ============================================================================

async def validate_session(
    x_session_id: Optional[str] = Header(None),
    session_service: SessionService = Depends(get_session_service)
) -> Optional[str]:
    """
    Validate session ID from header (optional for now).
    
    Args:
        x_session_id: Session ID from X-Session-ID header
        session_service: Session management service
        
    Returns:
        str: Validated session ID, or None if not provided
        
    Raises:
        HTTPException: If session ID is invalid (when session validation is enforced)
        
    Note:
        Currently returns None if no session provided (sessions are optional).
        In future, can be made mandatory for authenticated endpoints.
    """
    if not x_session_id:
        return None
        
    # For now, we accept any session ID
    # In future, validate against session_service.get_session()
    return x_session_id


# ============================================================================
# Authentication (Future - Placeholder)
# ============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Get current authenticated user (placeholder for future auth).
    
    Args:
        authorization: Authorization header (Bearer token)
        
    Returns:
        dict: User information, or None if not authenticated
        
    Note:
        Currently returns None. Will be implemented when authentication is added.
    """
    # Placeholder for future JWT/OAuth implementation
    return None


async def require_auth(
    user: Optional[dict] = Depends(get_current_user)
) -> dict:
    """
    Require authentication for endpoint (placeholder for future).
    
    Args:
        user: Current user from get_current_user
        
    Returns:
        dict: Authenticated user information
        
    Raises:
        HTTPException: 401 if user is not authenticated
        
    Note:
        Currently disabled. Will be enabled when authentication is added.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ============================================================================
# Rate Limiting (Simple Implementation)
# ============================================================================

# In-memory rate limiting (for production, use Redis)
_rate_limit_storage: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX_REQUESTS = 100  # requests per window


async def rate_limit(
    request: Request,
    max_requests: int = _RATE_LIMIT_MAX_REQUESTS,
    window_seconds: int = _RATE_LIMIT_WINDOW
) -> None:
    """
    Simple rate limiting based on client IP.
    
    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: 429 if rate limit exceeded
        
    Note:
        Uses in-memory storage. For production with multiple workers,
        use Redis with app.infrastructure.cache.redis_cache.RedisCache
    """
    import time
    
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Initialize storage for this IP if not exists
    if client_ip not in _rate_limit_storage:
        _rate_limit_storage[client_ip] = []
    
    # Remove old timestamps outside the window
    _rate_limit_storage[client_ip] = [
        timestamp for timestamp in _rate_limit_storage[client_ip]
        if current_time - timestamp < window_seconds
    ]
    
    # Check if limit exceeded
    if len(_rate_limit_storage[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
            headers={"Retry-After": str(window_seconds)}
        )
    
    # Add current request timestamp
    _rate_limit_storage[client_ip].append(current_time)
