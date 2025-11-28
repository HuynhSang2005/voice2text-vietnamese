import os
import numpy as np

from app.workers.base import BaseWorker
from app.core.config import settings


class WhisperWorker(BaseWorker):
    """Worker for Whisper models using faster-whisper (CTranslate2)."""
    
    # VAD Configuration
    SILENCE_THRESHOLD = 0.0005
    MIN_DURATION = 3.0  # seconds
    MAX_DURATION = 15.0  # seconds
    
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
        self.logger.info(f"Whisper model ({self.model_name}) loaded successfully")

    def process(self, item):
        if not self.model:
            return

        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                self.logger.debug("Resetting buffer for new session")
                self.buffer = np.array([], dtype=np.float32)
                if not audio_data:
                    return
        else:
            audio_data = item

        if audio_data:
            # Convert bytes (int16) to float32 normalized
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0
            
            # Append to buffer
            self.buffer = np.concatenate((self.buffer, samples))
            
            # Energy-based VAD
            duration = len(self.buffer) / 16000.0
            should_transcribe = False
            
            if duration > self.MIN_DURATION:
                # Check last 0.5s for silence
                last_05s = self.buffer[-8000:]
                last_energy = np.mean(last_05s ** 2)
                
                if last_energy < self.SILENCE_THRESHOLD:
                    should_transcribe = True
            
            if duration > self.MAX_DURATION:
                should_transcribe = True
                
            if should_transcribe:
                segments, info = self.model.transcribe(
                    self.buffer, 
                    language="vi", 
                    beam_size=5,
                    vad_filter=False
                )
                
                text = " ".join([s.text for s in segments]).strip()
                
                if text:
                    self.output_queue.put({
                        "text": text,
                        "is_final": True,
                        "model": self.model_name
                    })
                
                # Reset buffer
                self.buffer = np.array([], dtype=np.float32)
