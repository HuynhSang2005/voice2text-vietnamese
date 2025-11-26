import sherpa_onnx
import os
import sys

def test_online_loading():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    model_dir = os.path.join(base_dir, "models_storage", "zipformer", "sherpa-onnx-zipformer-vi-int8-2025-04-20")
    
    tokens = os.path.join(model_dir, "tokens.txt")
    encoder = os.path.join(model_dir, "encoder-epoch-12-avg-8.int8.onnx")
    decoder = os.path.join(model_dir, "decoder-epoch-12-avg-8.onnx")
    joiner = os.path.join(model_dir, "joiner-epoch-12-avg-8.int8.onnx")
    
    print(f"Testing OnlineRecognizer with model: {model_dir}")
    
    try:
        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
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
        print("SUCCESS: OnlineRecognizer loaded!")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_online_loading()
