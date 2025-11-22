import os
import sherpa_onnx
import numpy as np
from app.workers.base import BaseWorker

class ZipformerWorker(BaseWorker):
    def load_model(self):
        # Define paths relative to models_storage/zipformer
        # Assuming the user has downloaded the model files to this directory
        model_dir = os.path.join("models_storage", "zipformer")
        tokens = os.path.join(model_dir, "tokens.txt")
        encoder = os.path.join(model_dir, "encoder-epoch-12-avg-8.onnx")
        decoder = os.path.join(model_dir, "decoder-epoch-12-avg-8.onnx")
        joiner = os.path.join(model_dir, "joiner-epoch-12-avg-8.onnx")

        # Check if files exist, if not, maybe use default or error out
        if not os.path.exists(encoder):
            print(f"Warning: Zipformer model not found at {model_dir}. Please download it.")
            # For now, we can't proceed without model files.
            # But to avoid crashing the worker loop immediately if files are missing during dev:
            self.recognizer = None
            return

        config = sherpa_onnx.OnlineRecognizerConfig(
            model_config=sherpa_onnx.OnlineModelConfig(
                transducer=sherpa_onnx.OnlineTransducerModelConfig(
                    encoder=encoder,
                    decoder=decoder,
                    joiner=joiner,
                ),
                tokens=tokens,
                num_threads=1,
            ),
            feature_config=sherpa_onnx.FeatureConfig(sample_rate=16000),
        )
        self.recognizer = sherpa_onnx.OnlineRecognizer(config)
        self.stream = self.recognizer.create_stream()
        print("Zipformer model loaded successfully.")

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
            
            self.output_queue.put({
                "text": text,
                "is_final": is_endpoint,
                "model": "zipformer"
            })
            
            if is_endpoint:
                self.recognizer.reset(self.stream)
