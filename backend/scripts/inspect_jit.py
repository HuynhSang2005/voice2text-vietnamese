import torch
import os

def inspect_jit():
    path = "models_storage/zipformer/hynt-zipformer-30M-6000h/jit_script.pt"
    print(f"Inspecting {path}...")
    
    try:
        # Try loading as state_dict (checkpoint)
        checkpoint = torch.load(path, map_location="cpu")
        if isinstance(checkpoint, dict):
            print("SUCCESS: It is a dictionary (Checkpoint/State Dict)!")
            print("Keys:", checkpoint.keys())
            if "state_dict" in checkpoint:
                print("Found 'state_dict' key. This is a valid checkpoint.")
            return
        else:
            print(f"Loaded object is of type: {type(checkpoint)}")
            # It might be a JIT ScriptModule loaded via torch.load? No, JIT uses torch.jit.load
    except Exception as e:
        print(f"torch.load failed: {e}")
        
    try:
        # Try loading as JIT ScriptModule
        model = torch.jit.load(path, map_location="cpu")
        print("SUCCESS: It is a TorchScript (JIT) model!")
        
        # List methods
        print("Methods:")
        for method in dir(model):
            if not method.startswith("_"):
                print(f" - {method}")
                
        # Check for specific methods
        if hasattr(model, "encoder") and hasattr(model, "decoder") and hasattr(model, "joiner"):
             print("Found sub-modules: encoder, decoder, joiner")
             
        # Try extracting state_dict
        try:
            sd = model.state_dict()
            print(f"SUCCESS: Extracted state_dict! Keys: {len(sd)}")
            # Print first few keys
            print("Sample keys:", list(sd.keys())[:5])
        except Exception as e:
            print(f"Failed to extract state_dict: {e}")
        
    except Exception as e:
        print(f"torch.jit.load failed: {e}")

if __name__ == "__main__":
    inspect_jit()
