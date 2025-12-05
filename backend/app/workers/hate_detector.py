"""
HateDetectorWorker - ViSoBERT-HSD Hate Speech Detection Worker.

This worker runs ViSoBERT-HSD model for Vietnamese hate speech detection.
It uses ONNX Runtime for optimized inference.

Labels:
    0: CLEAN - Normal, clean text
    1: OFFENSIVE - Offensive/toxic language
    2: HATE - Hate speech targeting groups

Usage:
    The worker receives text items from input_queue and outputs
    classification results to output_queue.

    Input format:
        {
            "text": "text to classify",
            "request_id": "optional-id-for-tracking"
        }
    
    Output format:
        {
            "request_id": "...",
            "label": "CLEAN" | "OFFENSIVE" | "HATE",
            "label_id": 0 | 1 | 2,
            "confidence": 0.0-1.0,
            "is_flagged": True | False,
            "latency_ms": float
        }
"""

import os
import time
from typing import Any, Dict, Optional, List

from app.workers.base import BaseWorker
from app.core.config import settings


class HateDetectorWorker(BaseWorker):
    """Worker for ViSoBERT-HSD hate speech detection using ONNX Runtime.
    
    This worker loads the quantized INT8 ONNX model for optimal performance.
    Falls back to FP32 ONNX if INT8 is not available.
    """
    
    # Label mapping from model output
    LABEL_MAP = {
        0: "CLEAN",
        1: "OFFENSIVE", 
        2: "HATE"
    }
    
    # Minimum text length to process (skip very short texts)
    MIN_TEXT_LENGTH = 3
    
    # Maximum sequence length for tokenizer
    MAX_SEQUENCE_LENGTH = 256
    
    def __init__(self, input_queue, output_queue, model_name: str = "visobert-hsd"):
        super().__init__(input_queue, output_queue, model_name)
        self.tokenizer = None
        self.model = None
    
    def load_model(self) -> None:
        """Load ONNX model and tokenizer.
        
        Prefers INT8 quantized model for better performance.
        Falls back to FP32 ONNX if INT8 is not available.
        """
        from optimum.onnxruntime import ORTModelForSequenceClassification
        from transformers import AutoTokenizer
        
        # Get model paths
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        model_base = os.path.join(base_dir, settings.MODEL_STORAGE_PATH, "visobert-hsd")
        
        int8_path = os.path.join(model_base, "onnx-int8")
        onnx_path = os.path.join(model_base, "onnx")
        
        # Prefer INT8 quantized model
        if os.path.exists(int8_path) and os.listdir(int8_path):
            model_path = int8_path
            # INT8 quantized model uses 'model_quantized.onnx' filename
            file_name = "model_quantized.onnx"
            self.logger.info(f"Loading INT8 quantized model from {model_path}")
        elif os.path.exists(onnx_path) and os.listdir(onnx_path):
            model_path = onnx_path
            file_name = "model.onnx"
            self.logger.info(f"Loading FP32 ONNX model from {model_path}")
        else:
            raise FileNotFoundError(
                f"ViSoBERT-HSD model not found. "
                f"Please run 'python scripts/setup_visobert_hsd.py' to download and convert the model."
            )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Load ONNX model with correct file name
        self.model = ORTModelForSequenceClassification.from_pretrained(
            model_path,
            file_name=file_name,
            provider="CPUExecutionProvider"
        )
        
        self.logger.info(f"ViSoBERT-HSD model loaded successfully from {model_path}")
    
    def process(self, item: Any) -> None:
        """Process text item and output classification result.
        
        Args:
            item: Dictionary with 'text' and optional 'request_id'
        """
        if not item or not isinstance(item, dict):
            return
        
        text = item.get("text", "")
        request_id = item.get("request_id")
        
        # Skip empty or very short texts
        if not text or len(text.strip()) < self.MIN_TEXT_LENGTH:
            return
        
        start_time = time.perf_counter()
        
        try:
            result = self._classify_text(text, request_id)
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            self.output_queue.put(result)
            
        except Exception as e:
            self.logger.error(f"Detection error: {e}", exc_info=True)
            self.output_queue.put({
                "request_id": request_id,
                "error": str(e)
            })
    
    def _classify_text(self, text: str, request_id: Optional[str] = None) -> Dict:
        """Classify text and return structured result with detected keywords.
        
        Args:
            text: Text to classify
            request_id: Optional request ID for tracking
            
        Returns:
            Classification result dictionary including detected bad keywords
        """
        import torch
        
        # Tokenize input
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.MAX_SEQUENCE_LENGTH,
            padding=True
        )
        
        # Run inference
        outputs = self.model(**inputs)
        logits = outputs.logits
        
        # Calculate probabilities and get prediction
        probabilities = torch.softmax(logits, dim=-1)
        predicted_label = logits.argmax(dim=-1).item()
        confidence = probabilities[0][predicted_label].item()
        
        # Build result - include text for span detector to use
        return {
            "request_id": request_id,
            "text": text,  # Include original text for span detection
            "label": self.LABEL_MAP[predicted_label],
            "label_id": predicted_label,
            "confidence": round(confidence, 4),
            "is_flagged": predicted_label > 0,  # True for OFFENSIVE or HATE
            "text_length": len(text),
            "detected_keywords": []  # Will be populated by visobert-hsd-span
        }
