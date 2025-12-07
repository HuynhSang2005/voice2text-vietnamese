"""Unit tests for ConfidenceScore value object."""
import pytest
from app.domain.value_objects.confidence_score import ConfidenceScore


class TestConfidenceScoreValueObject:
    """Test suite for ConfidenceScore value object."""
    
    def test_create_valid_confidence_score(self):
        """Test creating confidence score with valid value."""
        score = ConfidenceScore(0.85)
        
        assert score.value == 0.85
        assert float(score) == 0.85
    
    def test_confidence_score_validation_valid_range(self):
        """Test confidence score accepts values in [0.0, 1.0]."""
        ConfidenceScore(0.0)  # Minimum
        ConfidenceScore(0.5)  # Middle
        ConfidenceScore(1.0)  # Maximum
    
    def test_confidence_score_validation_below_zero(self):
        """Test confidence score rejects values below 0.0."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ConfidenceScore(-0.1)
    
    def test_confidence_score_validation_above_one(self):
        """Test confidence score rejects values above 1.0."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            ConfidenceScore(1.1)
    
    def test_confidence_score_type_validation(self):
        """Test confidence score rejects non-numeric types."""
        with pytest.raises(TypeError, match="must be numeric"):
            ConfidenceScore("0.5")  # type: ignore
    
    def test_is_high_returns_true_for_high_confidence(self):
        """Test is_high() returns True for scores >= 0.8."""
        high_score = ConfidenceScore(0.8)
        very_high_score = ConfidenceScore(0.95)
        
        assert high_score.is_high() is True
        assert very_high_score.is_high() is True
    
    def test_is_high_returns_false_for_low_confidence(self):
        """Test is_high() returns False for scores < 0.8."""
        medium_score = ConfidenceScore(0.75)
        low_score = ConfidenceScore(0.5)
        
        assert medium_score.is_high() is False
        assert low_score.is_high() is False
    
    def test_is_medium_returns_true_for_medium_confidence(self):
        """Test is_medium() returns True for scores in [0.6, 0.8)."""
        medium_score_low = ConfidenceScore(0.6)
        medium_score_high = ConfidenceScore(0.79)
        
        assert medium_score_low.is_medium() is True
        assert medium_score_high.is_medium() is True
    
    def test_is_medium_returns_false_for_non_medium_confidence(self):
        """Test is_medium() returns False for scores outside [0.6, 0.8)."""
        high_score = ConfidenceScore(0.9)
        low_score = ConfidenceScore(0.5)
        
        assert high_score.is_medium() is False
        assert low_score.is_medium() is False
    
    def test_is_low_returns_true_for_low_confidence(self):
        """Test is_low() returns True for scores in [0.4, 0.6)."""
        low_score_threshold = ConfidenceScore(0.4)
        low_score_mid = ConfidenceScore(0.5)
        
        assert low_score_threshold.is_low() is True
        assert low_score_mid.is_low() is True
    
    def test_is_low_returns_false_for_non_low_confidence(self):
        """Test is_low() returns False for scores >= 0.6."""
        high_score = ConfidenceScore(0.8)
        medium_score = ConfidenceScore(0.6)  # Changed: 0.6 is not low
        
        assert high_score.is_low() is False
        assert medium_score.is_low() is False
    
    def test_is_very_low_returns_true_for_very_low_confidence(self):
        """Test is_very_low() returns True for scores < 0.4."""
        very_low_score = ConfidenceScore(0.3)
        zero_score = ConfidenceScore(0.0)
        
        assert very_low_score.is_very_low() is True
        assert zero_score.is_very_low() is True
    
    def test_is_very_low_returns_false_for_higher_confidence(self):
        """Test is_very_low() returns False for scores >= 0.4."""
        low_score = ConfidenceScore(0.4)
        medium_score = ConfidenceScore(0.7)
        
        assert low_score.is_very_low() is False
        assert medium_score.is_very_low() is False
    
    def test_get_level_returns_correct_classifications(self):
        """Test get_level() returns correct string classifications."""
        assert ConfidenceScore(0.95).get_level() == "HIGH"
        assert ConfidenceScore(0.7).get_level() == "MEDIUM"
        assert ConfidenceScore(0.5).get_level() == "LOW"
        assert ConfidenceScore(0.2).get_level() == "VERY_LOW"
    
    def test_comparison_operators_less_than(self):
        """Test < operator for confidence scores."""
        low = ConfidenceScore(0.5)
        high = ConfidenceScore(0.8)
        
        assert low < high
        assert not (high < low)
    
    def test_comparison_operators_less_equal(self):
        """Test <= operator for confidence scores."""
        low = ConfidenceScore(0.5)
        equal = ConfidenceScore(0.5)
        high = ConfidenceScore(0.8)
        
        assert low <= equal
        assert low <= high
        assert not (high <= low)
    
    def test_comparison_operators_greater_than(self):
        """Test > operator for confidence scores."""
        low = ConfidenceScore(0.5)
        high = ConfidenceScore(0.8)
        
        assert high > low
        assert not (low > high)
    
    def test_comparison_operators_greater_equal(self):
        """Test >= operator for confidence scores."""
        low = ConfidenceScore(0.5)
        equal = ConfidenceScore(0.5)
        high = ConfidenceScore(0.8)
        
        assert high >= low
        assert equal >= low
        assert not (low >= high)
    
    def test_equality_with_same_value(self):
        """Test equality for confidence scores with same value."""
        score1 = ConfidenceScore(0.85)
        score2 = ConfidenceScore(0.85)
        
        assert score1 == score2
    
    def test_equality_with_floating_point_precision(self):
        """Test equality handles floating point precision."""
        score1 = ConfidenceScore(0.1 + 0.2)  # 0.30000000000000004
        score2 = ConfidenceScore(0.3)
        
        assert score1 == score2
    
    def test_inequality_with_different_values(self):
        """Test inequality for confidence scores with different values."""
        score1 = ConfidenceScore(0.85)
        score2 = ConfidenceScore(0.90)
        
        assert score1 != score2
    
    def test_string_representation(self):
        """Test __str__ returns percentage format."""
        score = ConfidenceScore(0.856)
        
        assert str(score) == "85.6%"
    
    def test_repr_representation(self):
        """Test __repr__ returns constructor format."""
        score = ConfidenceScore(0.85)
        
        assert repr(score) == "ConfidenceScore(0.85)"
    
    def test_float_casting(self):
        """Test confidence score can be cast to float."""
        score = ConfidenceScore(0.85)
        
        assert float(score) == 0.85
        assert isinstance(float(score), float)
    
    def test_immutability(self):
        """Test that confidence score is immutable (frozen)."""
        score = ConfidenceScore(0.85)
        
        with pytest.raises(AttributeError):
            score.value = 0.90  # type: ignore
    
    def test_as_percentage(self):
        """Test as_percentage() method."""
        score = ConfidenceScore(0.85)
        
        assert score.as_percentage() == 85.0
        assert ConfidenceScore(0.0).as_percentage() == 0.0
        assert ConfidenceScore(1.0).as_percentage() == 100.0
    
    def test_from_percentage_class_method(self):
        """Test from_percentage() factory method."""
        score = ConfidenceScore.from_percentage(85.0)
        
        assert score.value == 0.85
        assert score.is_high()
    
    def test_from_percentage_validation(self):
        """Test from_percentage() validates input range."""
        with pytest.raises(ValueError):
            ConfidenceScore.from_percentage(-10.0)
        
        with pytest.raises(ValueError):
            ConfidenceScore.from_percentage(150.0)
    
    def test_zero_confidence(self):
        """Test confidence score with value 0.0."""
        score = ConfidenceScore(0.0)
        
        assert score.value == 0.0
        assert score.is_very_low()
        assert score.get_level() == "VERY_LOW"
    
    def test_full_confidence(self):
        """Test confidence score with value 1.0."""
        score = ConfidenceScore(1.0)
        
        assert score.value == 1.0
        assert score.is_high()
        assert score.get_level() == "HIGH"
