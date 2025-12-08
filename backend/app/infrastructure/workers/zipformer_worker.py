"""
Infrastructure Layer - Zipformer Transcription Worker

Async wrapper for Sherpa-ONNX Zipformer Vietnamese STT model.
Implements ITranscriptionWorker protocol using multiprocessing.
"""


import logging
import numpy as np
import os
import time
from typing import AsyncIterator, Optional

from app.core.config import settings
from app.domain.entities.transcription import Transcription
from app.domain.value_objects.audio_data import AudioData
from app.infrastructure.workers.base_worker import BaseWorker


logger = logging.getLogger(__name__)


class ZipformerWorker(BaseWorker):
    """
    Zipformer (RNN-T) Vietnamese STT worker.

    Uses Sherpa-ONNX INT8 quantized model for efficient inference.
    Implements streaming transcription with deduplication to avoid
    flooding clients with duplicate results.

    Model: hynt-zipformer-30M-6000h (trained on 6000 hours Vietnamese)
    """

    def __init__(
        self,
        model_name: str = "zipformer",
        queue_timeout: float = 1.0,
        stop_timeout: float = 5.0,
    ):
        """
        Initialize Zipformer worker.

        Args:
            model_name: Name for logging (default: "zipformer")
            queue_timeout: Queue operation timeout (seconds)
            stop_timeout: Shutdown timeout (seconds)
        """
        super().__init__(
            model_name=model_name,
            queue_timeout=queue_timeout,
            stop_timeout=stop_timeout,
        )

        # Will be initialized in worker process
        self.recognizer = None
        self.stream = None
        self.last_text = ""

    def load_model(self) -> None:
        """
        Load Sherpa-ONNX Zipformer model in worker process.

        Loads INT8 quantized model for efficient CPU inference.
        Model files must exist in models_storage/ directory.

        Raises:
            FileNotFoundError: If model files missing
            Exception: If model fails to load
        """
        import sherpa_onnx

        # Build model path
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        model_dir = os.path.join(
            base_dir,
            settings.MODEL_STORAGE_PATH,
            "zipformer",
            "hynt-zipformer-30M-6000h",
        )

        tokens = os.path.join(model_dir, "tokens.txt")
        encoder = os.path.join(model_dir, "encoder-epoch-20-avg-10.int8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-20-avg-10.int8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-20-avg-10.int8.onnx")

        if not os.path.exists(encoder):
            raise FileNotFoundError(f"Model files not found in {model_dir}")

        self.logger.info(f"Loading Zipformer model from {model_dir}")

        try:
            # Create recognizer with INT8 models
            recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                tokens=tokens,
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                provider="cpu",
            )

            self.recognizer = recognizer
            self.stream = recognizer.create_stream()
            self.last_text = ""  # Deduplication tracker

            self.logger.info("Zipformer model loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load Zipformer model: {e}", exc_info=True)
            self.recognizer = None
            raise

    def format_vietnamese_text(self, text: str) -> str:
        """
        Format Vietnamese text to Sentence case.

        Args:
            text: Raw transcription text

        Returns:
            Formatted text (lowercase with capitalized first letter)
        """
        if not text:
            return ""

        text = text.lower()
        if text:
            text = text[0].upper() + text[1:]

        return text

    def process(self, item: dict) -> None:
        """
        Process audio data and produce transcription results.

        Handles streaming audio with deduplication. Only sends results
        when text changes to avoid flooding client with duplicates.

        Args:
            item: Dictionary with keys:
                - audio: Raw PCM audio bytes (int16)
                - reset: Optional bool to reset stream
                - flush: Optional bool to output final result
        """
        if not self.recognizer:
            return

        force_output = False
        audio_data = item.get("audio")

        # Handle stream reset (new session)
        if item.get("reset"):
            self.logger.debug("Resetting stream for new session")
            self.stream = self.recognizer.create_stream()
            self.last_text = ""
            if not audio_data:
                return

        # Handle flush (end of session)
        if item.get("flush"):
            self.logger.info("Flush signal received - outputting final result")
            force_output = True

        # Process audio if present
        if audio_data:
            start_time = time.perf_counter()

            # Convert bytes (int16) to float32 normalized [-1.0, 1.0]
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0

            # Feed audio to model
            self.stream.accept_waveform(16000, samples)
            self.recognizer.decode_stream(self.stream)

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Get transcription
            raw_text = self.stream.result.text
            formatted_text = self.format_vietnamese_text(raw_text)

            # Deduplication: only send if text changed
            if formatted_text and formatted_text != self.last_text:
                self.last_text = formatted_text

                result = {
                    "text": formatted_text,
                    "is_final": False,
                    "model": "zipformer",
                    "workflow_type": "streaming",
                    "latency_ms": round(latency_ms, 2),
                }

                try:
                    self.output_queue.put(result, timeout=self.queue_timeout)
                except Exception:
                    self.logger.warning("Output queue full, dropping result")

        # Handle flush: output final result and reset
        if force_output:
            raw_text = self.stream.result.text
            formatted_text = self.format_vietnamese_text(raw_text)

            if formatted_text:
                result = {
                    "text": formatted_text,
                    "is_final": True,
                    "model": "zipformer",
                    "workflow_type": "streaming",
                    "latency_ms": 0,
                }

                try:
                    self.output_queue.put(result, timeout=self.queue_timeout)
                    self.logger.info(f"Flush output: '{formatted_text[:50]}...'")
                except Exception:
                    self.logger.warning("Output queue full, dropping flush result")

            # Reset for next session
            self.stream = self.recognizer.create_stream()
            self.last_text = ""
            self.logger.debug("Stream reset after flush")

    async def process_audio_stream(
        self, audio_stream: AsyncIterator[AudioData]
    ) -> AsyncIterator[Transcription]:
        """
        Process streaming audio and yield transcription results.

        Implements ITranscriptionWorker.process_audio_stream().
        Converts AudioData to dict format for worker process, then
        converts results back to Transcription entities.

        Args:
            audio_stream: Async iterator of AudioData chunks

        Yields:
            Transcription: Transcription entities with text and metadata

        Raises:
            RuntimeError: If worker not ready
            TimeoutError: If processing times out

        Example:
            ```python
            worker = ZipformerWorker()
            await worker.start()

            async for audio in audio_stream:
                async for result in worker.process_audio_stream([audio]):
                    print(f"Transcribed: {result.content}")

            await worker.stop()
            ```
        """
        if not await self.is_ready():
            raise RuntimeError("Zipformer worker not ready")

        # Process each audio chunk
        async for audio in audio_stream:
            # Validate audio format
            if audio.format != "pcm":
                raise ValueError(f"Unsupported audio format: {audio.format}")

            if audio.sample_rate != 16000:
                raise ValueError(
                    f"Invalid sample rate: {audio.sample_rate} (expected 16000)"
                )

            if not audio.is_mono():
                raise ValueError("Audio must be mono (1 channel)")

            # Send to worker process
            item = {"audio": audio.data, "reset": False, "flush": False}

            await self.put_input(item, timeout=5.0)

            # Try to get result (non-blocking with short timeout)
            try:
                result = await self.get_output(timeout=0.5)

                # Convert to Transcription entity
                transcription = Transcription.create_new(
                    session_id="temp",  # Will be set by use case
                    model_id=result.get("model", "zipformer"),
                    content=result["text"],
                    latency_ms=result.get("latency_ms", 0.0),
                )

                yield transcription

            except TimeoutError:
                # No result yet (deduplication or still processing)
                continue
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}", exc_info=True)
                continue

    async def reset_stream(self) -> None:
        """
        Reset transcription stream for new session.

        Clears accumulated context from previous transcription.
        Call this when starting a new transcription session.
        """
        item = {"audio": None, "reset": True, "flush": False}
        await self.put_input(item, timeout=2.0)
        self.logger.debug("Sent reset signal to worker")

    async def flush_and_reset(self) -> Optional[Transcription]:
        """
        Flush final result and reset stream.

        Forces output of accumulated transcription and resets
        the stream for the next session.

        Returns:
            Final Transcription if any text accumulated, None otherwise
        """
        # Send flush signal
        item = {"audio": None, "reset": False, "flush": True}
        await self.put_input(item, timeout=2.0)

        # Get final result
        try:
            result = await self.get_output(timeout=2.0)

            transcription = Transcription.create_new(
                session_id="temp",
                model_id=result.get("model", "zipformer"),
                content=result["text"],
                latency_ms=result.get("latency_ms", 0.0),
            )

            return transcription

        except TimeoutError:
            self.logger.debug("No final result to flush")
            return None
        except Exception as e:
            self.logger.error(f"Error flushing result: {e}", exc_info=True)
            return None
