from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class TranscriptionLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str
    model_id: str
    content: str
    latency_ms: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
