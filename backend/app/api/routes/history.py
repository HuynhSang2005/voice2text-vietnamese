"""
History Management Routes

Provides endpoints for retrieving and managing transcription history.
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_get_history_use_case,
    get_get_history_item_use_case,
    get_delete_history_item_use_case,
    get_delete_all_history_use_case,
)
from app.application.use_cases.get_history import (
    GetHistoryUseCase,
    GetHistoryItemUseCase,
)
from app.application.use_cases.delete_history import (
    DeleteHistoryItemUseCase,
    DeleteAllHistoryUseCase,
)
from app.application.dtos.requests import HistoryQueryRequest
from app.application.dtos.responses import HistoryResponse
from app.domain.exceptions import EntityNotFoundException  # Use base exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/history", tags=["History"])


@router.get(
    "",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get transcription history",
    description="Retrieve transcription history with filtering and pagination",
    responses={
        200: {
            "description": "History retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 123,
                                "content": "xin chào",
                                "model_id": "zipformer",
                                "session_id": "session-abc-123",
                                "latency_ms": 245,
                                "created_at": "2025-12-08T10:30:45Z",
                                "moderation_label": "clean",
                                "moderation_confidence": 0.95,
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "per_page": 50,
                        "total_pages": 1,
                    }
                }
            },
        }
    },
)
async def get_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    search: Optional[str] = Query(None, description="Search in transcription content"),
    model: Optional[str] = Query(None, description="Filter by model ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    moderation_label: Optional[str] = Query(
        None, description="Filter by moderation label"
    ),
    min_latency: Optional[float] = Query(
        None, ge=0, description="Minimum latency in ms"
    ),
    max_latency: Optional[float] = Query(
        None, ge=0, description="Maximum latency in ms"
    ),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    use_case: GetHistoryUseCase = Depends(get_get_history_use_case),
) -> HistoryResponse:
    """
    Get paginated transcription history with optional filtering.

    Args:
        page: Page number (1-indexed)
        limit: Number of items per page (max 100)
        search: Search term for content filtering
        model: Filter by model ID (e.g., "zipformer")
        session_id: Filter by session ID
        moderation_label: Filter by moderation label ("clean", "offensive", etc.)
        min_latency: Minimum latency threshold
        max_latency: Maximum latency threshold
        start_date: Filter records after this date
        end_date: Filter records before this date

    Returns:
        HistoryResponse: Paginated history with metadata

    Example:
        ```
        GET /api/v1/history?page=1&limit=10&search=xin%20chào&model=zipformer

        Response:
        {
            "items": [
                {
                    "id": 123,
                    "content": "xin chào",
                    "model_id": "zipformer",
                    "session_id": "session-abc-123",
                    "latency_ms": 245,
                    "created_at": "2025-12-08T10:30:45Z",
                    "moderation_label": "clean",
                    "moderation_confidence": 0.95
                }
            ],
            "total": 1,
            "page": 1,
            "per_page": 10,
            "total_pages": 1
        }
        ```
    """
    try:
        # Build query request
        query_request = HistoryQueryRequest(
            page=page,
            per_page=limit,
            search=search,
            model_id=model,
            session_id=session_id,
            moderation_label=moderation_label,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            start_date=start_date,
            end_date=end_date,
        )

        # Execute use case
        response = await use_case.execute(query_request)
        return response

    except Exception as e:
        logger.error(f"Failed to retrieve history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcription history",
        )


@router.get(
    "/{history_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get single history item",
    description="Retrieve a specific transcription record by ID",
    responses={
        200: {
            "description": "History item retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "content": "xin chào",
                        "model_id": "zipformer",
                        "session_id": "session-abc-123",
                        "latency_ms": 245,
                        "created_at": "2025-12-08T10:30:45Z",
                        "moderation_label": "clean",
                        "moderation_confidence": 0.95,
                    }
                }
            },
        },
        404: {
            "description": "History item not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Transcription record with ID 123 not found"}
                }
            },
        },
    },
)
async def get_history_item(
    history_id: int,
    use_case: GetHistoryItemUseCase = Depends(get_get_history_item_use_case),
) -> dict:
    """
    Get a single transcription history item by ID.

    Args:
        history_id: ID of the transcription record

    Returns:
        dict: Transcription record details

    Raises:
        HTTPException: 404 if record not found

    Example:
        ```
        GET /api/v1/history/123

        Response:
        {
            "id": 123,
            "content": "xin chào",
            "model_id": "zipformer",
            "session_id": "session-abc-123",
            "latency_ms": 245,
            "created_at": "2025-12-08T10:30:45Z",
            "moderation_label": "clean",
            "moderation_confidence": 0.95
        }
        ```
    """
    try:
        item = await use_case.execute(history_id)

        # Convert entity to dict for response
        return {
            "id": item.id,
            "content": item.content,
            "model_id": item.model_id,
            "session_id": item.session_id,
            "latency_ms": item.latency_ms,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "moderation_label": item.moderation_label,
            "moderation_confidence": item.moderation_confidence,
        }

    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to retrieve history item {history_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcription record",
        )


@router.delete(
    "/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete history item",
    description="Delete a specific transcription record by ID",
    responses={
        204: {"description": "History item deleted successfully"},
        404: {
            "description": "History item not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Transcription record with ID 123 not found"}
                }
            },
        },
    },
)
async def delete_history_item(
    history_id: int,
    use_case: DeleteHistoryItemUseCase = Depends(get_delete_history_item_use_case),
) -> None:
    """
    Delete a specific transcription history item.

    Args:
        history_id: ID of the transcription record to delete

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if record not found

    Example:
        ```
        DELETE /api/v1/history/123

        Response: 204 No Content
        ```
    """
    try:
        await use_case.execute(history_id)

    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete history item {history_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transcription record",
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all history",
    description="Delete all transcription history (use with caution)",
    responses={204: {"description": "All history deleted successfully"}},
)
async def delete_all_history(
    use_case: DeleteAllHistoryUseCase = Depends(get_delete_all_history_use_case),
) -> None:
    """
    Delete ALL transcription history.

    ⚠️ **WARNING**: This operation cannot be undone!

    Returns:
        None (204 No Content)

    Example:
        ```
        DELETE /api/v1/history

        Response: 204 No Content
        ```
    """
    try:
        await use_case.execute()
        logger.info("All transcription history deleted")

    except Exception as e:
        logger.error(f"Failed to delete all history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete history",
        )
