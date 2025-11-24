import os
import numpy as np
from app.workers.base import BaseWorker

class WhisperWorker(BaseWorker):
    def load_model(self):
        from faster_whisper import WhisperModel
        
        # model_path passed in __init__ is the model name from manager
        # e.g., "faster-whisper" or "phowhisper"
        
        model_name = self.model_path # This is actually the key used in manager
        
        compute_type = "int8"
        device = "cpu" # Or cuda if available
        
        if model_name == "phowhisper":
            # Load from local converted path
            model_dir = os.path.join("models_storage", "phowhisper-ct2")
            if not os.path.exists(model_dir):
                print(f"Warning: PhoWhisper model not found at {model_dir}")
                self.model = None
                return
            self.model = WhisperModel(model_dir, device=device, compute_type=compute_type)
        else:
            # Default faster-whisper (small or medium)
            # Auto download
            self.model = WhisperModel("small", device=device, compute_type=compute_type)
            
        self.buffer = np.array([], dtype=np.float32)
        print(f"Whisper model ({model_name}) loaded.")

    def process(self, item):
        if not self.model:
            return

        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                self.buffer = np.array([], dtype=np.float32)
        else:
            audio_data = item

        if audio_data:
            # Convert bytes (int16) to float32 normalized
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0
            
            # Append to buffer
            self.buffer = np.concatenate((self.buffer, samples))
            
            # VAD and Transcription Logic
            # Simple strategy: Transcribe every X seconds or when buffer is long enough
            # For real-time with Whisper, we usually need a VAD to detect silence and cut.
            # faster-whisper has built-in VAD in transcribe(), but that's for a file/complete buffer.
            # Here we are accumulating.
            
            # Strategy:
            # If buffer > 3 seconds, try to transcribe.
            # If we get a result, we might want to keep the buffer or clear it?
            # This is complex for streaming.
            # Simplified approach for "Research Dashboard":
            # Accumulate until silence (detected by VAD? or just simple energy?)
            # Or just transcribe the whole buffer every time (inefficient but simple for demo).
            
            # Let's use a simple threshold: Transcribe if buffer > 1s.
            # And we send "is_final=False".
            # If we detect silence (e.g. using Silero VAD separately, but we don't have it imported yet),
            # we could finalize.
            
            # For now, let's just transcribe the growing buffer and send updates.
            # To prevent infinite growth, we need a reset mechanism from client or silence detection.
            # Let's rely on client sending "reset" or just keep growing for short phrases.
            
            if len(self.buffer) > 16000 * 1.0: # > 1 second
                segments, info = self.model.transcribe(
                    self.buffer, 
                    language="vi", 
                    beam_size=1, 
                    vad_filter=True
                )
                
                text = " ".join([s.text for s in segments]).strip()
                
                self.output_queue.put({
                    "text": text,
                    "is_final": False, # Whisper is block-based, so it's always "interim" until we decide to cut.
                    "model": self.model_path
                })
