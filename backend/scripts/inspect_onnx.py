import onnxruntime as ort
import os

def inspect_onnx(model_path):
    print(f"Inspecting {model_path}...")
    try:
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        print("Inputs:")
        for input in session.get_inputs():
            print(f"  - {input.name}: {input.shape} ({input.type})")
        print("Outputs:")
        for output in session.get_outputs():
            print(f"  - {output.name}: {output.shape} ({output.type})")
            
        # Check metadata if possible (onnxruntime doesn't make it easy to read custom metadata directly via session, 
        # but we can check inputs to infer streaming capability)
        
        # Streaming Zipformer usually has inputs like 'cached_len', 'cached_avg', 'cached_key', 'cached_val' etc.
        # Offline usually just 'x' (features) and 'x_lens'.
        
    except Exception as e:
        print(f"Error inspecting ONNX: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to root
    root_dir = os.path.abspath(os.path.join(base_dir, "../"))
    model_dir = os.path.join(root_dir, "models_storage", "zipformer", "hynt-zipformer-30M-6000h")
    encoder_path = os.path.join(model_dir, "encoder-epoch-20-avg-10.int8.onnx")
    
    if os.path.exists(encoder_path):
        inspect_onnx(encoder_path)
    else:
        print(f"Model file not found: {encoder_path}")
