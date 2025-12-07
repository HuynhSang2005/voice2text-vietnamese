"""Transcription domain entity."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID


@dataclass
class Transcription:
    """
    Core business entity representing a transcription session.
    
    Contains all business logic related to transcription records,
    including moderation status and offensive content detection.
    
    Attributes:
        id: Unique identifier (database primary key)
        session_id: Unique session identifier
        model_id: Model used for transcription
        content: Transcribed text content
        latency_ms: Processing latency in milliseconds
        created_at: Timestamp of creation
        moderation_label: Moderation classification (CLEAN, OFFENSIVE, HATE)
        moderation_confidence: Confidence score (0.0-1.0)
        is_flagged: Whether content was flagged by moderation
        detected_keywords: List of detected offensive keywords
    """
    
    id: Optional[int]
    session_id: str
    model_id: str
    content: str
    latency_ms: float
    created_at: datetime
    moderation_label: Optional[str] = None
    moderation_confidence: Optional[float] = None
    is_flagged: Optional[bool] = None
    detected_keywords: Optional[List[str]] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate entity state after initialization."""
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.moderation_confidence is not None:
            if not (0.0 <= self.moderation_confidence <= 1.0):
                raise ValueError(
                    f"moderation_confidence must be between 0.0 and 1.0, "
                    f"got {self.moderation_confidence}"
                )
    
    def is_offensive(self) -> bool:
        """
        Check if the transcription contains offensive content.
        
        Returns:
            True if content is flagged or labeled as OFFENSIVE/HATE, False otherwise.
        """
        if self.is_flagged:
            return True
        
        if self.moderation_label in ("OFFENSIVE", "HATE"):
            return True
        
        return False
    
    def is_clean(self) -> bool:
        """
        Check if the transcription is clean (not offensive).
        
        Returns:
            True if content is clean, False otherwise.
        """
        return not self.is_offensive()
    
    def has_high_confidence_moderation(self, threshold: float = 0.8) -> bool:
        """
        Check if moderation result has high confidence.
        
        Args:
            threshold: Confidence threshold (default: 0.8)
        
        Returns:
            True if moderation confidence exceeds threshold, False otherwise.
        """
        if self.moderation_confidence is None:
            return False
        
        return self.moderation_confidence >= threshold
    
    def get_severity_level(self) -> str:
        """
        Get severity level of offensive content.
        
        Returns:
            "NONE", "LOW", "MEDIUM", or "HIGH" based on moderation data.
        """
        if not self.is_offensive():
            return "NONE"
        
        if self.moderation_label == "HATE":
            return "HIGH"
        
        if self.moderation_label == "OFFENSIVE":
            if self.has_high_confidence_moderation(0.9):
                return "MEDIUM"
            return "LOW"
        
        # Flagged but no label
        return "LOW"
    
    def to_dict(self) -> dict:
        """
        Convert entity to dictionary representation.
        
        Returns:
            Dictionary with all entity fields.
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "model_id": self.model_id,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
            "moderation_label": self.moderation_label,
            "moderation_confidence": self.moderation_confidence,
            "is_flagged": self.is_flagged,
            "detected_keywords": self.detected_keywords,
            "is_offensive": self.is_offensive(),
            "severity_level": self.get_severity_level(),
        }
    
    @classmethod
    def create_new(
        cls,
        session_id: str,
        model_id: str,
        content: str,
        latency_ms: float,
        moderation_label: Optional[str] = None,
        moderation_confidence: Optional[float] = None,
        is_flagged: Optional[bool] = None,
        detected_keywords: Optional[List[str]] = None,
    ) -> "Transcription":
        """
        Factory method to create a new transcription entity.
        
        Args:
            session_id: Unique session identifier
            model_id: Model ID used for transcription
            content: Transcribed text
            latency_ms: Processing latency
            moderation_label: Optional moderation classification
            moderation_confidence: Optional confidence score
            is_flagged: Optional flag status
            detected_keywords: Optional list of offensive keywords
        
        Returns:
            New Transcription entity instance.
        """
        return cls(
            id=None,
            session_id=session_id,
            model_id=model_id,
            content=content,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc),
            moderation_label=moderation_label,
            moderation_confidence=moderation_confidence,
            is_flagged=is_flagged,
            detected_keywords=detected_keywords or [],
        )
