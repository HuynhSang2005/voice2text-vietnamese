"""Moderation result domain entity."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class ModerationResult:
    """
    Domain entity representing content moderation analysis result.
    
    Contains the classification, confidence scores, and detected keywords
    from the hate speech detection model (ViSoBERT-HSD-Span).
    
    Attributes:
        label: Moderation classification (CLEAN, OFFENSIVE, HATE)
        confidence: Confidence score (0.0-1.0)
        is_flagged: Whether content should be flagged
        detected_keywords: List of detected offensive keywords
        processed_at: Timestamp of moderation processing
        model_version: Version of moderation model used
        spans: Optional span information (start, end, label)
    """
    
    label: str
    confidence: float
    is_flagged: bool
    detected_keywords: List[str] = field(default_factory=list)
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str = "visobert-hsd-span"
    spans: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    
    # Valid moderation labels
    CLEAN = "CLEAN"
    OFFENSIVE = "OFFENSIVE"
    HATE = "HATE"
    
    VALID_LABELS = {CLEAN, OFFENSIVE, HATE}
    
    def __post_init__(self) -> None:
        """Validate entity state after initialization."""
        if self.label not in self.VALID_LABELS:
            raise ValueError(
                f"Invalid moderation label: {self.label}. "
                f"Must be one of {self.VALID_LABELS}"
            )
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        
        if self.processed_at.tzinfo is None:
            self.processed_at = self.processed_at.replace(tzinfo=timezone.utc)
    
    def is_clean(self) -> bool:
        """
        Check if content is clean (not offensive).
        
        Returns:
            True if label is CLEAN, False otherwise.
        """
        return self.label == self.CLEAN
    
    def is_offensive(self) -> bool:
        """
        Check if content is offensive (but not hate speech).
        
        Returns:
            True if label is OFFENSIVE, False otherwise.
        """
        return self.label == self.OFFENSIVE
    
    def is_hate_speech(self) -> bool:
        """
        Check if content is hate speech.
        
        Returns:
            True if label is HATE, False otherwise.
        """
        return self.label == self.HATE
    
    def is_harmful(self) -> bool:
        """
        Check if content is harmful (offensive or hate speech).
        
        Returns:
            True if content is OFFENSIVE or HATE, False otherwise.
        """
        return self.is_offensive() or self.is_hate_speech()
    
    def has_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if moderation has high confidence.
        
        Args:
            threshold: Confidence threshold (default: 0.8)
        
        Returns:
            True if confidence exceeds threshold, False otherwise.
        """
        return self.confidence >= threshold
    
    def get_severity_score(self) -> float:
        """
        Calculate severity score combining label and confidence.
        
        Returns:
            Float between 0.0 (clean) and 1.0 (high-confidence hate speech).
        """
        if self.is_clean():
            return 0.0
        
        # Base severity by label
        base_severity = {
            self.OFFENSIVE: 0.5,
            self.HATE: 1.0,
        }.get(self.label, 0.0)
        
        # Weighted by confidence
        return base_severity * self.confidence
    
    def get_keyword_count(self) -> int:
        """
        Get count of detected offensive keywords.
        
        Returns:
            Number of keywords detected.
        """
        return len(self.detected_keywords)
    
    def to_dict(self) -> dict:
        """
        Convert entity to dictionary representation.
        
        Returns:
            Dictionary with all entity fields.
        """
        return {
            "label": self.label,
            "confidence": self.confidence,
            "is_flagged": self.is_flagged,
            "detected_keywords": self.detected_keywords,
            "processed_at": self.processed_at.isoformat(),
            "model_version": self.model_version,
            "spans": self.spans,
            "is_clean": self.is_clean(),
            "is_harmful": self.is_harmful(),
            "severity_score": self.get_severity_score(),
            "keyword_count": self.get_keyword_count(),
        }
    
    @classmethod
    def create_clean(cls, confidence: float = 1.0) -> "ModerationResult":
        """
        Factory method to create a CLEAN moderation result.
        
        Args:
            confidence: Confidence score (default: 1.0)
        
        Returns:
            ModerationResult with CLEAN label.
        """
        return cls(
            label=cls.CLEAN,
            confidence=confidence,
            is_flagged=False,
            detected_keywords=[],
        )
    
    @classmethod
    def create_offensive(
        cls,
        confidence: float,
        detected_keywords: List[str],
        spans: Optional[List[Dict[str, Any]]] = None,
    ) -> "ModerationResult":
        """
        Factory method to create an OFFENSIVE moderation result.
        
        Args:
            confidence: Confidence score
            detected_keywords: List of offensive keywords detected
            spans: Optional span information
        
        Returns:
            ModerationResult with OFFENSIVE label.
        """
        return cls(
            label=cls.OFFENSIVE,
            confidence=confidence,
            is_flagged=True,
            detected_keywords=detected_keywords,
            spans=spans or [],
        )
    
    @classmethod
    def create_hate_speech(
        cls,
        confidence: float,
        detected_keywords: List[str],
        spans: Optional[List[Dict[str, Any]]] = None,
    ) -> "ModerationResult":
        """
        Factory method to create a HATE moderation result.
        
        Args:
            confidence: Confidence score
            detected_keywords: List of hate keywords detected
            spans: Optional span information
        
        Returns:
            ModerationResult with HATE label.
        """
        return cls(
            label=cls.HATE,
            confidence=confidence,
            is_flagged=True,
            detected_keywords=detected_keywords,
            spans=spans or [],
        )
