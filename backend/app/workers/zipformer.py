import os
import numpy as np

from app.workers.base import BaseWorker

class ZipformerWorker(BaseWorker):
    def load_model(self):
        import sherpa_onnx
        
        # Define paths relative to backend execution (which is usually project root or backend dir)
        # If running from backend dir, we need to go up one level
        # Better to use absolute path based on project root
        
        # models_storage is at d:\voice2text-vietnamese\backend\models_storage
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        model_dir = os.path.join(base_dir, "models_storage", "zipformer", "hynt-zipformer-30M-6000h")
        
        tokens = os.path.join(model_dir, "tokens.txt")
        encoder = os.path.join(model_dir, "encoder-epoch-20-avg-10.int8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-20-avg-10.int8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-20-avg-10.int8.onnx")

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
            # Use OfflineRecognizer as the model is offline-only
            print("[ZipformerWorker] Creating recognizer using OfflineRecognizer.from_transducer...")
            recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                tokens=tokens,
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                num_threads=1,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                provider="cpu",
            )
            
            print("[ZipformerWorker] OfflineRecognizer created successfully")
            self.recognizer = recognizer
            # OfflineRecognizer also has create_stream
            self.stream = recognizer.create_stream()
            print("[ZipformerWorker] Stream created successfully")
            print("Zipformer model loaded successfully.")
            
        except Exception as e:
            print(f"Fatal: Failed to load Zipformer model: {e}")
            import traceback
            traceback.print_exc()
            self.recognizer = None
            raise

    def format_vietnamese_text(self, text: str) -> str:
        """
        Convert text to Sentence case (first letter capitalized, rest lowercase).
        Example: "XIN CHÀO" -> "Xin chào"
        """
        if not text:
            return ""
        
        # Lowercase everything first
        text = text.lower()
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
            
        return text

    def process(self, item):
        if not self.recognizer:
            return

        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                print("[ZipformerWorker] Resetting stream for new session")
                self.stream = self.recognizer.create_stream()
                # If reset is the only instruction, return early
                if not audio_data:
                    return
        else:
            audio_data = item

        if audio_data:
            # Convert bytes (int16) to float32 normalized
            samples = np.frombuffer(audio_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0
            
            # print(f"[ZipformerWorker] Processing {len(samples)} samples ({len(audio_data)} bytes)")
            
            self.stream.accept_waveform(16000, samples)
            
            self.recognizer.decode_stream(self.stream)
            
            raw_text = self.stream.result.text
            formatted_text = self.format_vietnamese_text(raw_text)
            
            # For Offline, is_endpoint is not available or not used same way.
            # We'll just send the current text as "interim" (is_final=False)
            
            is_final = False 
            
            result = {
                "text": formatted_text,
                "is_final": is_final,
                "model": "zipformer"
            }
            
            # print(f"[ZipformerWorker] Putting result in queue: text='{formatted_text}'")
            
            self.output_queue.put(result)
