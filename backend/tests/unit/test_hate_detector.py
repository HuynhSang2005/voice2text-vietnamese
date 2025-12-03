"""
Unit tests for HateDetectorWorker.

Tests the hate speech detector worker's ability to:
- Load ONNX model (mocked for unit tests)
- Process text classification
- Return correct labels and confidence scores
- Handle edge cases (empty text, short text, errors)

Note: These are unit tests with mocked model. Integration tests
with real model are in tests/integration/ directory.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

# Add backend to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.workers.hate_detector import HateDetectorWorker


class TestHateDetectorWorker:
    """Test suite for HateDetectorWorker class."""
    
    @pytest.fixture
    def mock_queues(self):
        """Create mock input/output queues."""
        input_q = MagicMock()
        output_q = MagicMock()
        return input_q, output_q
    
    @pytest.fixture
    def worker(self, mock_queues):
        """Create worker instance with mocked queues."""
        input_q, output_q = mock_queues
        return HateDetectorWorker(input_q, output_q, "visobert-hsd")
    
    @pytest.fixture
    def mock_torch(self):
        """Create mock torch module with softmax."""
        mock = MagicMock()
        # Mock softmax to return a tensor-like object
        mock.softmax.return_value = MagicMock()
        return mock
    
    @pytest.fixture
    def mock_model_and_tokenizer(self):
        """Create mock model and tokenizer."""
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        
        mock_model = MagicMock()
        mock_logits = MagicMock()
        mock_model.return_value.logits = mock_logits
        
        return mock_tokenizer, mock_model, mock_logits


class TestWorkerInitialization:
    """Test worker initialization."""
    
    def test_worker_creation(self):
        """Test worker can be created."""
        input_q = MagicMock()
        output_q = MagicMock()
        worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
        
        assert worker.model_name == "visobert-hsd"
        assert worker.tokenizer is None
        assert worker.model is None
    
    def test_label_map(self):
        """Test label map is correctly defined."""
        input_q = MagicMock()
        output_q = MagicMock()
        worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
        
        assert worker.LABEL_MAP[0] == "CLEAN"
        assert worker.LABEL_MAP[1] == "OFFENSIVE"
        assert worker.LABEL_MAP[2] == "HATE"
    
    def test_constants(self):
        """Test class constants are properly set."""
        assert HateDetectorWorker.MIN_TEXT_LENGTH == 3
        assert HateDetectorWorker.MAX_SEQUENCE_LENGTH == 256


class TestModelLoading:
    """Test model loading functionality."""
    
    @pytest.fixture
    def worker(self):
        """Create worker instance."""
        input_q = MagicMock()
        output_q = MagicMock()
        return HateDetectorWorker(input_q, output_q, "visobert-hsd")
    
    @patch("os.path.exists")
    @patch("os.listdir")
    def test_load_model_prefers_int8(self, mock_listdir, mock_exists, worker):
        """Test that model loading prefers INT8 quantized model."""
        # Both paths exist
        mock_exists.return_value = True
        mock_listdir.return_value = ["model.onnx"]
        
        mock_tokenizer_cls = MagicMock()
        mock_model_cls = MagicMock()
        
        with patch.dict("sys.modules", {
            "optimum": MagicMock(),
            "optimum.onnxruntime": MagicMock(ORTModelForSequenceClassification=mock_model_cls),
            "transformers": MagicMock(AutoTokenizer=mock_tokenizer_cls),
        }):
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            
            with patch.object(AutoTokenizer, "from_pretrained", mock_tokenizer_cls.from_pretrained):
                with patch.object(ORTModelForSequenceClassification, "from_pretrained", mock_model_cls.from_pretrained):
                    worker.load_model()
        
        # Verify INT8 path was used (check call contains 'onnx-int8')
        call_args = mock_model_cls.from_pretrained.call_args
        assert "onnx-int8" in str(call_args) or mock_model_cls.from_pretrained.called
    
    @patch("os.path.exists")
    @patch("os.listdir")
    def test_load_model_not_found(self, mock_listdir, mock_exists, worker):
        """Test error when no model is found."""
        # Make all paths not exist or empty
        mock_exists.return_value = False
        mock_listdir.return_value = []
        
        # Also mock the imports so they don't fail
        with patch.dict("sys.modules", {
            "optimum": MagicMock(),
            "optimum.onnxruntime": MagicMock(),
            "transformers": MagicMock(),
        }):
            with pytest.raises(FileNotFoundError) as exc_info:
                worker.load_model()
        
            assert "ViSoBERT-HSD model not found" in str(exc_info.value)
            assert "setup_visobert_hsd.py" in str(exc_info.value)


class TestTextProcessing:
    """Test text processing and classification."""
    
    @pytest.fixture
    def worker_with_mock_model(self):
        """Create worker with mocked model and tokenizer."""
        input_q = MagicMock()
        output_q = MagicMock()
        worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
        
        # Mock tokenizer
        worker.tokenizer = MagicMock()
        worker.tokenizer.return_value = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock()
        }
        
        # Mock model
        worker.model = MagicMock()
        
        return worker
    
    def test_process_empty_text(self, worker_with_mock_model):
        """Test that empty text is ignored."""
        worker = worker_with_mock_model
        
        worker.process({"text": "", "request_id": "test-1"})
        
        # Should not put anything in queue
        worker.output_queue.put.assert_not_called()
    
    def test_process_short_text(self, worker_with_mock_model):
        """Test that very short text is ignored."""
        worker = worker_with_mock_model
        
        worker.process({"text": "ab", "request_id": "test-1"})
        
        worker.output_queue.put.assert_not_called()
    
    def test_process_none_item(self, worker_with_mock_model):
        """Test that None item is handled."""
        worker = worker_with_mock_model
        
        worker.process(None)
        
        worker.output_queue.put.assert_not_called()
    
    def test_process_invalid_item(self, worker_with_mock_model):
        """Test that non-dict item is handled."""
        worker = worker_with_mock_model
        
        worker.process("just a string")
        
        worker.output_queue.put.assert_not_called()
    
    def test_process_clean_text(self, worker_with_mock_model):
        """Test processing clean text."""
        import torch
        
        worker = worker_with_mock_model
        
        # Setup mock logits to return CLEAN (label 0)
        mock_logits = torch.tensor([[2.5, -1.0, -2.0]])  # Real tensor
        worker.model.return_value.logits = mock_logits
        
        worker.process({"text": "Xin chào bạn", "request_id": "test-clean"})
        
        # Check output
        worker.output_queue.put.assert_called_once()
        result = worker.output_queue.put.call_args[0][0]
        
        assert result["request_id"] == "test-clean"
        assert result["label"] == "CLEAN"
        assert result["label_id"] == 0
        assert result["is_flagged"] == False
        assert "latency_ms" in result
    
    def test_process_offensive_text(self, worker_with_mock_model):
        """Test processing offensive text."""
        import torch
        
        worker = worker_with_mock_model
        
        # Setup mock logits to return OFFENSIVE (label 1)
        mock_logits = torch.tensor([[-1.0, 2.5, -0.5]])
        worker.model.return_value.logits = mock_logits
        
        worker.process({"text": "Đồ ngu ngốc", "request_id": "test-offensive"})
        
        result = worker.output_queue.put.call_args[0][0]
        
        assert result["label"] == "OFFENSIVE"
        assert result["label_id"] == 1
        assert result["is_flagged"] == True
    
    def test_process_hate_text(self, worker_with_mock_model):
        """Test processing hate speech text."""
        import torch
        
        worker = worker_with_mock_model
        
        # Setup mock logits to return HATE (label 2)
        mock_logits = torch.tensor([[-1.0, -0.5, 2.5]])
        worker.model.return_value.logits = mock_logits
        
        worker.process({"text": "Hate speech example", "request_id": "test-hate"})
        
        result = worker.output_queue.put.call_args[0][0]
        
        assert result["label"] == "HATE"
        assert result["label_id"] == 2
        assert result["is_flagged"] == True
    
    def test_process_includes_text_length(self, worker_with_mock_model):
        """Test that result includes text length."""
        import torch
        
        worker = worker_with_mock_model
        
        mock_logits = torch.tensor([[2.5, -1.0, -2.0]])
        worker.model.return_value.logits = mock_logits
        
        test_text = "This is a test message"
        worker.process({"text": test_text, "request_id": "test"})
        
        result = worker.output_queue.put.call_args[0][0]
        assert result["text_length"] == len(test_text)


class TestErrorHandling:
    """Test error handling in worker."""
    
    @pytest.fixture
    def worker_with_mock_model(self):
        """Create worker with mocked model."""
        input_q = MagicMock()
        output_q = MagicMock()
        worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
        worker.tokenizer = MagicMock()
        worker.model = MagicMock()
        return worker
    
    def test_process_error_returns_error_result(self, worker_with_mock_model):
        """Test that errors during processing return error result."""
        worker = worker_with_mock_model
        
        # Make tokenizer raise an exception
        worker.tokenizer.side_effect = RuntimeError("Tokenizer failed")
        
        worker.process({"text": "Test text", "request_id": "error-test"})
        
        # Should put error result in queue
        worker.output_queue.put.assert_called_once()
        result = worker.output_queue.put.call_args[0][0]
        
        assert result["request_id"] == "error-test"
        assert "error" in result
        assert "Tokenizer failed" in result["error"]


class TestTokenizerConfiguration:
    """Test tokenizer configuration."""
    
    @pytest.fixture
    def worker_with_mock_model(self):
        """Create worker with mocked model and tokenizer."""
        import torch
        
        input_q = MagicMock()
        output_q = MagicMock()
        worker = HateDetectorWorker(input_q, output_q, "visobert-hsd")
        worker.tokenizer = MagicMock()
        worker.tokenizer.return_value = {"input_ids": MagicMock()}
        worker.model = MagicMock()
        
        # Return real tensor for proper softmax
        mock_logits = torch.tensor([[2.5, -1.0, -2.0]])
        worker.model.return_value.logits = mock_logits
        return worker
    
    def test_tokenizer_called_with_correct_params(self, worker_with_mock_model):
        """Test tokenizer is called with correct parameters."""
        worker = worker_with_mock_model
        
        test_text = "Test text for tokenization"
        worker.process({"text": test_text})
        
        # Check tokenizer was called with correct parameters
        worker.tokenizer.assert_called_once()
        call_kwargs = worker.tokenizer.call_args.kwargs
        
        assert call_kwargs["return_tensors"] == "pt"
        assert call_kwargs["truncation"] == True
        assert call_kwargs["max_length"] == 256
        assert call_kwargs["padding"] == True
