import sherpa_onnx
import os

def test_load():
    model_dir = "models_storage/zipformer/sherpa-onnx-zipformer-vi-int8-2025-04-20"
    print(f"Listing files in {model_dir} (Recursive)...")
    for root, dirs, files in os.walk(model_dir):
        level = root.replace(model_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")

    tokens = os.path.join(model_dir, "tokens.txt")
    encoder = os.path.join(model_dir, "encoder-epoch-12-avg-8.int8.onnx")
    decoder = os.path.join(model_dir, "decoder-epoch-12-avg-8.onnx")
    joiner = os.path.join(model_dir, "joiner-epoch-12-avg-8.int8.onnx")
    
    print(f"Selected files:")
    print(f" Tokens: {tokens}")
    print(f" Encoder: {encoder}")
    print(f" Decoder: {decoder}")
    print(f" Joiner: {joiner}")

    # Check existence
    for f in [tokens, encoder, decoder, joiner]:
        if not os.path.exists(f):
            print(f"MISSING: {f}")
            return

    with open("load_result.txt", "w") as f:
        print("Loading recognizer (Offline)...")
        try:
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
            print("Success (Offline)!")
            f.write("Offline: Success\n")
        except Exception as e:
            print(f"Failed (Offline): {e}")
            f.write(f"Offline: Failed - {e}\n")
            
        # print("Loading recognizer (Online)...")
        # try:
        #     recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        #         tokens=tokens,
        #         encoder=encoder,
        #         decoder=decoder,
        #         joiner=joiner,
        #         num_threads=1,
        #         sample_rate=16000,
        #         feature_dim=80,
        #         decoding_method="greedy_search",
        #         provider="cpu",
        #     )
        #     print("Success (Online)!")
        #     f.write("Online: Success\n")
        # except Exception as e:
        #     print(f"Failed (Online): {e}")
        #     f.write(f"Online: Failed - {e}\n")

if __name__ == "__main__":
    test_load()
