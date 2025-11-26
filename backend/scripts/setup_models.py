import os
import urllib.request
import shutil
import subprocess
import sys

"""
SETUP MODELS SCRIPT
-------------------
This script handles the downloading and preparation of AI models required for the backend.
It is designed to be idempotent (safe to run multiple times).

Usage:
    python backend/scripts/setup_models.py
"""

# Hynt Model details
HYNT_REPO_ID = "hynt/Zipformer-30M-RNNT-6000h"
HYNT_FILES = [
    "encoder-epoch-20-avg-10.int8.onnx",
    "decoder-epoch-20-avg-10.int8.onnx",
    "joiner-epoch-20-avg-10.int8.onnx",
    "bpe.model",
    "tokens.txt",
    "jit_script.pt",
    "config.json"
]
HYNT_BASE_URL = f"https://huggingface.co/{HYNT_REPO_ID}/resolve/main"

# HKAB Model details
HKAB_REPO_URL = "https://github.com/HKAB/vietnamese-rnnt-tutorial.git"

def download_file(url, dest_path):
    if os.path.exists(dest_path):
        print(f"File already exists: {dest_path}")
        return
    print(f"Downloading {url} to {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print("Download complete.")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        # Don't raise, just print error so other files can try
        pass

def generate_tokens(bpe_model_path, tokens_path):
    print(f"Generating tokens.txt from {bpe_model_path}...")
    try:
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.load(bpe_model_path)
        
        with open(tokens_path, "w", encoding="utf-8") as f:
            for i in range(sp.get_piece_size()):
                piece = sp.id_to_piece(i)
                f.write(f"{piece} {i}\n")
        print(f"Generated {tokens_path}")
    except ImportError:
        print("Error: sentencepiece not installed. Please run 'pip install sentencepiece'")
    except Exception as e:
        print(f"Error generating tokens: {e}")

def main():
    # Define paths
    # Script is in backend/scripts/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Models are in backend/models_storage (one level up from scripts)
    models_root = os.path.join(base_dir, "..", "models_storage")
    models_root = os.path.abspath(models_root)
    
    print(f"Models Root: {models_root}")
    
    if not os.path.exists(models_root):
        os.makedirs(models_root)
    
    # 1. Hynt Model
    hynt_dir = os.path.join(models_root, "zipformer", "hynt-zipformer-30M-6000h")
    if not os.path.exists(hynt_dir):
        os.makedirs(hynt_dir)
        
    print(f"--- Downloading Hynt Model to {hynt_dir} ---")
    for filename in HYNT_FILES:
        url = f"{HYNT_BASE_URL}/{filename}"
        dest_path = os.path.join(hynt_dir, filename)
        download_file(url, dest_path)
        
    # Generate tokens.txt for Hynt
    bpe_path = os.path.join(hynt_dir, "bpe.model")
    tokens_path = os.path.join(hynt_dir, "tokens.txt")
    if os.path.exists(bpe_path) and not os.path.exists(tokens_path):
        generate_tokens(bpe_path, tokens_path)
        
    # 2. HKAB Model
    hkab_dir = os.path.join(models_root, "hkab")
    print(f"\n--- Cloning HKAB Repo to {hkab_dir} ---")
    if not os.path.exists(hkab_dir):
        try:
            subprocess.check_call(["git", "clone", HKAB_REPO_URL, hkab_dir])
            print("HKAB repo cloned.")
        except Exception as e:
            print(f"Failed to clone HKAB repo: {e}")
    else:
        print("HKAB repo already exists.")
        
    print("\n--- PhoWhisper Setup (Optional) ---")
    print("To use PhoWhisper (Vietnamese specific), you need to convert it manually.")
    print("See docs/docs-models.md for details.")
    print("Command example (requires 'transformers' and 'torch' installed):")
    print("  ct2-transformers-converter --model vinai/PhoWhisper-small --output_dir backend/models_storage/phowhisper-ct2 --quantization int8")
        
    print("\nAll model preparations complete.")

if __name__ == "__main__":
    main()
