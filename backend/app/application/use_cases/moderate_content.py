"""
Moderation use cases for standalone content moderation.

This module contains use cases for moderating text content independently
from transcription. Useful for:
- Post-processing already transcribed text
- Moderating user-submitted text
- Batch moderation of historical content
"""

from typing import Optional

from app.application.dtos.requests import StandaloneModerateRequest
from app.application.dtos.responses import ContentModerationResponse
from app.application.interfaces.workers import IModerationWorker
from app.domain.entities.moderation_result import ModerationResult
from app.domain.exceptions import ValidationException, BusinessRuleViolationException
from app.domain.exceptions.worker import WorkerException


class ModerateContentUseCase:
    """
    Use case for standalone content moderation.
    
    This use case analyzes text content for offensive language and hate speech
    without requiring a transcription workflow. It applies configurable thresholds
    and returns detailed moderation results.
    
    Business Rules:
    - Text must not be empty or whitespace-only
    - Text length limited to 5000 characters
    - Confidence threshold must be between 0.0 and 1.0
    - Moderation worker must be available and ready
    
    Example:
        ```python
        use_case = ModerateContentUseCase(moderation_worker)
        
        request = StandaloneModerateRequest(
            text="Sample text to moderate",
            threshold=0.5
        )
        
        response = await use_case.execute(request)
        if response.is_flagged:
            print(f"Content flagged as {response.label}")
        ```
    """
    
    def __init__(self, moderation_worker: IModerationWorker):
        """
        Initialize use case with moderation worker dependency.
        
        Args:
            moderation_worker: Worker for content moderation
            
        Raises:
            ValidationException: If moderation_worker is None
        """
        if moderation_worker is None:
            raise ValidationException(
                field="moderation_worker",
                value=None,
                constraint="must not be None"
            )
        
        self._moderation_worker = moderation_worker
    
    async def execute(
        self,
        request: StandaloneModerateRequest
    ) -> ContentModerationResponse:
        """
        Execute content moderation on provided text.
        
        This method validates the request, checks worker readiness,
        performs moderation analysis, applies threshold-based flagging,
        and returns a detailed response.
        
        Args:
            request: Moderation request with text and threshold
            
        Returns:
            ContentModerationResponse: Moderation result with label,
                                      confidence, and detected keywords
                                      
        Raises:
            ValidationException: If request is None or invalid
            BusinessRuleViolationException: If worker not ready
            WorkerException: If moderation fails
            
        Example:
            ```python
            request = StandaloneModerateRequest(
                text="Xin chào",
                threshold=0.5
            )
            response = await use_case.execute(request)
            # response.label = "CLEAN"
            # response.confidence = 0.98
            # response.is_flagged = False
            ```
        """
        # Validate request
        if request is None:
            raise ValidationException(
                field="request",
                value=None,
                constraint="must not be None"
            )
        
        # Check worker readiness
        is_ready = await self._moderation_worker.is_ready()
        if not is_ready:
            raise BusinessRuleViolationException(
                rule="moderation_worker_must_be_ready",
                reason="Moderation worker is not available or not started"
            )
        
        try:
            # Perform moderation
            result: ModerationResult = await self._moderation_worker.moderate(
                request.text
            )
            
            # Apply threshold-based flagging
            # Override is_flagged if confidence doesn't meet threshold
            should_flag = (
                result.is_harmful() and 
                result.confidence >= request.threshold
            )
            
            # Create response
            response = ContentModerationResponse(
                label=result.label,
                confidence=result.confidence,
                is_flagged=should_flag,
                detected_keywords=result.detected_keywords
            )
            
            return response
            
        except WorkerException:
            # Re-raise worker exceptions as-is
            raise
            
        except Exception as e:
            # Wrap unexpected exceptions
            raise WorkerException(
                worker_type="moderation",
                message=f"Moderation failed with unexpected error: {str(e)}"
            ) from e


class GetModerationStatusUseCase:
    """
    Use case for checking moderation worker availability.
    
    This use case queries the moderation worker to determine if it's
    ready to process content. Useful for health checks and UI status display.
    
    Example:
        ```python
        use_case = GetModerationStatusUseCase(moderation_worker)
        status = await use_case.execute()
        
        if status["is_ready"]:
            print("Moderation available")
        else:
            print("Moderation unavailable")
        ```
    """
    
    def __init__(self, moderation_worker: Optional[IModerationWorker]):
        """
        Initialize use case with optional moderation worker.
        
        Args:
            moderation_worker: Worker for content moderation (can be None)
            
        Note:
            Unlike ModerateContentUseCase, this accepts None to handle
            cases where moderation is disabled system-wide.
        """
        self._moderation_worker = moderation_worker
    
    async def execute(self) -> dict:
        """
        Get current moderation worker status.
        
        Returns:
            Dictionary with status information:
            - is_available: Whether worker exists (not None)
            - is_ready: Whether worker is started and ready
            - model_version: Model version if available
            
        Example:
            ```python
            status = await use_case.execute()
            # {
            #     "is_available": True,
            #     "is_ready": True,
            #     "model_version": "visobert-hsd-span"
            # }
            ```
        """
        # If no worker configured
        if self._moderation_worker is None:
            return {
                "is_available": False,
                "is_ready": False,
                "model_version": None
            }
        
        try:
            # Check worker readiness
            is_ready = await self._moderation_worker.is_ready()
            
            return {
                "is_available": True,
                "is_ready": is_ready,
                "model_version": "visobert-hsd-span"  # Could be made configurable
            }
            
        except Exception as e:
            # If status check fails, return unavailable
            return {
                "is_available": True,
                "is_ready": False,
                "model_version": None,
                "error": str(e)
            }
