"""Dependency injection container."""
from dependency_injector import containers, providers

from app.infrastructure.config.settings import Settings


class Container(containers.DeclarativeContainer):
    """
    Main dependency injection container.
    
    Manages the lifecycle and wiring of all application dependencies.
    Follows Clean Architecture principles with clear layer separation.
    """
    
    # Configuration
    config = providers.Configuration()
    
    # Settings (from environment)
    settings = providers.Singleton(
        Settings,
    )
    
    # Database (placeholder - will be implemented in Phase 2)
    # db_session = providers.Resource(
    #     get_async_session,
    #     database_url=settings.provided.database_url,
    # )
    
    # Repositories (placeholder - will be implemented in Phase 2)
    # transcription_repository = providers.Factory(
    #     SQLModelTranscriptionRepository,
    #     session=db_session,
    # )
    # 
    # session_repository = providers.Factory(
    #     SQLModelSessionRepository,
    #     session=db_session,
    # )
    
    # Workers (placeholder - will be implemented in Phase 2)
    # zipformer_worker = providers.Singleton(
    #     ZipformerWorker,
    #     config=settings.provided.zipformer_config,
    # )
    # 
    # span_detector_worker = providers.Singleton(
    #     SpanDetectorWorker,
    #     config=settings.provided.visobert_config,
    # )
    
    # Use Cases (placeholder - will be implemented in Phase 3)
    # transcribe_audio_use_case = providers.Factory(
    #     TranscribeAudioUseCase,
    #     transcription_repo=transcription_repository,
    #     session_repo=session_repository,
    #     zipformer_worker=zipformer_worker,
    # )
    # 
    # moderate_content_use_case = providers.Factory(
    #     ModerateContentUseCase,
    #     transcription_repo=transcription_repository,
    #     span_detector_worker=span_detector_worker,
    # )


# Global container instance
container = Container()
