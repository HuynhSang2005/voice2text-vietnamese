from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from pydantic import field_serializer


class TranscriptionLog(SQLModel, table=True):
    """
    Database model for storing transcription history.
    
    Each record represents a transcription session (one recording session).
    """
    __tablename__ = "transcription_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, description="Unique session identifier")
    model_id: str = Field(index=True, description="Model used for transcription")
    content: str = Field(description="Transcribed text content")
    latency_ms: float = Field(default=0.0, description="Processing latency in milliseconds")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="Timestamp of creation"
    )

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO 8601 format with Z suffix."""
        if value is None:
            return None
        # Ensure UTC timezone and format with Z suffix
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')
