"""Dependency injection container."""
from dependency_injector import containers, providers
from typing import Optional

from app.infrastructure.config.settings import Settings

# Application Layer - Use Cases
from app.application.use_cases.transcribe_audio import (
    TranscribeAudioUseCase,
    TranscribeAudioBatchUseCase,
)
from app.application.use_cases.get_history import (
    GetHistoryUseCase,
    GetHistoryItemUseCase,
)
from app.application.use_cases.delete_history import (
    DeleteHistoryItemUseCase,
    DeleteAllHistoryUseCase,
    DeleteHistoryByDateRangeUseCase,
)
from app.application.use_cases.model_management import (
    GetModelStatusUseCase,
    SwitchModelUseCase,
    ListAvailableModelsUseCase,
)
from app.application.use_cases.moderate_content import (
    ModerateContentUseCase,
    GetModerationStatusUseCase,
)

# Application Layer - Services
from app.application.services.audio_service import AudioService
from app.application.services.session_service import SessionService

# Application Layer - Interfaces (for type hints)
from app.application.interfaces.workers import (
    ITranscriptionWorker,
    IModerationWorker,
    IWorkerManager,
)
from app.application.interfaces.cache import ICache
from app.domain.repositories.transcription_repository import ITranscriptionRepository
from app.domain.repositories.session_repository import ISessionRepository


class Container(containers.DeclarativeContainer):
    """
    Main dependency injection container.
    
    Manages the lifecycle and wiring of all application dependencies.
    Follows Clean Architecture principles with clear layer separation.
    
    Scopes:
    - Singleton: Shared instance (stateless services, workers)
    - Factory: New instance per request (use cases, stateful services)
    - Resource: Managed lifecycle (database sessions, connections)
    """
    
    # ===== CONFIGURATION =====
    config = providers.Configuration()
    
    # Settings (from environment)
    settings = providers.Singleton(
        Settings,
    )
    
    # ===== APPLICATION SERVICES (Singleton - stateless) =====
    
    audio_service = providers.Singleton(
        AudioService,
        max_file_size_mb=10,
        supported_formats=["pcm", "wav", "mp3", "flac"],
        min_sample_rate=8000,
        max_sample_rate=48000,
        require_mono=False,
    )
    
    session_service = providers.Singleton(
        SessionService,
        cache=None,  # Optional: will be wired in Phase 3 when cache is implemented
        default_ttl_minutes=30,
        require_validation=False,
    )
    
    # ===== INFRASTRUCTURE DEPENDENCIES (Placeholder - Phase 3) =====
    
    # Cache (Optional - Redis or in-memory)
    cache = providers.Singleton(
        lambda: None,  # Placeholder: will be implemented in Phase 3
    )
    
    # Database session (SQLModel async session)
    # db_session = providers.Resource(
    #     get_async_session,
    #     database_url=settings.provided.database_url,
    # )
    
    # ===== REPOSITORIES (Placeholder - Phase 3) =====
    
    # Will be implemented in Phase 3 when infrastructure layer is built
    transcription_repository = providers.Singleton(
        lambda: None,  # Placeholder: ITranscriptionRepository
    )
    
    session_repository = providers.Singleton(
        lambda: None,  # Placeholder: ISessionRepository  
    )
    
    # ===== WORKERS (Placeholder - Phase 3) =====
    
    # Will be implemented in Phase 3 when worker infrastructure is built
    transcription_worker = providers.Singleton(
        lambda: None,  # Placeholder: ITranscriptionWorker (Zipformer)
    )
    
    moderation_worker = providers.Singleton(
        lambda: None,  # Placeholder: IModerationWorker (ViSoBERT)
    )
    
    worker_manager = providers.Singleton(
        lambda: None,  # Placeholder: IWorkerManager
    )
    
    # ===== USE CASES (Factory - new instance per request) =====
    
    # Transcription Use Cases
    transcribe_audio_use_case = providers.Factory(
        TranscribeAudioUseCase,
        repository=transcription_repository,
        transcription_worker=transcription_worker,
        moderation_worker=moderation_worker,
    )
    
    transcribe_audio_batch_use_case = providers.Factory(
        TranscribeAudioBatchUseCase,
        repository=transcription_repository,
        transcription_worker=transcription_worker,
        moderation_worker=moderation_worker,
    )
    
    # History Use Cases
    get_history_use_case = providers.Factory(
        GetHistoryUseCase,
        repository=transcription_repository,
        cache=cache,
    )
    
    get_history_item_use_case = providers.Factory(
        GetHistoryItemUseCase,
        repository=transcription_repository,
    )
    
    delete_history_item_use_case = providers.Factory(
        DeleteHistoryItemUseCase,
        repository=transcription_repository,
        cache=cache,
    )
    
    delete_all_history_use_case = providers.Factory(
        DeleteAllHistoryUseCase,
        repository=transcription_repository,
        cache=cache,
    )
    
    delete_history_by_date_range_use_case = providers.Factory(
        DeleteHistoryByDateRangeUseCase,
        repository=transcription_repository,
        cache=cache,
    )
    
    # Model Management Use Cases
    get_model_status_use_case = providers.Factory(
        GetModelStatusUseCase,
        worker_manager=worker_manager,
    )
    
    switch_model_use_case = providers.Factory(
        SwitchModelUseCase,
        worker_manager=worker_manager,
    )
    
    list_available_models_use_case = providers.Factory(
        ListAvailableModelsUseCase,
        # No dependencies needed
    )
    
    # Moderation Use Cases
    moderate_content_use_case = providers.Factory(
        ModerateContentUseCase,
        moderation_worker=moderation_worker,
    )
    
    get_moderation_status_use_case = providers.Factory(
        GetModerationStatusUseCase,
        moderation_worker=moderation_worker,
    )


# Global container instance
container = Container()
