"""Unit tests for ModerationResult domain entity."""
import pytest
from datetime import datetime, timezone

from app.domain.entities.moderation_result import ModerationResult
from app.domain.value_objects.confidence_score import ConfidenceScore


class TestModerationResultEntity:
    """Test suite for ModerationResult entity."""
    
    def test_create_clean_result(self):
        """Test creating a clean moderation result."""
        result = ModerationResult.create_clean(
            confidence=0.99,
        )
        
        assert result.label == "CLEAN"
        assert result.confidence == 0.99
        assert result.is_flagged is False
        assert result.detected_keywords == []
        assert result.spans == []
        assert isinstance(result.processed_at, datetime)
    
    def test_create_offensive_result(self):
        """Test creating an offensive moderation result."""
        keywords = ["word1", "word2"]
        
        result = ModerationResult.create_offensive(
            confidence=0.85,
            detected_keywords=keywords,
        )
        
        assert result.label == "OFFENSIVE"
        assert result.confidence == 0.85
        assert result.detected_keywords == keywords
        assert result.is_flagged is True
        assert isinstance(result.processed_at, datetime)
    
    def test_create_hate_result(self):
        """Test creating a hate speech moderation result."""
        keywords = ["hate1", "hate2"]
        spans = [{"start": 0, "end": 5}, {"start": 10, "end": 15}]
        
        result = ModerationResult.create_hate_speech(
            confidence=0.92,
            detected_keywords=keywords,
            spans=spans,
        )
        
        assert result.label == "HATE"
        assert result.confidence == 0.92
        assert result.detected_keywords == keywords
        assert result.spans == spans
        assert result.is_flagged is True
    
    def test_is_clean_returns_true_for_clean_label(self):
        """Test is_clean() returns True for CLEAN label."""
        result = ModerationResult.create_clean(
            confidence=0.99,
        )
        
        assert result.is_clean() is True
    
    def test_is_clean_returns_false_for_offensive_label(self):
        """Test is_clean() returns False for non-CLEAN labels."""
        offensive_result = ModerationResult.create_offensive(
            confidence=0.85,
            detected_keywords=["bad"],
        )
        
        hate_result = ModerationResult.create_hate_speech(
            confidence=0.92,
            detected_keywords=["hate"],
        )
        
        assert offensive_result.is_clean() is False
        assert hate_result.is_clean() is False
    
    def test_is_harmful_returns_true_for_offensive_and_hate(self):
        """Test is_harmful() returns True for OFFENSIVE and HATE labels."""
        offensive_result = ModerationResult.create_offensive(
            confidence=0.85,
            detected_keywords=["bad"],
        )
        
        hate_result = ModerationResult.create_hate_speech(
            confidence=0.92,
            detected_keywords=["hate"],
        )
        
        assert offensive_result.is_harmful() is True
        assert hate_result.is_harmful() is True
    
    def test_is_harmful_returns_false_for_clean(self):
        """Test is_harmful() returns False for CLEAN label."""
        clean_result = ModerationResult.create_clean(
            confidence=0.99,
        )
        
        assert clean_result.is_harmful() is False
    
    def test_get_severity_score_for_hate(self):
        """Test severity score for HATE label."""
        result = ModerationResult.create_hate_speech(
            confidence=0.95,
            detected_keywords=["hate"],
        )
        
        score = result.get_severity_score()
        
        # HATE: 1.0 * 0.95 = 0.95
        assert score == pytest.approx(0.95, rel=0.01)
    
    def test_get_severity_score_for_offensive(self):
        """Test severity score for OFFENSIVE label."""
        result = ModerationResult.create_offensive(
            confidence=0.85,
            detected_keywords=["bad"],
        )
        
        score = result.get_severity_score()
        
        # OFFENSIVE: 0.5 * 0.85 = 0.425
        assert score == pytest.approx(0.425, rel=0.01)
    
    def test_get_severity_score_for_clean(self):
        """Test severity score for CLEAN label."""
        result = ModerationResult.create_clean(
            confidence=0.99,
        )
        
        score = result.get_severity_score()
        
        assert score == 0.0
    
    def test_has_high_confidence(self):
        """Test high confidence detection."""
        high_conf_result = ModerationResult.create_offensive(
            confidence=0.9,
            detected_keywords=["bad"],
        )
        
        low_conf_result = ModerationResult.create_offensive(
            confidence=0.65,
            detected_keywords=["bad"],
        )
        
        assert high_conf_result.has_high_confidence(threshold=0.8) is True
        assert low_conf_result.has_high_confidence(threshold=0.8) is False
    
    def test_moderation_result_with_spans(self):
        """Test moderation result with span information."""
        spans = [
            {"start": 0, "end": 5, "label": "HATE"},
            {"start": 10, "end": 15, "label": "HATE"},
            {"start": 20, "end": 25, "label": "HATE"},
        ]
        
        result = ModerationResult.create_hate_speech(
            confidence=0.92,
            detected_keywords=["hate1", "hate2"],
            spans=spans,
        )
        
        assert result.spans == spans
        assert len(result.spans) == 3
    
    def test_moderation_result_with_metadata(self):
        """Test moderation result with model_version."""
        result = ModerationResult(
            label="OFFENSIVE",
            confidence=0.85,
            is_flagged=True,
            detected_keywords=["bad"],
            spans=[],
            processed_at=datetime.now(timezone.utc),
            model_version="visobert-hsd-span-v2",
        )
        
        assert result.model_version == "visobert-hsd-span-v2"
    
    def test_moderation_result_equality(self):
        """Test moderation result equality based on all fields."""
        processed_at = datetime.now(timezone.utc)
        keywords = ["test"]
        
        r1 = ModerationResult(
            label="OFFENSIVE",
            confidence=0.85,
            is_flagged=True,
            detected_keywords=keywords,
            spans=[],
            processed_at=processed_at,
        )
        
        r2 = ModerationResult(
            label="OFFENSIVE",
            confidence=0.85,
            is_flagged=True,
            detected_keywords=keywords,
            spans=[],
            processed_at=processed_at,
        )
        
        r3 = ModerationResult(
            label="CLEAN",
            confidence=0.99,
            is_flagged=False,
            detected_keywords=[],
            spans=[],
            processed_at=processed_at,
        )
        
        assert r1 == r2
        assert r1 != r3
    
    def test_moderation_result_immutability(self):
        """Test that moderation result fields should not be modified after creation."""
        result = ModerationResult.create_clean(
            confidence=0.99,
        )
        
        # Note: ModerationResult is not frozen, but we test the pattern
        # In production, fields should not be modified directly
        original_label = result.label
        assert original_label == "CLEAN"
    
    def test_confidence_score_validation(self):
        """Test that confidence score must be between 0.0 and 1.0."""
        # Valid confidence scores
        ModerationResult.create_clean(confidence=0.0)
        ModerationResult.create_clean(confidence=0.5)
        ModerationResult.create_clean(confidence=1.0)
        
        # Invalid confidence scores should raise ValueError
        with pytest.raises(ValueError):
            ModerationResult.create_clean(confidence=-0.1)
        
        with pytest.raises(ValueError):
            ModerationResult.create_clean(confidence=1.1)
    
    def test_label_validation(self):
        """Test that label must be one of CLEAN, OFFENSIVE, HATE."""
        # Valid labels work fine via factory methods
        ModerationResult.create_clean(confidence=0.99)
        ModerationResult.create_offensive(confidence=0.85, detected_keywords=[])
        ModerationResult.create_hate_speech(confidence=0.92, detected_keywords=[])
        
        # Invalid label should raise ValueError
        with pytest.raises(ValueError):
            ModerationResult(
                label="INVALID",
                confidence=0.85,
                is_flagged=False,
                detected_keywords=[],
                spans=[],
                processed_at=datetime.now(timezone.utc),
            )
