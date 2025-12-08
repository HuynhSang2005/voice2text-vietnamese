"""
Model Management Routes

Provides endpoints for managing STT models (list, switch, status).
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_list_available_models_use_case,
    get_switch_model_use_case,
    get_get_model_status_use_case,
)
from app.application.use_cases.model_management import (
    ListAvailableModelsUseCase,
    SwitchModelUseCase,
    GetModelStatusUseCase,
)
from app.application.dtos.requests import ModelSwitchRequest
from app.application.dtos.responses import (
    ModelInfo,
    ModelSwitchResponse,
    ModelStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["Models"])


@router.get(
    "",
    response_model=List[ModelInfo],
    status_code=status.HTTP_200_OK,
    summary="List available models",
    description="Get a list of all available speech-to-text models with their metadata",
    responses={
        200: {
            "description": "List of available models",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "zipformer",
                            "name": "Zipformer 30M",
                            "description": "Real-time streaming ASR optimized for Vietnamese (6000h trained)",
                            "version": "1.0",
                            "language": "vi",
                            "sample_rate": 16000,
                            "is_available": True,
                            "is_default": True
                        }
                    ]
                }
            }
        }
    }
)
async def list_models(
    use_case: ListAvailableModelsUseCase = Depends(get_list_available_models_use_case)
) -> List[ModelInfo]:
    """
    List all available speech-to-text models.
    
    Returns:
        List[ModelInfo]: List of available models with metadata
        
    Example:
        ```
        GET /api/v1/models
        
        Response:
        [
            {
                "id": "zipformer",
                "name": "Zipformer 30M",
                "description": "Real-time streaming ASR...",
                "version": "1.0",
                "language": "vi",
                "sample_rate": 16000,
                "is_available": true,
                "is_default": true
            }
        ]
        ```
    """
    try:
        models = await use_case.execute()
        return models
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model list"
        )


@router.post(
    "/switch",
    response_model=ModelSwitchResponse,
    status_code=status.HTTP_200_OK,
    summary="Switch active model",
    description="Switch the active speech-to-text model (currently not supported - only one model available)",
    responses={
        200: {
            "description": "Model switched successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Switched to model: zipformer",
                        "previous_model": "zipformer",
                        "current_model": "zipformer"
                    }
                }
            }
        },
        400: {
            "description": "Invalid model ID or model not available",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Model 'invalid_model' is not available"
                    }
                }
            }
        },
        503: {
            "description": "Model switch failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to initialize model"
                    }
                }
            }
        }
    }
)
async def switch_model(
    request: ModelSwitchRequest,
    use_case: SwitchModelUseCase = Depends(get_switch_model_use_case)
) -> ModelSwitchResponse:
    """
    Switch the active STT model.
    
    Args:
        request: Model switch request with target model ID
        
    Returns:
        ModelSwitchResponse: Switch result with previous and current model
        
    Raises:
        HTTPException: 400 if model not available, 503 if switch fails
        
    Note:
        Currently only one model (Zipformer) is available, so switching
        will return the same model. This endpoint is prepared for future
        multi-model support.
        
    Example:
        ```
        POST /api/v1/models/switch
        {
            "model_id": "zipformer"
        }
        
        Response:
        {
            "success": true,
            "message": "Switched to model: zipformer",
            "previous_model": "zipformer",
            "current_model": "zipformer"
        }
        ```
    """
    try:
        response = await use_case.execute(request)
        return response
    except ValueError as e:
        # Model not found or not available
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Model switch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to switch model: {str(e)}"
        )


@router.get(
    "/status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current model status",
    description="Get the status of the currently active model including readiness and performance metrics",
    responses={
        200: {
            "description": "Model status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "model_id": "zipformer",
                        "model_name": "Zipformer 30M",
                        "is_ready": True,
                        "is_loading": False,
                        "total_requests": 1523,
                        "successful_requests": 1520,
                        "failed_requests": 3,
                        "average_latency_ms": 245.3,
                        "last_used": "2025-12-08T10:30:45Z"
                    }
                }
            }
        },
        503: {
            "description": "Model not ready",
            "content": {
                "application/json": {
                    "example": {
                        "model_id": "zipformer",
                        "model_name": "Zipformer 30M",
                        "is_ready": False,
                        "is_loading": True,
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "average_latency_ms": 0.0,
                        "last_used": None
                    }
                }
            }
        }
    }
)
async def get_model_status(
    use_case: GetModelStatusUseCase = Depends(get_get_model_status_use_case)
) -> ModelStatusResponse:
    """
    Get current model status and performance metrics.
    
    Returns:
        ModelStatusResponse: Current model status with metrics
        
    Raises:
        HTTPException: 503 if model is not ready
        
    Example:
        ```
        GET /api/v1/models/status
        
        Response:
        {
            "model_id": "zipformer",
            "model_name": "Zipformer 30M",
            "is_ready": true,
            "is_loading": false,
            "total_requests": 1523,
            "successful_requests": 1520,
            "failed_requests": 3,
            "average_latency_ms": 245.3,
            "last_used": "2025-12-08T10:30:45Z"
        }
        ```
    """
    try:
        status_response = await use_case.execute()
        
        # Return 503 if model is not ready
        if not status_response.is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model is not ready"
            )
        
        return status_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model status"
        )
