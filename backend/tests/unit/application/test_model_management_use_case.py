"""
Tests for Model Management Use Cases.

Tests for SwitchModelUseCase, GetModelStatusUseCase, and ListAvailableModelsUseCase.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from pathlib import Path

from app.application.use_cases.model_management import (
    SwitchModelUseCase,
    GetModelStatusUseCase,
    ListAvailableModelsUseCase
)
from app.domain.value_objects.model_config import ModelConfig
from app.domain.exceptions import (
    ValidationException,
    BusinessRuleViolationException,
    WorkerException
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_worker_manager():
    """Mock worker manager."""
    manager = AsyncMock()
    manager.switch_model = AsyncMock()
    manager.get_model_status = AsyncMock(return_value={
        "current_model": "zipformer-vi-30M",
        "model_ready": True,
        "moderation_enabled": False,
        "moderation_ready": False
    })
    return manager


@pytest.fixture
def valid_stt_config(tmp_path):
    """Create valid STT model configuration."""
    model_path = tmp_path / "zipformer"
    model_path.mkdir()
    return ModelConfig.for_zipformer(
        model_path=str(model_path),
        model_id="zipformer-test",
        device="cpu"
    )


@pytest.fixture
def valid_moderation_config(tmp_path):
    """Create valid moderation model configuration."""
    model_path = tmp_path / "visobert"
    model_path.mkdir()
    return ModelConfig.for_visobert_hsd(
        model_path=str(model_path),
        model_id="visobert-test",
        device="cpu"
    )


# ==================== SwitchModelUseCase Tests ====================

class TestSwitchModelUseCaseConstructor:
    """Tests for SwitchModelUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_worker_manager(self):
        """Test that worker_manager is required."""
        with pytest.raises(ValidationException) as exc_info:
            SwitchModelUseCase(worker_manager=None)
        
        assert "worker_manager" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_constructor_accepts_valid_manager(self, mock_worker_manager):
        """Test constructor with valid worker manager."""
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        assert use_case._worker_manager is mock_worker_manager


class TestSwitchModelUseCaseValidation:
    """Tests for SwitchModelUseCase validation logic."""
    
    @pytest.mark.asyncio
    async def test_validates_model_config_required(self, mock_worker_manager):
        """Test that model_config is required."""
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(ValidationException) as exc_info:
            await use_case.execute(model_config=None)
        
        assert "model_config" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validates_model_type_must_be_stt(
        self,
        mock_worker_manager,
        valid_moderation_config
    ):
        """Test that only STT models can be switched."""
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(BusinessRuleViolationException) as exc_info:
            await use_case.execute(model_config=valid_moderation_config)
        
        error = exc_info.value
        assert error.rule == "model_type_must_be_stt"
        assert "moderation" in error.reason.lower()


class TestSwitchModelUseCaseExecution:
    """Tests for SwitchModelUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_switches_model_successfully(
        self,
        mock_worker_manager,
        valid_stt_config
    ):
        """Test successful model switch."""
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        success = await use_case.execute(model_config=valid_stt_config)
        
        # Assert switch was called
        mock_worker_manager.switch_model.assert_called_once_with(valid_stt_config)
        
        # Assert status was checked
        mock_worker_manager.get_model_status.assert_called_once()
        
        # Assert success
        assert success is True
    
    @pytest.mark.asyncio
    async def test_fails_when_new_model_not_ready(
        self,
        mock_worker_manager,
        valid_stt_config
    ):
        """Test failure when new model doesn't start."""
        # Mock status showing model not ready
        mock_worker_manager.get_model_status = AsyncMock(return_value={
            "current_model": "zipformer-test",
            "model_ready": False
        })
        
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute(model_config=valid_stt_config)
        
        assert "failed to start" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_wraps_unexpected_exceptions(
        self,
        mock_worker_manager,
        valid_stt_config
    ):
        """Test that unexpected exceptions are wrapped as WorkerException."""
        # Mock switch_model to raise unexpected error
        mock_worker_manager.switch_model = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )
        
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute(model_config=valid_stt_config)
        
        assert "Model switch failed" in str(exc_info.value)
        assert exc_info.value.__cause__.__class__.__name__ == "RuntimeError"
    
    @pytest.mark.asyncio
    async def test_propagates_domain_exceptions(
        self,
        mock_worker_manager,
        valid_stt_config
    ):
        """Test that domain exceptions are re-raised as-is."""
        # Mock switch_model to raise WorkerException
        original_exception = WorkerException(
            worker_type="transcription",
            message="Worker crashed"
        )
        mock_worker_manager.switch_model = AsyncMock(side_effect=original_exception)
        
        use_case = SwitchModelUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute(model_config=valid_stt_config)
        
        # Should be the same exception instance
        assert exc_info.value is original_exception


# ==================== GetModelStatusUseCase Tests ====================

