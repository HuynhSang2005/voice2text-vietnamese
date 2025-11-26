import sherpa_onnx
import os

def check_zipformer_streaming():
    model_dir = "models_storage/hynt-zipformer-30M-6000h"
    encoder_path = os.path.join(model_dir, "encoder-epoch-20-avg-10.onnx")
    decoder_path = os.path.join(model_dir, "decoder-epoch-20-avg-10.onnx")
    joiner_path = os.path.join(model_dir, "joiner-epoch-20-avg-10.onnx")
    tokens_path = os.path.join(model_dir, "tokens.txt")
    
    print("Checking Zipformer Streaming feasibility...")
    
    # Method 1: Try loading ONNX files as OnlineTransducer
    # Note: The files I have are likely Offline. But let's try.
    try:
        print("Attempting to load ONNX files as OnlineTransducer...")
        recognizer = sherpa_onnx.OnlineRecognizer(
            tokens=tokens_path,
            encoder=encoder_path,
            decoder=decoder_path,
            joiner=joiner_path,
            num_threads=1,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search"
        )
        print("SUCCESS: Loaded ONNX files as OnlineTransducer!")
        # If loaded, it might be streaming-compatible?
        # But if it's offline model, it might fail during stream creation or inference.
        s = recognizer.create_stream()
        print("Stream created.")
    except Exception as e:
        print(f"FAILED to load ONNX as Online: {e}")

    # Method 2: Check jit_script.pt (TorchScript)
    # sherpa-onnx supports loading TorchScript via `sherpa` (not sherpa-onnx) usually?
    # But `sherpa-onnx` is for ONNX.
    # However, the user said "dùng thư viện hỗ trợ như sherpa-onnx để chạy streaming với model Torch JIT Script".
    # Maybe `sherpa-onnx` supports loading .pt?
    # No, `sherpa-onnx` is strictly ONNX.
    # `k2-fsa/sherpa` (python package `k2` or `sherpa`) supports TorchScript.
    # I don't have `sherpa` installed, only `sherpa-onnx`.
    
    print("Note: To use jit_script.pt, we likely need 'sherpa' (not sherpa-onnx) or export it to Streaming ONNX.")
    
    # Conclusion
    if os.path.exists(os.path.join(model_dir, "jit_script.pt")):
        print("Found jit_script.pt. This is likely the TorchScript model.")
        print("It can be exported to Streaming ONNX using icefall/sherpa tools.")

if __name__ == "__main__":
    check_zipformer_streaming()
