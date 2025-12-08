"""Confidence score value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceScore:
    """
    Immutable value object representing a confidence score.

    Ensures confidence values are always valid (between 0.0 and 1.0)
    and provides semantic methods for interpreting confidence levels.

    Attributes:
        value: Confidence score between 0.0 (no confidence) and 1.0 (full confidence)
    """

    value: float

    # Confidence thresholds
    HIGH_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.6
    LOW_THRESHOLD = 0.4

    def __post_init__(self) -> None:
        """Validate confidence score after initialization."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(f"Confidence must be numeric, got {type(self.value)}")

        if not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.value}"
            )

    def __float__(self) -> float:
        """Allow casting to float."""
        return self.value

    def __str__(self) -> str:
        """String representation as percentage."""
        return f"{self.value:.1%}"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ConfidenceScore({self.value})"

    def __lt__(self, other: "ConfidenceScore") -> bool:
        """Less than comparison."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "ConfidenceScore") -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "ConfidenceScore") -> bool:
        """Greater than comparison."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "ConfidenceScore") -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return self.value >= other.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, ConfidenceScore):
            return NotImplemented
        return abs(self.value - other.value) < 1e-6  # Floating-point comparison

    def is_high(self) -> bool:
        """
        Check if confidence is high (>= 0.8).

        Returns:
            True if confidence >= HIGH_THRESHOLD, False otherwise.
        """
        return self.value >= self.HIGH_THRESHOLD

    def is_medium(self) -> bool:
        """
        Check if confidence is medium (>= 0.6 and < 0.8).

        Returns:
            True if MEDIUM_THRESHOLD <= confidence < HIGH_THRESHOLD, False otherwise.
        """
        return self.MEDIUM_THRESHOLD <= self.value < self.HIGH_THRESHOLD

    def is_low(self) -> bool:
        """
        Check if confidence is low (< 0.6).

        Returns:
            True if confidence < MEDIUM_THRESHOLD, False otherwise.
        """
        return self.value < self.MEDIUM_THRESHOLD

    def is_very_low(self) -> bool:
        """
        Check if confidence is very low (< 0.4).

        Returns:
            True if confidence < LOW_THRESHOLD, False otherwise.
        """
        return self.value < self.LOW_THRESHOLD

    def get_level(self) -> str:
        """
        Get confidence level as string.

        Returns:
            "VERY_LOW", "LOW", "MEDIUM", or "HIGH".
        """
        if self.is_very_low():
            return "VERY_LOW"
        elif self.is_low():
            return "LOW"
        elif self.is_medium():
            return "MEDIUM"
        else:
            return "HIGH"

    def as_percentage(self) -> float:
        """
        Get confidence as percentage (0-100).

        Returns:
            Confidence score as percentage.
        """
        return self.value * 100

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with value, percentage, and level.
        """
        return {
            "value": self.value,
            "percentage": self.as_percentage(),
            "level": self.get_level(),
            "is_high": self.is_high(),
            "is_medium": self.is_medium(),
            "is_low": self.is_low(),
        }

    @classmethod
    def from_percentage(cls, percentage: float) -> "ConfidenceScore":
        """
        Create confidence score from percentage (0-100).

        Args:
            percentage: Confidence as percentage (0-100)

        Returns:
            ConfidenceScore instance.

        Raises:
            ValueError: If percentage is not between 0 and 100.
        """
        if not (0.0 <= percentage <= 100.0):
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        return cls(percentage / 100.0)

    @classmethod
    def max_confidence(cls) -> "ConfidenceScore":
        """Create maximum confidence score (1.0)."""
        return cls(1.0)

    @classmethod
    def zero_confidence(cls) -> "ConfidenceScore":
        """Create zero confidence score (0.0)."""
        return cls(0.0)

    @classmethod
    def high_confidence(cls) -> "ConfidenceScore":
        """Create high confidence score (0.8)."""
        return cls(cls.HIGH_THRESHOLD)

    @classmethod
    def medium_confidence(cls) -> "ConfidenceScore":
        """Create medium confidence score (0.6)."""
        return cls(cls.MEDIUM_THRESHOLD)
