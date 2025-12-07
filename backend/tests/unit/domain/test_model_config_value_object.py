"""Unit tests for ModelConfig value object."""
import pytest
from pathlib import Path
from app.domain.value_objects.model_config import ModelConfig


class TestModelConfigValueObject:
    """Test suite for ModelConfig value object."""
    
    @pytest.fixture
    def valid_model_path(self, tmp_path):
        """Create a temporary valid model path."""
        model_dir = tmp_path / "test_model"
        model_dir.mkdir()
        return str(model_dir)
    
    def test_create_valid_model_config(self, valid_model_path):
        """Test creating model config with valid parameters."""
        config = ModelConfig(
            model_id="test-model",
            model_type="stt",
            model_path=valid_model_path,
            language="vi",
            device="cpu",
        )
        
        assert config.model_id == "test-model"
        assert config.model_type == "stt"
        assert config.model_path == valid_model_path
        assert config.language == "vi"
        assert config.device == "cpu"
        assert config.parameters == {}
    
    def test_create_with_parameters(self, valid_model_path):
        """Test creating model config with custom parameters."""
        params = {"sample_rate": 16000, "num_threads": 4}
        config = ModelConfig(
            model_id="test-model",
            model_type="stt",
            model_path=valid_model_path,
            parameters=params,
        )
        
        assert config.parameters == params
    
    def test_validation_invalid_model_type(self, valid_model_path):
        """Test validation rejects invalid model types."""
        with pytest.raises(ValueError, match="Invalid model_type"):
            ModelConfig(
                model_id="test",
                model_type="invalid",
                model_path=valid_model_path,
            )
    
    def test_validation_invalid_device(self, valid_model_path):
        """Test validation rejects invalid devices."""
        with pytest.raises(ValueError, match="Invalid device"):
            ModelConfig(
                model_id="test",
                model_type="stt",
                model_path=valid_model_path,
                device="tpu",
            )
    
    def test_validation_unsupported_language(self, valid_model_path):
        """Test validation rejects unsupported languages."""
        with pytest.raises(ValueError, match="Unsupported language"):
            ModelConfig(
                model_id="test",
                model_type="stt",
                model_path=valid_model_path,
                language="fr",
            )
    
    def test_validation_nonexistent_path(self):
        """Test validation rejects nonexistent model paths."""
        with pytest.raises(ValueError, match="path does not exist"):
            ModelConfig(
                model_id="test",
                model_type="stt",
                model_path="/nonexistent/path",
            )
    
    def test_is_stt_model_returns_true(self, valid_model_path):
        """Test is_stt_model() returns True for STT models."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        assert config.is_stt_model() is True
    
    def test_is_stt_model_returns_false(self, valid_model_path):
        """Test is_stt_model() returns False for non-STT models."""
        config = ModelConfig(
            model_id="test",
            model_type="moderation",
            model_path=valid_model_path,
        )
        
        assert config.is_stt_model() is False
    
    def test_is_moderation_model_returns_true(self, valid_model_path):
        """Test is_moderation_model() returns True for moderation models."""
        config = ModelConfig(
            model_id="test",
            model_type="moderation",
            model_path=valid_model_path,
        )
        
        assert config.is_moderation_model() is True
    
    def test_is_moderation_model_returns_false(self, valid_model_path):
        """Test is_moderation_model() returns False for non-moderation models."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        assert config.is_moderation_model() is False
    
    def test_uses_gpu_returns_true_for_cuda(self, valid_model_path):
        """Test uses_gpu() returns True for CUDA device."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            device="cuda",
        )
        
        assert config.uses_gpu() is True
    
    def test_uses_gpu_returns_false_for_cpu(self, valid_model_path):
        """Test uses_gpu() returns False for CPU device."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            device="cpu",
        )
        
        assert config.uses_gpu() is False
    
    def test_is_vietnamese_returns_true(self, valid_model_path):
        """Test is_vietnamese() returns True for Vietnamese models."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            language="vi",
        )
        
        assert config.is_vietnamese() is True
    
    def test_is_vietnamese_returns_false(self, valid_model_path):
        """Test is_vietnamese() returns False for non-Vietnamese models."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            language="en",
        )
        
        assert config.is_vietnamese() is False
    
    def test_get_parameter_returns_value(self, valid_model_path):
        """Test get_parameter() returns correct value."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            parameters={"sample_rate": 16000},
        )
        
        assert config.get_parameter("sample_rate") == 16000
    
    def test_get_parameter_returns_default(self, valid_model_path):
        """Test get_parameter() returns default for missing keys."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        assert config.get_parameter("missing_key", "default") == "default"
    
    def test_has_parameter_returns_true(self, valid_model_path):
        """Test has_parameter() returns True for existing parameters."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            parameters={"sample_rate": 16000},
        )
        
        assert config.has_parameter("sample_rate") is True
    
    def test_has_parameter_returns_false(self, valid_model_path):
        """Test has_parameter() returns False for missing parameters."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        assert config.has_parameter("missing") is False
    
    def test_to_dict_includes_all_fields(self, valid_model_path):
        """Test to_dict() includes all configuration fields."""
        config = ModelConfig(
            model_id="test-model",
            model_type="stt",
            model_path=valid_model_path,
            language="vi",
            device="cpu",
            parameters={"sample_rate": 16000},
        )
        
        result = config.to_dict()
        
        assert result["model_id"] == "test-model"
        assert result["model_type"] == "stt"
        assert result["model_path"] == valid_model_path
        assert result["language"] == "vi"
        assert result["device"] == "cpu"
        assert result["parameters"] == {"sample_rate": 16000}
        assert result["is_stt"] is True
        assert result["is_moderation"] is False
        assert result["uses_gpu"] is False
    
    def test_for_zipformer_factory_method(self, valid_model_path):
        """Test for_zipformer() factory method."""
        config = ModelConfig.for_zipformer(
            model_path=valid_model_path,
            model_id="zipformer-test",
            device="cpu",
        )
        
        assert config.model_id == "zipformer-test"
        assert config.model_type == "stt"
        assert config.language == "vi"
        assert config.device == "cpu"
        assert config.get_parameter("sample_rate") == 16000
        assert config.get_parameter("num_threads") == 4
        assert config.get_parameter("decoding_method") == "greedy_search"
    
    def test_for_zipformer_default_model_id(self, valid_model_path):
        """Test for_zipformer() uses default model_id."""
        config = ModelConfig.for_zipformer(model_path=valid_model_path)
        
        assert config.model_id == "zipformer-vi-30M"
    
    def test_for_zipformer_custom_parameters(self, valid_model_path):
        """Test for_zipformer() with custom parameters."""
        config = ModelConfig.for_zipformer(
            model_path=valid_model_path,
            sample_rate=8000,
            custom_param="value",
        )
        
        assert config.get_parameter("sample_rate") == 8000
        assert config.get_parameter("custom_param") == "value"
    
    def test_for_visobert_hsd_factory_method(self, valid_model_path):
        """Test for_visobert_hsd() factory method."""
        config = ModelConfig.for_visobert_hsd(
            model_path=valid_model_path,
            model_id="visobert-test",
            device="cpu",
        )
        
        assert config.model_id == "visobert-test"
        assert config.model_type == "moderation"
        assert config.language == "vi"
        assert config.device == "cpu"
        assert config.get_parameter("max_length") == 256
        assert config.get_parameter("threshold") == 0.5
        assert config.get_parameter("detect_spans") is True
    
    def test_for_visobert_hsd_default_model_id(self, valid_model_path):
        """Test for_visobert_hsd() uses default model_id."""
        config = ModelConfig.for_visobert_hsd(model_path=valid_model_path)
        
        assert config.model_id == "visobert-hsd-span"
    
    def test_for_visobert_hsd_custom_parameters(self, valid_model_path):
        """Test for_visobert_hsd() with custom parameters."""
        config = ModelConfig.for_visobert_hsd(
            model_path=valid_model_path,
            threshold=0.7,
            custom_param="value",
        )
        
        assert config.get_parameter("threshold") == 0.7
        assert config.get_parameter("custom_param") == "value"
    
    def test_immutability(self, valid_model_path):
        """Test that model config is immutable (frozen)."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        with pytest.raises(AttributeError):
            config.device = "cuda"  # type: ignore
    
    def test_parameters_default_to_empty_dict(self, valid_model_path):
        """Test parameters default to empty dict when None."""
        config = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
            parameters=None,
        )
        
        assert config.parameters == {}
    
    def test_equality_based_on_all_fields(self, valid_model_path):
        """Test equality compares all fields."""
        config1 = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        config2 = ModelConfig(
            model_id="test",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        config3 = ModelConfig(
            model_id="different",
            model_type="stt",
            model_path=valid_model_path,
        )
        
        assert config1 == config2
        assert config1 != config3
    
    def test_supported_model_types(self, valid_model_path):
        """Test all supported model types."""
        for model_type in ["stt", "moderation"]:
            config = ModelConfig(
                model_id="test",
                model_type=model_type,
                model_path=valid_model_path,
            )
            assert config.model_type == model_type
    
    def test_supported_devices(self, valid_model_path):
        """Test all supported devices."""
        for device in ["cpu", "cuda"]:
            config = ModelConfig(
                model_id="test",
                model_type="stt",
                model_path=valid_model_path,
                device=device,
            )
            assert config.device == device
    
    def test_supported_languages(self, valid_model_path):
        """Test all supported languages."""
        for language in ["vi", "en"]:
            config = ModelConfig(
                model_id="test",
                model_type="stt",
                model_path=valid_model_path,
                language=language,
            )
            assert config.language == language
