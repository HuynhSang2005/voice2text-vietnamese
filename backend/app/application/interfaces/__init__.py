"""
Application Layer - Central Interface Exports

This module provides a centralized location to import all interface
definitions used by the application layer. It re-exports domain
repository interfaces and defines application-specific interfaces.

Usage:
    ```python
    from app.application.interfaces import (
        ITranscriptionRepository,
        ITranscriptionWorker,
        ICache
    )
    
    class TranscribeAudioUseCase:
        def __init__(
            self,
            repo: ITranscriptionRepository,
            worker: ITranscriptionWorker,
            cache: ICache
        ):
            ...
    ```
"""

# Re-export domain repository interfaces
from app.domain.repositories.transcription_repository import ITranscriptionRepository
from app.domain.repositories.session_repository import ISessionRepository

# Export application-specific interfaces
from app.application.interfaces.workers import (
    ITranscriptionWorker,
    IModerationWorker,
    IWorkerManager,
)
from app.application.interfaces.cache import ICache, ICacheFactory


__all__ = [
    # Domain Repository Interfaces
    "ITranscriptionRepository",
    "ISessionRepository",
    # Worker Interfaces
    "ITranscriptionWorker",
    "IModerationWorker",
    "IWorkerManager",
    # Cache Interfaces
    "ICache",
    "ICacheFactory",
]
