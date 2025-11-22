from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Transcription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_used: str
    content: str
    latency_ms: float
    created_at: datetime = Field(default_factory=datetime.now)
