"""
Moderation Routes

Provides endpoints for content moderation functionality.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_moderate_content_use_case,
    get_get_moderation_status_use_case,
)
from app.application.use_cases.moderate_content import (
    ModerateContentUseCase,
    GetModerationStatusUseCase,
)
from app.application.dtos.requests import (
    StandaloneModerateRequest,
    ModerationToggleRequest,
)
from app.application.dtos.responses import (
    ModerationResponse,
    ModerationStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/moderation", tags=["Moderation"])


@router.post(
    "/moderate",
    response_model=ModerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Moderate content",
    description="Analyze text content for hate speech and offensive language",
    responses={
        200: {
            "description": "Content moderated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "label": "clean",
                        "confidence": 0.95,
                        "details": {
                            "hate_speech": False,
                            "offensive": False,
                            "profanity": False
                        },
                        "text": "xin chào",
                        "timestamp": "2025-12-08T10:30:45Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Text content is required"
                    }
                }
            }
        },
        503: {
            "description": "Moderation service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Moderation worker is not ready"
                    }
                }
            }
        }
    }
)
async def moderate_content(
    request: StandaloneModerateRequest,
    use_case: ModerateContentUseCase = Depends(get_moderate_content_use_case)
) -> ModerationResponse:
    """
    Moderate text content for hate speech detection.
    
    This endpoint performs standalone moderation analysis on provided text.
    It uses the ViSoBERT-HSD-Span model to detect Vietnamese hate speech.
    
    Args:
        request: Text content to moderate
        
    Returns:
        ModerationResponse: Moderation analysis result
        
    Raises:
        HTTPException: 400 if text is empty, 503 if moderation service unavailable
        
    Example:
        ```
        POST /api/v1/moderation/moderate
        {
            "text": "xin chào"
        }
        
        Response:
        {
            "label": "clean",
            "confidence": 0.95,
            "details": {
                "hate_speech": false,
                "offensive": false,
                "profanity": false
            },
            "text": "xin chào",
            "timestamp": "2025-12-08T10:30:45Z"
        }
        ```
    """
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text content is required and cannot be empty"
            )
        
        # Execute moderation
        response = await use_case.execute(request)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Moderation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Moderation service error: {str(e)}"
        )


@router.post(
    "/toggle",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Toggle moderation",
    description="Enable or disable automatic moderation for transcriptions",
    responses={
        200: {
            "description": "Moderation setting updated",
            "content": {
                "application/json": {
                    "example": {
                        "enabled": True,
                        "message": "Moderation has been enabled"
                    }
                }
            }
        }
    }
)
async def toggle_moderation(
    request: ModerationToggleRequest
) -> dict:
    """
    Enable or disable automatic content moderation.
    
    Args:
        request: Toggle request with enabled flag
        
    Returns:
        dict: Updated moderation status
        
    Note:
        This is a placeholder for future implementation.
        Currently, moderation is always enabled if the worker is available.
        
    Example:
        ```
        POST /api/v1/moderation/toggle
        {
            "enabled": true
        }
        
        Response:
        {
            "enabled": true,
            "message": "Moderation has been enabled"
        }
        ```
    """
    # Placeholder for future implementation
    # In the future, this could update a global setting or session-specific setting
    message = "Moderation has been enabled" if request.enabled else "Moderation has been disabled"
    
    logger.info(f"Moderation toggle: {request.enabled}")
    
    return {
        "enabled": request.enabled,
        "message": message
    }


@router.get(
    "/status",
    response_model=ModerationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get moderation status",
    description="Get current moderation service status and statistics",
    responses={
        200: {
            "description": "Moderation status retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "enabled": True,
                        "worker_ready": True,
                        "model_name": "ViSoBERT-HSD-Span",
                        "total_checks": 1523,
                        "clean_count": 1450,
                        "offensive_count": 73,
                        "average_confidence": 0.89
                    }
                }
            }
        },
        503: {
            "description": "Moderation service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "enabled": False,
                        "worker_ready": False,
                        "model_name": "ViSoBERT-HSD-Span",
                        "total_checks": 0,
                        "clean_count": 0,
                        "offensive_count": 0,
                        "average_confidence": 0.0
                    }
                }
            }
        }
    }
)
async def get_moderation_status(
    use_case: GetModerationStatusUseCase = Depends(get_get_moderation_status_use_case)
) -> ModerationStatusResponse:
    """
    Get current moderation service status and usage statistics.
    
    Returns:
        ModerationStatusResponse: Moderation status with statistics
        
    Example:
        ```
        GET /api/v1/moderation/status
        
        Response:
        {
            "enabled": true,
            "worker_ready": true,
            "model_name": "ViSoBERT-HSD-Span",
            "total_checks": 1523,
            "clean_count": 1450,
            "offensive_count": 73,
            "average_confidence": 0.89
        }
        ```
    """
    try:
        status_response = await use_case.execute()
        return status_response
        
    except Exception as e:
        logger.error(f"Failed to get moderation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve moderation status"
        )
