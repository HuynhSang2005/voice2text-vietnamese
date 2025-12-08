"""Session domain entity."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4


@dataclass
class Session:
    """
    Domain entity representing a user transcription session.

    A session groups multiple transcriptions from a single recording session
    and manages session lifecycle (creation, expiration, cleanup).

    Attributes:
        id: Unique session identifier (UUID)
        model_id: Current model being used
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        is_active: Whether session is currently active
        transcription_count: Number of transcriptions in session
    """

    id: str
    model_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool = True
    transcription_count: int = 0

    def __post_init__(self) -> None:
        """Validate entity state after initialization."""
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)

        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)

    def is_expired(self) -> bool:
        """
        Check if session has expired.

        Returns:
            True if current time exceeds expiration time, False otherwise.
        """
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """
        Check if session is valid and active.

        Returns:
            True if session is active and not expired, False otherwise.
        """
        return self.is_active and not self.is_expired()

    def extend_expiration(self, hours: int = 24) -> None:
        """
        Extend session expiration time.

        Args:
            hours: Number of hours to extend (default: 24)
        """
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    def deactivate(self) -> None:
        """Mark session as inactive (closed)."""
        self.is_active = False

    def increment_transcription_count(self) -> None:
        """Increment the transcription counter."""
        self.transcription_count += 1

    def get_remaining_time(self) -> timedelta:
        """
        Get remaining time until session expires.

        Returns:
            Timedelta representing remaining time, or zero if expired.
        """
        remaining = self.expires_at - datetime.now(timezone.utc)
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def to_dict(self) -> dict:
        """
        Convert entity to dictionary representation.

        Returns:
            Dictionary with all entity fields.
        """
        return {
            "id": self.id,
            "model_id": self.model_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
            "is_valid": self.is_valid(),
            "transcription_count": self.transcription_count,
            "remaining_seconds": int(self.get_remaining_time().total_seconds()),
        }

    @classmethod
    def create_new(
        cls,
        model_id: str,
        ttl_hours: int = 24,
        session_id: Optional[str] = None,
    ) -> "Session":
        """
        Factory method to create a new session.

        Args:
            model_id: Model ID to use for transcription
            ttl_hours: Time-to-live in hours (default: 24)
            session_id: Optional custom session ID, generates UUID if not provided

        Returns:
            New Session entity instance.
        """
        now = datetime.now(timezone.utc)

        return cls(
            id=session_id or str(uuid4()),
            model_id=model_id,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
            is_active=True,
            transcription_count=0,
        )
