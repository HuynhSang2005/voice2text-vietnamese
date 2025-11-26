import os
import urllib.request
import shutil
import subprocess
import sys

"""
SETUP MODELS SCRIPT
-------------------
Script này tự động tải và cài đặt các model AI cần thiết cho Backend.
Đảm bảo môi trường "Clone & Run" cho developer mới.

Chức năng:
1. Tải Zipformer model (Sherpa-ONNX).
2. Generate tokens.txt từ bpe.model.
3. Clone HKAB repo (Tham khảo).
4. Hướng dẫn convert PhoWhisper.

Sử dụng:
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

def check_system_deps():
    """Kiểm tra các dependencies hệ thống cần thiết."""
    print("--- Checking System Dependencies ---")
    
    # Check Git
    if shutil.which("git") is None:
        print("[WARNING] 'git' not found. HKAB cloning will fail.")
    else:
        print("[OK] git found.")
        
    # Check FFmpeg (Optional but good for audio)
    if shutil.which("ffmpeg") is None:
        print("[WARNING] 'ffmpeg' not found. Audio processing might fail at runtime.")
    else:
        print("[OK] ffmpeg found.")

def download_file(url, dest_path):
    if os.path.exists(dest_path):
        print(f"[SKIP] File exists: {os.path.basename(dest_path)}")
        return
    print(f"[DOWNLOADING] {url} -> {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print("[DONE] Download complete.")
    except Exception as e:
        print(f"[ERROR] Failed to download {url}: {e}")
        pass

def generate_tokens(bpe_model_path, tokens_path):
    print(f"[GENERATING] tokens.txt from {bpe_model_path}...")
    try:
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.load(bpe_model_path)
        
        with open(tokens_path, "w", encoding="utf-8") as f:
            for i in range(sp.get_piece_size()):
                piece = sp.id_to_piece(i)
                f.write(f"{piece} {i}\n")
        print(f"[DONE] Generated {tokens_path}")
    except ImportError:
        print("[ERROR] 'sentencepiece' not installed. Run 'pip install sentencepiece'")
    except Exception as e:
        print(f"[ERROR] Error generating tokens: {e}")

def main():
    check_system_deps()
    
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Models are in backend/models_storage (one level up from scripts)
    models_root = os.path.join(base_dir, "..", "models_storage")
    models_root = os.path.abspath(models_root)
    
    print(f"\nModels Root: {models_root}")
    
    if not os.path.exists(models_root):
        os.makedirs(models_root)
    
    # 1. Hynt Model
    hynt_dir = os.path.join(models_root, "zipformer", "hynt-zipformer-30M-6000h")
    if not os.path.exists(hynt_dir):
        os.makedirs(hynt_dir)
        
    print(f"\n--- 1. Setup Zipformer (Hynt) ---")
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
    print(f"\n--- 2. Setup HKAB (Git Clone) ---")
    if not os.path.exists(hkab_dir):
        try:
            subprocess.check_call(["git", "clone", HKAB_REPO_URL, hkab_dir])
            print("[DONE] HKAB repo cloned.")
        except Exception as e:
            print(f"[ERROR] Failed to clone HKAB repo: {e}")
    else:
        print("[SKIP] HKAB repo already exists.")
        
    print("\n--- 3. PhoWhisper Instructions ---")
    print("PhoWhisper cần được convert thủ công (do yêu cầu thư viện nặng).")
    print("Chạy lệnh sau nếu bạn muốn dùng PhoWhisper:")
    print(f"  ct2-transformers-converter --model vinai/PhoWhisper-small --output_dir {os.path.join(models_root, 'phowhisper-ct2')} --quantization int8")
        
    print("\n[SUCCESS] All model preparations complete.")

if __name__ == "__main__":
    main()
