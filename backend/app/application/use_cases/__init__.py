"""Use cases - Application-specific business operations."""

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
    SwitchModelUseCase,
    GetModelStatusUseCase,
    ListAvailableModelsUseCase,
)
from app.application.use_cases.moderate_content import (
    ModerateContentUseCase,
    GetModerationStatusUseCase,
)

__all__ = [
    # Transcription
    "TranscribeAudioUseCase",
    "TranscribeAudioBatchUseCase",
    # History Management
    "GetHistoryUseCase",
    "GetHistoryItemUseCase",
    "DeleteHistoryItemUseCase",
    "DeleteAllHistoryUseCase",
    "DeleteHistoryByDateRangeUseCase",
    # Model Management
    "SwitchModelUseCase",
    "GetModelStatusUseCase",
    "ListAvailableModelsUseCase",
    # Content Moderation
    "ModerateContentUseCase",
    "GetModerationStatusUseCase",
]

