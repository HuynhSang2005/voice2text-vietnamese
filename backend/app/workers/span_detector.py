"""
Span Detector Worker
=====================
Worker for ViSoBERT-HSD-Span hate speech span detection using ONNX Runtime.

This worker uses a Token Classification model (BIO tagging) to detect the specific
toxic spans within text that has been flagged by the hate speech classifier.

Model:
    - Name: visolex/visobert-hsd-span
    - Labels: O (0), B-T (1), I-T (2)
    - Max Length: 64 tokens
    - Dataset: ViHOS (Vietnamese Hate and Offensive Spans)

Example:
    Input: "thằng ngu này sao mà chậm quá"
    Output: [{"text": "thằng ngu", "start": 0, "end": 9}]
"""
import os
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.workers.base import BaseWorker
from app.core.config import settings


class SpanDetectorWorker(BaseWorker):
    """Worker for ViSoBERT-HSD-Span hate speech span detection using ONNX Runtime.
    
    This worker loads the quantized INT8 ONNX model for optimal performance.
    Falls back to FP32 ONNX if INT8 is not available.
    
    BIO Tagging Scheme:
        - O (0): Outside of toxic span
        - B-T (1): Beginning of toxic span
        - I-T (2): Inside of toxic span (continuation)
    """
    
    # Label mapping for BIO scheme
    LABEL_MAP = {
        0: "O",     # Outside
        1: "B-T",   # Beginning of toxic span
        2: "I-T"    # Inside toxic span
    }
    
    # Minimum text length to process (skip very short texts)
    MIN_TEXT_LENGTH = 3
    
    # Maximum sequence length (model trained with this constraint)
    MAX_SEQUENCE_LENGTH = 64
    
    def __init__(self, input_queue, output_queue, model_name: str = "visobert-hsd-span"):
        super().__init__(input_queue, output_queue, model_name)
        self.tokenizer = None
        self.model = None
    
    def load_model(self) -> None:
        """Load ONNX model and tokenizer.
        
        Prefers INT8 quantized model for better performance.
        Falls back to FP32 ONNX if INT8 is not available.
        """
        from optimum.onnxruntime import ORTModelForTokenClassification
        from transformers import AutoTokenizer
        
        # Get model paths
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        model_base = os.path.join(base_dir, settings.MODEL_STORAGE_PATH, "visobert-hsd-span")
        
        int8_path = os.path.join(model_base, "onnx-int8")
        onnx_path = os.path.join(model_base, "onnx")
        
        # Prefer INT8 quantized model
        if os.path.exists(int8_path) and os.listdir(int8_path):
            model_path = int8_path
            # INT8 quantized model uses 'model_quantized.onnx' filename
            file_name = "model_quantized.onnx"
            self.logger.info(f"Loading INT8 quantized span detector from {model_path}")
        elif os.path.exists(onnx_path) and os.listdir(onnx_path):
            model_path = onnx_path
            file_name = "model.onnx"
            self.logger.info(f"Loading FP32 ONNX span detector from {model_path}")
        else:
            raise FileNotFoundError(
                f"ViSoBERT-HSD-Span model not found. "
                f"Please run 'python scripts/setup_hsd_span_model.py' to download and convert the model."
            )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Load ONNX model with correct file name
        self.model = ORTModelForTokenClassification.from_pretrained(
            model_path,
            file_name=file_name,
            provider="CPUExecutionProvider"
        )
        
        self.logger.info(f"ViSoBERT-HSD-Span model loaded successfully from {model_path}")
    
    def process(self, item: Any) -> None:
        """Process text item and output span detection result.
        
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
            result = self._detect_spans(text, request_id)
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            self.output_queue.put(result)
            
        except Exception as e:
            self.logger.error(f"Span detection error: {e}", exc_info=True)
            self.output_queue.put({
                "request_id": request_id,
                "error": str(e),
                "detected_keywords": [],
                "spans": []
            })
    
    def _detect_spans(self, text: str, request_id: Optional[str] = None) -> Dict:
        """Detect toxic spans in text using BIO tagging.
        
        Args:
            text: Text to analyze
            request_id: Optional request ID for tracking
            
        Returns:
            Result dictionary with detected_keywords and spans
        """
        import torch
        
        # Tokenize input with offset mapping for character-level extraction
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.MAX_SEQUENCE_LENGTH,
            padding="max_length",
            return_offsets_mapping=True
        )
        
        # Extract offset mapping before inference (not needed by model)
        offset_mapping = inputs.pop("offset_mapping")[0].tolist()
        
        # Run inference
        outputs = self.model(**inputs)
        logits = outputs.logits
        
        # Get predictions
        predictions = logits.argmax(dim=-1)[0].tolist()
        
        # Get attention mask to identify valid tokens
        attention_mask = inputs["attention_mask"][0].tolist()
        
        # Extract spans using BIO logic
        spans = self._extract_spans(text, predictions, offset_mapping, attention_mask)
        
        # Extract unique keywords
        detected_keywords = list(dict.fromkeys([s["text"] for s in spans]))
        
        return {
            "request_id": request_id,
            "detected_keywords": detected_keywords,
            "spans": spans,
            "text_length": len(text)
        }
    
    def _extract_spans(
        self,
        text: str,
        predictions: List[int],
        offset_mapping: List[Tuple[int, int]],
        attention_mask: List[int]
    ) -> List[Dict[str, any]]:
        """Extract span text from BIO predictions.
        
        BIO Logic:
            - B-T (1): Start a new toxic span
            - I-T (2): Continue the current toxic span
            - O (0): End current span (if any)
        
        Args:
            text: Original input text
            predictions: List of predicted label IDs (0=O, 1=B-T, 2=I-T)
            offset_mapping: List of (start, end) character offsets
            attention_mask: List indicating valid tokens (1) vs padding (0)
            
        Returns:
            List of span dictionaries with text, start, end
        """
        spans = []
        current_span_start = None
        current_span_end = None
        
        for idx, (pred, offsets, mask) in enumerate(zip(predictions, offset_mapping, attention_mask)):
            # Skip padding tokens
            if mask == 0:
                continue
                
            start, end = offsets
            
            # Skip special tokens (CLS, SEP, PAD have offset (0, 0))
            if start == 0 and end == 0:
                continue
            
            label = self.LABEL_MAP.get(pred, "O")
            
            if label == "B-T":
                # Start new span - first save current span if exists
                if current_span_start is not None:
                    span_text = text[current_span_start:current_span_end].strip()
                    if span_text:
                        spans.append({
                            "text": span_text,
                            "start": current_span_start,
                            "end": current_span_end
                        })
                # Start new span
                current_span_start = start
                current_span_end = end
                
            elif label == "I-T":
                # Continue span
                if current_span_start is not None:
                    # Extend current span
                    current_span_end = end
                else:
                    # I-T without B-T, treat as B-T (recovery)
                    current_span_start = start
                    current_span_end = end
                    
            else:  # O
                # End current span if exists
                if current_span_start is not None:
                    span_text = text[current_span_start:current_span_end].strip()
                    if span_text:
                        spans.append({
                            "text": span_text,
                            "start": current_span_start,
                            "end": current_span_end
                        })
                    current_span_start = None
                    current_span_end = None
        
        # Don't forget last span if text ends with toxic content
        if current_span_start is not None:
            span_text = text[current_span_start:current_span_end].strip()
            if span_text:
                spans.append({
                    "text": span_text,
                    "start": current_span_start,
                    "end": current_span_end
                })
        
        return spans