class TestGetModelStatusUseCaseConstructor:
    """Tests for GetModelStatusUseCase constructor."""
    
    @pytest.mark.asyncio
    async def test_constructor_requires_worker_manager(self):
        """Test that worker_manager is required."""
        with pytest.raises(ValidationException) as exc_info:
            GetModelStatusUseCase(worker_manager=None)
        
        assert "worker_manager" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_constructor_accepts_valid_manager(self, mock_worker_manager):
        """Test constructor with valid worker manager."""
        use_case = GetModelStatusUseCase(worker_manager=mock_worker_manager)
        assert use_case._worker_manager is mock_worker_manager


class TestGetModelStatusUseCaseExecution:
    """Tests for GetModelStatusUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_returns_model_status(self, mock_worker_manager):
        """Test successful status retrieval."""
        expected_status = {
            "current_model": "zipformer-vi-30M",
            "model_ready": True,
            "moderation_enabled": True,
            "moderation_ready": True
        }
        mock_worker_manager.get_model_status = AsyncMock(return_value=expected_status)
        
        use_case = GetModelStatusUseCase(worker_manager=mock_worker_manager)
        status = await use_case.execute()
        
        assert status == expected_status
        mock_worker_manager.get_model_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_returns_status_when_model_not_ready(self, mock_worker_manager):
        """Test status when model is not ready."""
        status_not_ready = {
            "current_model": None,
            "model_ready": False,
            "moderation_enabled": False,
            "moderation_ready": False
        }
        mock_worker_manager.get_model_status = AsyncMock(return_value=status_not_ready)
        
        use_case = GetModelStatusUseCase(worker_manager=mock_worker_manager)
        status = await use_case.execute()
        
        assert status["model_ready"] is False
        assert status["current_model"] is None
    
    @pytest.mark.asyncio
    async def test_wraps_exceptions_as_worker_exception(self, mock_worker_manager):
        """Test that exceptions are wrapped as WorkerException."""
        mock_worker_manager.get_model_status = AsyncMock(
            side_effect=RuntimeError("Status check failed")
        )
        
        use_case = GetModelStatusUseCase(worker_manager=mock_worker_manager)
        
        with pytest.raises(WorkerException) as exc_info:
            await use_case.execute()
        
        assert "Failed to get model status" in str(exc_info.value)
        assert exc_info.value.__cause__.__class__.__name__ == "RuntimeError"


# ==================== ListAvailableModelsUseCase Tests ====================

class TestListAvailableModelsUseCaseExecution:
    """Tests for ListAvailableModelsUseCase execution."""
    
    @pytest.mark.asyncio
    async def test_returns_list_of_models(self):
        """Test that use case returns available models."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        
        assert isinstance(models, list)
        assert len(models) > 0
    
    @pytest.mark.asyncio
    async def test_returns_stt_models(self):
        """Test that STT models are included."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        stt_models = [m for m in models if m["model_type"] == "stt"]
        
        assert len(stt_models) > 0
        assert any(m["model_id"] == "zipformer-vi-30M" for m in stt_models)
    
    @pytest.mark.asyncio
    async def test_returns_moderation_models(self):
        """Test that moderation models are included."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        mod_models = [m for m in models if m["model_type"] == "moderation"]
        
        assert len(mod_models) > 0
        assert any(m["model_id"] == "visobert-hsd-span" for m in mod_models)
    
    @pytest.mark.asyncio
    async def test_model_entries_have_required_fields(self):
        """Test that each model has required fields."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        required_fields = [
            "model_id",
            "model_type",
            "name",
            "description",
            "language",
            "default_path",
            "parameters"
        ]
        
        for model in models:
            for field in required_fields:
                assert field in model, f"Missing field '{field}' in model {model.get('model_id')}"
    
    @pytest.mark.asyncio
    async def test_returns_copy_not_original(self):
        """Test that returned list is a copy to prevent mutation."""
        use_case = ListAvailableModelsUseCase()
        
        models1 = await use_case.execute()
        models2 = await use_case.execute()
        
        # Modify first result
        models1[0]["model_id"] = "MODIFIED"
        
        # Second result should be unaffected
        assert models2[0]["model_id"] != "MODIFIED"
    
    @pytest.mark.asyncio
    async def test_zipformer_model_has_correct_parameters(self):
        """Test that Zipformer model has expected parameters."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        zipformer = next(m for m in models if m["model_id"] == "zipformer-vi-30M")
        
        assert zipformer["model_type"] == "stt"
        assert zipformer["language"] == "vi"
        assert "sample_rate" in zipformer["parameters"]
        assert zipformer["parameters"]["sample_rate"] == 16000
    
    @pytest.mark.asyncio
    async def test_visobert_model_has_correct_parameters(self):
        """Test that ViSoBERT model has expected parameters."""
        use_case = ListAvailableModelsUseCase()
        
        models = await use_case.execute()
        visobert = next(m for m in models if m["model_id"] == "visobert-hsd-span")
        
        assert visobert["model_type"] == "moderation"
        assert visobert["language"] == "vi"
        assert "threshold" in visobert["parameters"]
        assert "detect_spans" in visobert["parameters"]
