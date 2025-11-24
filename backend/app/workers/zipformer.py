import os
import numpy as np

from app.workers.base import BaseWorker

class ZipformerWorker(BaseWorker):
    def load_model(self):
        import sherpa_onnx
        
        # Define paths relative to models_storage/zipformer
        model_dir = os.path.join("models_storage", "zipformer")
        tokens = os.path.join(model_dir, "tokens.txt")
        encoder = os.path.join(model_dir, "encoder-epoch-12-avg-8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-12-avg-8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-12-avg-8.onnx")

        # Check if files exist
        if not os.path.exists(encoder):
            print(f"Error: Zipformer encoder not found at {encoder}")
            self.recognizer = None
            raise FileNotFoundError(f"Model files not found in {model_dir}")

        print(f"Loading model from {model_dir}...")
        print(f"  - encoder: {encoder}")
        print(f"  - decoder: {decoder}")
        print(f"  - joiner: {joiner}")
        print(f"  - tokens: {tokens}")

        try:
            # Use the official API from sherpa-onnx examples
            print("[ZipformerWorker] Creating recognizer using OnlineRecognizer.from_transducer...")
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
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
            
            print("[ZipformerWorker] OnlineRecognizer created successfully")
            self.recognizer = recognizer
            self.stream = recognizer.create_stream()
            print("[ZipformerWorker] Stream created successfully")
            print("Zipformer model loaded successfully.")
            
        except Exception as e:
            print(f"Fatal: Failed to load Zipformer model: {e}")
            import traceback
            traceback.print_exc()
            self.recognizer = None
            raise

    def process(self, item):
        if not self.recognizer:
            return

        # Item is expected to be a dict: {"audio": bytes, "reset": bool}
        # or just bytes if we assume continuous stream.
        # Let's support a simple protocol: dict with 'audio' (bytes) and optional 'reset'
        
        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                self.stream = self.recognizer.create_stream()
        else:
            audio_data = item

        if audio_data:
            # Convert bytes (int16) to float32 normalized
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0
            
            print(f"[ZipformerWorker] Processing {len(samples)} samples ({len(audio_data)} bytes)")
            
            self.stream.accept_waveform(16000, samples)
            
            while self.recognizer.is_ready(self.stream):
                self.recognizer.decode_stream(self.stream)
            
            text = self.stream.result.text
            
            # Send result back
            # Zipformer is streaming, so we send partial results?
            # Sherpa-onnx result.text is the full text so far.
            # We might want to send only if changed?
            # For simplicity, send it. Frontend handles diff? 
            # Actually, frontend expects "is_final". 
            # Zipformer streaming output is usually "interim" until endpointing?
            # Sherpa-onnx endpointing is handled by `is_endpoint`.
            
            is_endpoint = self.recognizer.is_endpoint(self.stream)
            
            result = {
                "text": text,
                "is_final": is_endpoint,
                "model": "zipformer"
            }
            
            print(f"[ZipformerWorker] Putting result in queue: text='{text}', is_final={is_endpoint}")
            
            self.output_queue.put(result)
            
            if is_endpoint:
                self.recognizer.reset(self.stream)
