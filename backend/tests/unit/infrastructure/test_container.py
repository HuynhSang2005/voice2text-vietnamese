"""
Tests for dependency injection container wiring.

Verifies that all use cases and services are correctly wired in the DI container.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from dependency_injector import providers

from app.infrastructure.config.container import Container
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
from app.application.services.audio_service import AudioService
from app.application.services.session_service import SessionService


class TestContainerConfiguration:
    """Test container configuration and provider setup."""
    
    def test_container_can_be_instantiated(self):
        """Test that container can be created."""
        from dependency_injector import containers
        container = Container()
        assert container is not None
        # Container() returns DynamicContainer instance
        assert isinstance(container, (containers.DeclarativeContainer, containers.DynamicContainer))
    
    def test_settings_provider_is_singleton(self):
        """Test that settings provider is configured as singleton."""
        container = Container()
        assert isinstance(container.settings, providers.Singleton)
    
    def test_audio_service_provider_is_singleton(self):
        """Test that audio service provider is singleton."""
        container = Container()
        assert isinstance(container.audio_service, providers.Singleton)
    
    def test_session_service_provider_is_singleton(self):
        """Test that session service provider is singleton."""
        container = Container()
        assert isinstance(container.session_service, providers.Singleton)
    
    def test_use_case_providers_are_factories(self):
        """Test that all use case providers are factories."""
        container = Container()
        
        use_case_providers = [
            container.transcribe_audio_use_case,
            container.transcribe_audio_batch_use_case,
            container.get_history_use_case,
            container.get_history_item_use_case,
            container.delete_history_item_use_case,
            container.delete_all_history_use_case,
            container.delete_history_by_date_range_use_case,
            container.get_model_status_use_case,
            container.switch_model_use_case,
            container.list_available_models_use_case,
            container.moderate_content_use_case,
            container.get_moderation_status_use_case,
        ]
        
        for provider in use_case_providers:
            assert isinstance(provider, providers.Factory)


class TestServiceProviders:
    """Test service provider resolution."""
    
    def test_audio_service_can_be_resolved(self):
        """Test that audio service can be resolved from container."""
        container = Container()
        audio_service = container.audio_service()
        
        assert audio_service is not None
        assert isinstance(audio_service, AudioService)
    
    def test_audio_service_is_singleton_instance(self):
        """Test that audio service returns same instance."""
        container = Container()
        service1 = container.audio_service()
        service2 = container.audio_service()
        
        assert service1 is service2
    
    def test_audio_service_has_correct_configuration(self):
        """Test that audio service has expected configuration."""
        container = Container()
        audio_service = container.audio_service()
        
        assert audio_service.get_max_file_size_mb() == 10
        assert "pcm" in audio_service.get_supported_formats()
        assert audio_service.get_sample_rate_range() == (8000, 48000)
    
    def test_session_service_can_be_resolved(self):
        """Test that session service can be resolved from container."""
        container = Container()
        session_service = container.session_service()
        
        assert session_service is not None
        assert isinstance(session_service, SessionService)
    
    def test_session_service_is_singleton_instance(self):
        """Test that session service returns same instance."""
        container = Container()
        service1 = container.session_service()
        service2 = container.session_service()
        
        assert service1 is service2
    
    def test_session_service_has_correct_configuration(self):
        """Test that session service has expected configuration."""
        container = Container()
        session_service = container.session_service()
        
        # Method returns seconds (30 minutes = 1800 seconds)
        assert session_service.get_default_ttl_seconds() == 1800


class TestUseCaseProviders:
    """Test use case provider resolution with mock dependencies."""
    
    @pytest.fixture
    def container_with_mocks(self):
        """Create container with mocked dependencies."""
        container = Container()
        
        # Override placeholder dependencies with mocks
        container.transcription_repository.override(Mock())
        container.session_repository.override(Mock())
        container.transcription_worker.override(Mock())
        container.moderation_worker.override(Mock())
        container.worker_manager.override(Mock())
        container.cache.override(Mock())
        
        yield container
        
        # Reset overrides
        container.reset_singletons()
    
    def test_transcribe_audio_use_case_can_be_resolved(self, container_with_mocks):
        """Test that transcribe audio use case can be resolved."""
        use_case = container_with_mocks.transcribe_audio_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, TranscribeAudioUseCase)
    
    def test_transcribe_audio_batch_use_case_can_be_resolved(self, container_with_mocks):
        """Test that batch transcribe use case can be resolved."""
        use_case = container_with_mocks.transcribe_audio_batch_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, TranscribeAudioBatchUseCase)
    
    def test_get_history_use_case_can_be_resolved(self, container_with_mocks):
        """Test that get history use case can be resolved."""
        use_case = container_with_mocks.get_history_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, GetHistoryUseCase)
    
    def test_get_history_item_use_case_can_be_resolved(self, container_with_mocks):
        """Test that get history item use case can be resolved."""
        use_case = container_with_mocks.get_history_item_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, GetHistoryItemUseCase)
    
    def test_delete_history_item_use_case_can_be_resolved(self, container_with_mocks):
        """Test that delete history item use case can be resolved."""
        use_case = container_with_mocks.delete_history_item_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, DeleteHistoryItemUseCase)
    
    def test_delete_all_history_use_case_can_be_resolved(self, container_with_mocks):
        """Test that delete all history use case can be resolved."""
        use_case = container_with_mocks.delete_all_history_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, DeleteAllHistoryUseCase)
    
    def test_delete_history_by_date_range_use_case_can_be_resolved(self, container_with_mocks):
        """Test that delete by date range use case can be resolved."""
        use_case = container_with_mocks.delete_history_by_date_range_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, DeleteHistoryByDateRangeUseCase)
    
    def test_get_model_status_use_case_can_be_resolved(self, container_with_mocks):
        """Test that get model status use case can be resolved."""
        use_case = container_with_mocks.get_model_status_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, GetModelStatusUseCase)
    
    def test_switch_model_use_case_can_be_resolved(self, container_with_mocks):
        """Test that switch model use case can be resolved."""
        use_case = container_with_mocks.switch_model_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, SwitchModelUseCase)
    
    def test_list_available_models_use_case_can_be_resolved(self, container_with_mocks):
        """Test that list available models use case can be resolved."""
        use_case = container_with_mocks.list_available_models_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, ListAvailableModelsUseCase)
    
    def test_moderate_content_use_case_can_be_resolved(self, container_with_mocks):
        """Test that moderate content use case can be resolved."""
        use_case = container_with_mocks.moderate_content_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, ModerateContentUseCase)
    
    def test_get_moderation_status_use_case_can_be_resolved(self, container_with_mocks):
        """Test that get moderation status use case can be resolved."""
        use_case = container_with_mocks.get_moderation_status_use_case()
        
        assert use_case is not None
        assert isinstance(use_case, GetModerationStatusUseCase)
    
    def test_use_cases_are_factory_instances(self, container_with_mocks):
        """Test that use cases return new instances each time."""
        use_case1 = container_with_mocks.transcribe_audio_use_case()
        use_case2 = container_with_mocks.transcribe_audio_use_case()
        
        # Factory should return different instances
        assert use_case1 is not use_case2


class TestDependencyWiring:
    """Test that dependencies are correctly wired."""
    
    @pytest.fixture
    def container_with_mocks(self):
        """Create container with mocked dependencies."""
        container = Container()
        
        # Create identifiable mocks
        mock_repo = Mock(name="transcription_repo")
        mock_worker = Mock(name="transcription_worker")
        mock_moderation = Mock(name="moderation_worker")
        mock_cache = Mock(name="cache")
        
        container.transcription_repository.override(mock_repo)
        container.session_repository.override(Mock())
        container.transcription_worker.override(mock_worker)
        container.moderation_worker.override(mock_moderation)
        container.cache.override(mock_cache)
        
        yield container
        
        container.reset_singletons()
    
    def test_transcribe_audio_use_case_receives_dependencies(self, container_with_mocks):
        """Test that transcribe audio use case receives correct dependencies."""
        use_case = container_with_mocks.transcribe_audio_use_case()

        # Verify dependencies are injected
        assert use_case._repository is not None
        assert use_case._transcription_worker is not None
        assert use_case._moderation_worker is not None
    
    def test_get_history_use_case_receives_dependencies(self, container_with_mocks):
        """Test that get history use case receives correct dependencies."""
        use_case = container_with_mocks.get_history_use_case()

        # Verify dependencies are injected
        assert use_case._repository is not None
        assert use_case._cache is not None
    
    def test_moderate_content_use_case_receives_dependencies(self, container_with_mocks):
        """Test that moderate content use case receives correct dependencies."""
        use_case = container_with_mocks.moderate_content_use_case()
        
        # Verify dependency is injected
        assert use_case._moderation_worker is not None


class TestContainerOverrides:
    """Test container override functionality."""
    
    def test_can_override_transcription_repository(self):
        """Test that transcription repository can be overridden."""
        container = Container()
        mock_repo = Mock()
        mock_worker = Mock()
        
        # Override all required dependencies to avoid validation errors
        container.transcription_repository.override(mock_repo)
        container.transcription_worker.override(mock_worker)
        use_case = container.transcribe_audio_use_case()
        
        assert use_case._repository is mock_repo
    
    def test_can_override_transcription_worker(self):
        """Test that transcription worker can be overridden."""
        container = Container()
        mock_worker = Mock()
        
        # Override all required dependencies
        container.transcription_repository.override(Mock())
        container.moderation_worker.override(Mock())
        container.transcription_worker.override(mock_worker)
        
        use_case = container.transcribe_audio_use_case()
        
        assert use_case._transcription_worker is mock_worker
    
    def test_can_override_cache(self):
        """Test that cache can be overridden."""
        container = Container()
        mock_cache = Mock()
        
        container.transcription_repository.override(Mock())
        container.cache.override(mock_cache)
        
        use_case = container.get_history_use_case()
        
        assert use_case._cache is mock_cache
    
    def test_overrides_can_be_reset(self):
        """Test that container overrides can be reset."""
        container = Container()
        mock_repo = Mock()
        
        # Override and get instance
        container.transcription_repository.override(mock_repo)
        resolved_before = container.transcription_repository()
        assert resolved_before is mock_repo
        
        # Reset by creating new container
        container = Container()
        resolved_after = container.transcription_repository()
        assert resolved_after is None  # Back to placeholder


class TestGlobalContainerInstance:
    """Test global container instance."""
    
    def test_global_container_exists(self):
        """Test that global container instance is created."""
        from dependency_injector import containers
        from app.infrastructure.config.container import container

        assert container is not None
        # Global container is DynamicContainer instance
        assert isinstance(container, (containers.DeclarativeContainer, containers.DynamicContainer))
    
    def test_global_container_has_all_providers(self):
        """Test that global container has all expected providers."""
        from app.infrastructure.config.container import container
        
        # Check services
        assert hasattr(container, 'audio_service')
        assert hasattr(container, 'session_service')
        
        # Check use cases
        assert hasattr(container, 'transcribe_audio_use_case')
        assert hasattr(container, 'get_history_use_case')
        assert hasattr(container, 'moderate_content_use_case')
