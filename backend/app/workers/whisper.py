import os
import time
import numpy as np

from app.workers.base import BaseWorker
from app.core.config import settings


class WhisperWorker(BaseWorker):
    """Worker for Whisper models using faster-whisper (CTranslate2).
    
    Whisper is a buffered model - it needs sufficient audio context to produce
    accurate transcriptions. This worker accumulates audio chunks and processes
    them in batches based on silence detection or max duration.
    
    Key differences from streaming models (Zipformer, HKAB):
    - Emits is_final=true only (no interim text)
    - Higher latency (2-8s) but potentially more accurate
    - VAD is used to detect sentence boundaries, not filter noise
    """
    
    # VAD Configuration - balanced for accuracy and latency
    SILENCE_THRESHOLD = 0.0003  # Energy threshold for custom silence detection
    MIN_DURATION = 3.0  # Minimum buffer before transcribing (need enough context)
    MAX_DURATION = 15.0  # Force transcribe if buffer too long
    SILENCE_DURATION = 0.5  # Seconds of silence to trigger transcription
    
    def load_model(self):
        from faster_whisper import WhisperModel
        
        compute_type = "int8"
        device = "cpu"
        
        if self.model_name == "phowhisper":
            # Load from local converted path
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            model_dir = os.path.join(base_dir, settings.MODEL_STORAGE_PATH, "phowhisper-ct2")
            
            if os.path.exists(model_dir):
                self.logger.info(f"Loading PhoWhisper from {model_dir}")
                self.model = WhisperModel(model_dir, device=device, compute_type=compute_type)
            else:
                self.logger.warning(f"PhoWhisper not found at {model_dir}, falling back to 'small'")
                self.model = WhisperModel("small", device=device, compute_type=compute_type)
        else:
            # Default faster-whisper (small)
            self.logger.info("Loading faster-whisper 'small' model")
            self.model = WhisperModel("small", device=device, compute_type=compute_type)
            
        self.buffer = np.array([], dtype=np.float32)
        self.silence_samples = 0  # Track consecutive silence samples
        self.logger.info(f"Whisper model ({self.model_name}) loaded successfully")

    def process(self, item):
        if not self.model:
            return

        audio_data = None
        force_transcribe = False
        
        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                self.logger.debug("Resetting buffer for new session")
                self.buffer = np.array([], dtype=np.float32)
                self.silence_samples = 0
                if not audio_data:
                    return
            if item.get("flush"):
                # Force transcribe remaining buffer
                self.logger.info("Flush signal received - forcing transcription")
                force_transcribe = True
        else:
            audio_data = item

        if audio_data:
            # Convert bytes (int16) to float32 normalized
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0
            
            # Append to buffer
            self.buffer = np.concatenate((self.buffer, samples))
            
            # Check if this chunk is silence
            chunk_energy = np.mean(samples ** 2)
            if chunk_energy < self.SILENCE_THRESHOLD:
                self.silence_samples += len(samples)
            else:
                self.silence_samples = 0
            
        # Calculate buffer duration
        duration = len(self.buffer) / 16000.0
        silence_duration = self.silence_samples / 16000.0
        
        # Decide if we should transcribe
        should_transcribe = force_transcribe
        
        # Transcribe if we have enough audio AND detected silence
        if not should_transcribe and duration >= self.MIN_DURATION:
            if silence_duration >= self.SILENCE_DURATION:
                should_transcribe = True
                self.logger.debug(f"Silence detected ({silence_duration:.2f}s), triggering transcription")
        
        # Force transcribe if buffer too long
        if not should_transcribe and duration >= self.MAX_DURATION:
            should_transcribe = True
            self.logger.debug(f"Max duration reached ({duration:.2f}s), forcing transcription")
            
        # Transcribe if we have enough audio (at least 0.3s for flush)
        min_required = 0.3 if force_transcribe else self.MIN_DURATION
        
        if should_transcribe and duration >= min_required:
            start_time = time.perf_counter()
            
            self.logger.info(f"Transcribing buffer of {duration:.2f}s (force={force_transcribe})")
            
            # VAD parameters tuned for Vietnamese speech:
            # - Lower threshold (0.3) to not discard too much audio
            # - Longer min_speech (500ms) to filter out clicks/noise
            # - speech_pad (400ms) to keep context around speech
            segments, info = self.model.transcribe(
                self.buffer, 
                language="vi", 
                beam_size=3,  # Reduced from 5 for faster CPU inference
                vad_filter=True,  # Enable VAD to remove silence
                vad_parameters={
                    "threshold": 0.3,  # Lower = keep more audio (was 0.5)
                    "min_speech_duration_ms": 500,  # Min 500ms speech (was 250)
                    "min_silence_duration_ms": 800,  # 800ms silence to split (was 500)
                    "speech_pad_ms": 400,  # Pad speech segments with 400ms context
                },
                no_speech_threshold=0.6,  # Filter out segments with high no_speech probability
                condition_on_previous_text=False,  # Prevent hallucination from context leak
            )
            
            # Filter segments with low no_speech_prob (actual speech)
            filtered_segments = []
            for s in segments:
                # Only keep segments with low no_speech probability (likely real speech)
                if s.no_speech_prob < 0.5:
                    filtered_segments.append(s)
                else:
                    self.logger.debug(f"Filtered out segment with high no_speech_prob: {s.no_speech_prob:.2f} - '{s.text[:30]}'")
            
            text = " ".join([s.text for s in filtered_segments]).strip()
            
            # Calculate processing latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            if text:
                self.logger.info(f"Transcription result: '{text[:50]}{'...' if len(text) > 50 else ''}' (latency: {latency_ms:.0f}ms)")
                self.output_queue.put({
                    "text": text,
                    "is_final": True,
                    "model": self.model_name,
                    "workflow_type": "buffered",  # Buffered = each result is a separate chunk, needs append
                    "latency_ms": round(latency_ms, 2)
                })
            else:
                self.logger.debug("Transcription returned empty text")
            
            # Reset buffer and silence counter
            self.buffer = np.array([], dtype=np.float32)
            self.silence_samples = 0
