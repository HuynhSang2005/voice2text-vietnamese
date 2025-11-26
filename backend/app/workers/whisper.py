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
            if os.path.exists(model_dir):
                print(f"[WhisperWorker] Loading PhoWhisper from {model_dir}")
                self.model = WhisperModel(model_dir, device=device, compute_type=compute_type)
            else:
                print(f"[WhisperWorker] Warning: PhoWhisper model not found at {model_dir}")
                print("[WhisperWorker] Falling back to 'small' model (standard Faster-Whisper).")
                self.model = WhisperModel("small", device=device, compute_type=compute_type)
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
            
            # VAD-based buffering strategy
            # We use a simple energy-based VAD or just time-based for now to keep it simple and fast on CPU
            # without adding heavy dependencies like torch.hub load inside the worker.
            # Ideally we should use Silero VAD, but let's start with a smart buffering:
            # 1. Accumulate at least 2 seconds.
            # 2. If > 2s, check if the last 0.5s is silent (low energy).
            # 3. If silent, transcribe and clear buffer.
            # 4. If buffer > 10s, force transcribe.
            
            # Energy calculation
            chunk_energy = np.mean(samples**2)
            # print(f"Energy: {chunk_energy}")
            
            # Threshold for silence (tunable)
            SILENCE_THRESHOLD = 0.001 
            MIN_DURATION = 2.0
            MAX_DURATION = 10.0
            
            duration = len(self.buffer) / 16000.0
            
            should_transcribe = False
            
            if duration > MIN_DURATION:
                # Check last 0.5s
                last_05s = self.buffer[-8000:]
                last_energy = np.mean(last_05s**2)
                
                if last_energy < SILENCE_THRESHOLD:
                    should_transcribe = True
                    # print("Silence detected, transcribing...")
            
            if duration > MAX_DURATION:
                should_transcribe = True
                # print("Max duration reached, transcribing...")
                
            if should_transcribe:
                # Transcribe
                segments, info = self.model.transcribe(
                    self.buffer, 
                    language="vi", 
                    beam_size=1, 
                    vad_filter=True # Use internal VAD to filter out non-speech within the chunk
                )
                
                text = " ".join([s.text for s in segments]).strip()
                
                if text:
                    self.output_queue.put({
                        "text": text,
                        "is_final": True, # We consider this a "final" segment
                        "model": self.model_path
                    })
                
                # Reset buffer
                self.buffer = np.array([], dtype=np.float32)
