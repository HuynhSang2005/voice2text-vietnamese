"""
Database models for the Infrastructure layer.

This module contains SQLModel ORM models that map to database tables.
These models are separate from domain entities and are used exclusively
for database operations.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class TranscriptionModel(SQLModel, table=True):
    """
    SQLModel ORM model for transcription_logs table.

    Stores transcription history with moderation data.
    Each record represents one transcription session.

    Indexes:
        - session_id: For querying by session
        - model_id: For querying by model
        - created_at: For time-based queries and sorting
        - moderation_label: For filtering by moderation status
        - is_flagged: For finding flagged content
    """

    __tablename__ = "transcription_logs"

    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Core fields with indexes
    session_id: str = Field(
        index=True, max_length=255, description="Unique session identifier"
    )
    model_id: str = Field(
        index=True,
        max_length=100,
        description="Model used for transcription (e.g., 'zipformer-30M')",
    )
    content: str = Field(description="Transcribed text content", max_length=10000)
    latency_ms: float = Field(
        default=0.0, ge=0.0, description="Processing latency in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="Timestamp of creation (UTC)",
    )

    # Content Moderation fields
    moderation_label: Optional[str] = Field(
        default=None,
        index=True,
        max_length=20,
        description="Moderation label: CLEAN, OFFENSIVE, or HATE",
    )
    moderation_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score of moderation (0.0 to 1.0)",
    )
    is_flagged: Optional[bool] = Field(
        default=None,
        index=True,
        description="Whether the content was flagged by moderation",
    )
    detected_keywords: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="List of detected offensive keywords",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "session_id": "sess_123abc",
                "model_id": "zipformer-30M",
                "content": "Xin chào, tôi là người dùng mới",
                "latency_ms": 245.5,
                "moderation_label": "CLEAN",
                "moderation_confidence": 0.98,
                "is_flagged": False,
                "detected_keywords": [],
            }
        }


class SessionModel(SQLModel, table=True):
    """
    SQLModel ORM model for sessions table.

    Stores user session data for grouping transcriptions.
    Each session has a TTL (time-to-live) and can be active or inactive.

    Indexes:
        - model_id: For querying by model
        - expires_at: For finding expired sessions
        - is_active: For finding active sessions
    """

    __tablename__ = "sessions"

    # Primary key (UUID string)
    id: str = Field(primary_key=True, max_length=36)

    # Session metadata
    model_id: str = Field(
        index=True, max_length=100, description="Current model being used"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation timestamp (UTC)",
    )
    expires_at: datetime = Field(
        index=True, description="Session expiration timestamp (UTC)"
    )
    is_active: bool = Field(
        default=True, index=True, description="Whether session is currently active"
    )
    transcription_count: int = Field(
        default=0, ge=0, description="Number of transcriptions in session"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "model_id": "zipformer-30M",
                "is_active": True,
                "transcription_count": 5,
            }
        }
