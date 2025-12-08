"""
Infrastructure Layer - Span Detector Moderation Worker

Async wrapper for ViSoBERT-HSD-Span hate speech detection model.
Implements IModerationWorker protocol using multiprocessing.
"""


import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.domain.entities.moderation_result import ModerationResult
from app.infrastructure.workers.base_worker import BaseWorker


logger = logging.getLogger(__name__)


class SpanDetectorWorker(BaseWorker):
    """
    ViSoBERT-HSD-Span hate speech detection worker.

    Uses Optimum ONNX Runtime for efficient NLP inference.
    Implements BIO tagging with fallback rule-based detection.

    Model: ViSoBERT-HSD-Span (Vietnamese hate speech detection)

    Labels:
        - CLEAN: No offensive content
        - OFFENSIVE: Contains offensive language
        - HATE: Contains hate speech
    """

    # BIO tag to label mapping
    LABEL_MAP = {
        0: "O",  # Outside
        1: "B-HATE",  # Begin hate
        2: "I-HATE",  # Inside hate
    }

    # Model configuration
    MIN_TEXT_LENGTH = 3
    MAX_SEQUENCE_LENGTH = 512

    # Fallback offensive phrases for rule-based detection
    FALLBACK_BAD_PHRASES = [
        "địt",
        "đụ",
        "đéo",
        "đm",
        "dm",
        "đmm",
        "lồn",
        "lon",
        "cặc",
        "cak",
        "vcl",
        "vkl",
        "vãi",
        "chó",
        "loz",
        "cc",
        "concac",
        "đỉa",
        "súc vật",
        "chết đi",
        "chết tiệt",
        "đồ ngu",
        "đồ khốn",
        "khốn nạn",
        "thối tha",
        "đồ dơ",
        "đồ bẩn",
        "ngu như",
        "ngu ngốc",
        "óc",
        "não",
        "chửi",
        "mẹ mày",
        "cha mày",
        "bố mày",
        "lão già",
        "con rắn",
        "đồ phản bội",
        "đồ bội bạc",
        "đồ phản",
        "phản đồ",
        "phản quốc",
        "phản động",
        "đồ bán nước",
        "bán nước",
        "bán rẻ",
        "tao thích",
        "cút đi",
        "câm mồm",
        "im mồm",
        "mồm",
        "câm đi",
        "thằng",
        "con",
        "đồ",
        "đéo biết",
    ]

    # Moderation label mapping (BIO tags → final label)
    MODERATION_LABEL_MAP = {
        "HATE": "HATE",
        "OFFENSIVE": "OFFENSIVE",
        "CLEAN": "CLEAN",
    }

    # Severe hate speech indicators
    SEVERE_HATE_INDICATORS = [
        "chết đi",
        "chết tiệt",
        "giết",
        "đánh đập",
        "phản quốc",
        "phản động",
        "bán nước",
        "đồ phản bội",
        "súc vật",
        "đồ bội bạc",
        "con rắn",
        "khốn nạn",
        "địt mẹ",
        "đụ má",
        "lồn mẹ",
    ]

    # Mild offensive indicators
    MILD_OFFENSIVE_INDICATORS = [
        "ngu",
        "óc chó",
        "đồ ngu",
        "ngu ngốc",
        "chó",
        "đéo",
        "vkl",
        "vcl",
        "thằng",
        "con",
        "mồm",
    ]

    def __init__(
        self,
        model_name: str = "visobert-hsd-span",
        queue_timeout: float = 1.0,
        stop_timeout: float = 5.0,
    ):
        """
        Initialize Span Detector worker.

        Args:
            model_name: Name for logging (default: "visobert-hsd-span")
            queue_timeout: Queue operation timeout (seconds)
            stop_timeout: Shutdown timeout (seconds)
        """
        super().__init__(
            model_name=model_name,
            queue_timeout=queue_timeout,
            stop_timeout=stop_timeout,
        )

        # Will be initialized in worker process
        self.tokenizer = None
        self.model = None

    def load_model(self) -> None:
        """
        Load ONNX model and tokenizer in worker process.

        Prefers INT8 quantized model for better performance.
        Falls back to FP32 ONNX if INT8 not available.

        Raises:
            FileNotFoundError: If model files missing
            Exception: If model fails to load
        """
        from optimum.onnxruntime import ORTModelForTokenClassification
        from transformers import AutoTokenizer

        # Build model path
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        model_base = os.path.join(
            base_dir, settings.MODEL_STORAGE_PATH, "visobert-hsd-span"
        )

        int8_path = os.path.join(model_base, "onnx-int8")
        onnx_path = os.path.join(model_base, "onnx")

        # Prefer INT8 quantized model
        if os.path.exists(int8_path) and os.listdir(int8_path):
            model_path = int8_path
            file_name = "model_quantized.onnx"
            self.logger.info(f"Loading INT8 quantized span detector from {model_path}")
        elif os.path.exists(onnx_path) and os.listdir(onnx_path):
            model_path = onnx_path
            file_name = "model.onnx"
            self.logger.info(f"Loading FP32 ONNX span detector from {model_path}")
        else:
            raise FileNotFoundError(
                "ViSoBERT-HSD-Span model not found. "
                "Please run 'python scripts/setup_hsd_span_model.py'"
            )

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

        # Load ONNX model
        self.model = ORTModelForTokenClassification.from_pretrained(
            model_path, file_name=file_name, provider="CPUExecutionProvider"
        )

        self.logger.info(
            f"ViSoBERT-HSD-Span model loaded successfully from {model_path}"
        )

    def process(self, item: Dict[str, Any]) -> None:
        """
        Process text and produce moderation result.

        Runs hate speech detection model and outputs structured result
        with label, confidence, and detected offensive spans.

        Args:
            item: Dictionary with keys:
                - text: Text to moderate (required)
                - request_id: Optional tracking ID
        """
        if not item or not isinstance(item, dict):
            return

        text = item.get("text", "")
        request_id = item.get("request_id")

        # Skip empty or very short texts
        if not text or len(text.strip()) < self.MIN_TEXT_LENGTH:
            # Return CLEAN for empty text
            result = {
                "request_id": request_id,
                "label": "CLEAN",
                "confidence": 1.0,
                "is_flagged": False,
                "detected_keywords": [],
                "spans": [],
                "latency_ms": 0.0,
            }
            try:
                self.output_queue.put(result, timeout=self.queue_timeout)
            except Exception:
                pass
            return

        start_time = time.perf_counter()

        try:
            result = self._detect_spans(text, request_id)
            result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

            try:
                self.output_queue.put(result, timeout=self.queue_timeout)
            except Exception:
                self.logger.warning("Output queue full, dropping result")

        except Exception as e:
            self.logger.error(f"Span detection error: {e}", exc_info=True)
            # Send error result
            error_result = {
                "request_id": request_id,
                "label": "CLEAN",  # Default to CLEAN on error
                "confidence": 0.0,
                "is_flagged": False,
                "detected_keywords": [],
                "spans": [],
                "error": str(e),
            }
            try:
                self.output_queue.put(error_result, timeout=self.queue_timeout)
            except Exception:
                pass

    def _detect_spans(
        self, text: str, request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect hate speech spans using NLP model with fallback.

        Main detection logic combining:
        1. BERT-based BIO tagging
        2. Rule-based fallback detection
        3. Span merging and filtering

        Args:
            text: Text to analyze
            request_id: Optional tracking ID

        Returns:
            Dictionary with detection results:
                - label: CLEAN, OFFENSIVE, or HATE
                - confidence: float (0.0-1.0)
                - is_flagged: bool
                - detected_keywords: List[str]
                - spans: List[Dict] with start, end, text, label
                - request_id: Optional[str]
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.MAX_SEQUENCE_LENGTH,
            padding=True,
        )

        # Run model inference
        outputs = self.model(**inputs)
        predictions = outputs.logits.argmax(dim=-1).squeeze().tolist()

        # Handle single token case
        if isinstance(predictions, int):
            predictions = [predictions]

        # Extract spans from BIO tags
        model_spans = self._extract_spans(text, predictions, inputs)

        # Filter and validate model spans
        filtered_spans = self._filter_model_spans(model_spans, text)

        # Fallback rule-based detection
        fallback_spans = self._fallback_detect_spans(text)

        # Merge all spans
        all_spans = self._merge_spans(filtered_spans + fallback_spans, text)

        # Infer final label and confidence
        label, confidence, is_flagged, detected_keywords = self._infer_label(
            all_spans, text
        )

        return {
            "request_id": request_id,
            "label": label,
            "confidence": confidence,
            "is_flagged": is_flagged,
            "detected_keywords": detected_keywords,
            "spans": all_spans,
        }

    def _extract_spans(
        self, text: str, predictions: List[int], inputs: Any
    ) -> List[Dict[str, Any]]:
        """
        Extract offensive spans from BIO tag predictions.

        Converts token-level BIO tags to character-level spans.

        Args:
            text: Original text
            predictions: List of predicted label IDs
            inputs: Tokenizer output with offset_mapping

        Returns:
            List of span dicts with start, end, text, label, source
        """
        spans = []
        current_span = None

        # Get token offsets (character positions)
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

        for idx, (token, pred_id) in enumerate(zip(tokens, predictions)):
            # Skip special tokens
            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue

            label = self.LABEL_MAP.get(pred_id, "O")

            if label.startswith("B-"):
                # Begin new span
                if current_span:
                    spans.append(current_span)

                current_span = {
                    "label": label[2:],  # Remove "B-" prefix
                    "token_ids": [idx],
                    "tokens": [token],
                }

            elif label.startswith("I-") and current_span:
                # Continue span
                current_span["token_ids"].append(idx)
                current_span["tokens"].append(token)

            else:
                # Outside or new span type
                if current_span:
                    spans.append(current_span)
                    current_span = None

        # Add last span
        if current_span:
            spans.append(current_span)

        # Convert token positions to character positions
        result_spans = []
        for span in spans:
            # Reconstruct span text from tokens
            span_text = self.tokenizer.convert_tokens_to_string(span["tokens"])
            span_text = span_text.strip()

            if not span_text:
                continue

            # Find character position in original text
            start = text.lower().find(span_text.lower())
            if start == -1:
                continue

            end = start + len(span_text)

            result_spans.append(
                {
                    "start": start,
                    "end": end,
                    "text": text[start:end],
                    "label": span["label"],
                    "source": "model",
                }
            )

        return result_spans

    def _filter_model_spans(
        self, spans: List[Dict[str, Any]], text: str
    ) -> List[Dict[str, Any]]:
        """
        Filter and validate model-detected spans.

        Removes false positives and very short spans.

        Args:
            spans: List of span dicts from model
            text: Original text

        Returns:
            Filtered list of spans
        """
        filtered = []

        for span in spans:
            span_text = span["text"].strip()

            # Skip very short spans (likely false positives)
            if len(span_text) < 2:
                continue

            # Skip single-character or numeric-only spans
            if len(span_text) == 1 or span_text.isdigit():
                continue

            filtered.append(span)

        return filtered

    def _fallback_detect_spans(self, text: str) -> List[Dict[str, Any]]:
        """
        Rule-based fallback detection using offensive phrase list.

        Searches for known offensive phrases in text and creates spans.

        Args:
            text: Text to search

        Returns:
            List of span dicts with start, end, text, label, source
        """
        spans = []
        text_lower = text.lower()

        for phrase in self.FALLBACK_BAD_PHRASES:
            start = 0
            while True:
                start = text_lower.find(phrase, start)
                if start == -1:
                    break

                end = start + len(phrase)

                # Determine severity
                if phrase in self.SEVERE_HATE_INDICATORS:
                    label = "HATE"
                else:
                    label = "OFFENSIVE"

                spans.append(
                    {
                        "start": start,
                        "end": end,
                        "text": text[start:end],
                        "label": label,
                        "source": "fallback",
                    }
                )

                start = end

        return spans

    def _merge_spans(
        self, spans: List[Dict[str, Any]], text: str
    ) -> List[Dict[str, Any]]:
        """
        Merge overlapping and adjacent spans.

        Combines spans that overlap or are very close together,
        taking the most severe label.

        Args:
            spans: List of all detected spans
            text: Original text

        Returns:
            Merged list of spans
        """
        if not spans:
            return []

        # Sort by start position
        sorted_spans = sorted(spans, key=lambda s: s["start"])

        merged = []
        current = sorted_spans[0].copy()

        for span in sorted_spans[1:]:
            # Check if overlapping or adjacent (within 3 chars)
            if span["start"] <= current["end"] + 3:
                # Merge spans
                current["end"] = max(current["end"], span["end"])
                current["text"] = text[current["start"] : current["end"]]

                # Take most severe label
                if span["label"] == "HATE" or current["label"] == "HATE":
                    current["label"] = "HATE"
                elif span["label"] == "OFFENSIVE" or current["label"] == "OFFENSIVE":
                    current["label"] = "OFFENSIVE"

                # Prefer model source over fallback
                if span["source"] == "model":
                    current["source"] = "model"
            else:
                # No overlap, save current and start new
                merged.append(current)
                current = span.copy()

        # Add last span
        merged.append(current)

        return merged

    def _infer_label(
        self, spans: List[Dict[str, Any]], text: str
    ) -> Tuple[str, float, bool, List[str]]:
        """
        Infer final moderation label from detected spans.

        Combines span information to produce overall classification
        with confidence score.

        Args:
            spans: List of detected offensive spans
            text: Original text

        Returns:
            Tuple of (label, confidence, is_flagged, keywords):
                - label: "CLEAN", "OFFENSIVE", or "HATE"
                - confidence: float (0.0-1.0)
                - is_flagged: bool
                - keywords: List of detected offensive words
        """
        if not spans:
            return ("CLEAN", 1.0, False, [])

        # Extract keywords
        keywords = list(set(span["text"].strip() for span in spans))

        # Count span types
        hate_count = sum(1 for s in spans if s["label"] == "HATE")
        offensive_count = sum(1 for s in spans if s["label"] == "OFFENSIVE")

        # Determine label
        if hate_count > 0:
            label = "HATE"
            # Higher confidence with more severe indicators
            confidence = min(0.95, 0.7 + (hate_count * 0.1))
        elif offensive_count > 0:
            label = "OFFENSIVE"
            # Moderate confidence for offensive content
            confidence = min(0.9, 0.6 + (offensive_count * 0.1))
        else:
            label = "CLEAN"
            confidence = 1.0

        is_flagged = label in ["HATE", "OFFENSIVE"]

        return (label, confidence, is_flagged, keywords)

    async def moderate(self, text: str) -> ModerationResult:
        """
        Analyze text for hate speech and offensive content.

        Implements IModerationWorker.moderate().
        Sends text to worker process and returns structured result.

        Args:
            text: Text content to moderate

        Returns:
            ModerationResult entity with label, confidence, and spans

        Raises:
            RuntimeError: If worker not ready
            ValueError: If text empty or too long
            TimeoutError: If processing times out

        Example:
            ```python
            worker = SpanDetectorWorker()
            await worker.start()

            result = await worker.moderate("Xin chào các bạn")
            print(f"Label: {result.label}, Confidence: {result.confidence}")

            await worker.stop()
            ```
        """
        if not await self.is_ready():
            raise RuntimeError("Span detector worker not ready")

        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if len(text) > 10000:
            raise ValueError("Text too long (max 10000 chars)")

        # Send to worker
        item = {"text": text, "request_id": None}
        await self.put_input(item, timeout=5.0)

        # Get result
        try:
            result = await self.get_output(timeout=10.0)

            # Convert to ModerationResult entity
            if result["label"] == "CLEAN":
                moderation_result = ModerationResult.create_clean()
            elif result["label"] == "OFFENSIVE":
                moderation_result = ModerationResult.create_offensive(
                    confidence=result["confidence"],
                    detected_keywords=result["detected_keywords"],
                    spans=result.get("spans", []),
                )
            else:  # HATE
                moderation_result = ModerationResult.create_hate_speech(
                    confidence=result["confidence"],
                    detected_keywords=result["detected_keywords"],
                    spans=result.get("spans", []),
                )

            return moderation_result

        except TimeoutError:
            self.logger.error("Moderation timeout")
            raise TimeoutError("Moderation processing timeout after 10s")
        except Exception as e:
            self.logger.error(f"Moderation error: {e}", exc_info=True)
            raise RuntimeError(f"Moderation failed: {e}")
