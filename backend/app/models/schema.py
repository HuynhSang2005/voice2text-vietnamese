from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


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
        default_factory=datetime.utcnow,
        index=True,
        description="Timestamp of creation"
    )
