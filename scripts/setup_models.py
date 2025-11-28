#!/usr/bin/env python3
"""
Setup Models Script
===================
Downloads and configures all AI models for the Vietnamese Speech-to-Text system.

Models:
1. Zipformer (Hynt) - RNN-T model from HuggingFace (30M params)
2. Faster-Whisper - OpenAI Whisper optimized with CTranslate2
3. PhoWhisper - VinAI's Vietnamese-optimized Whisper
4. HKAB - Community RNN-T model with ONNX export

Usage:
    python scripts/setup_models.py              # Setup all models
    python scripts/setup_models.py --zipformer  # Setup only Zipformer
    python scripts/setup_models.py --whisper    # Setup only Faster-Whisper
    python scripts/setup_models.py --phowhisper # Setup only PhoWhisper
    python scripts/setup_models.py --hkab       # Setup only HKAB

Requirements:
    - Python 3.10+
    - Internet connection
    - ~5GB disk space for all models
"""
import os
import sys
import shutil
import argparse
import subprocess
import urllib.request
from pathlib import Path
from typing import List, Optional

# ============================================================================
# Configuration
# ============================================================================

# Get the project root (parent of scripts/)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
MODELS_DIR = BACKEND_DIR / "models_storage"

# Hynt Zipformer Model (HuggingFace)
# Note: tokens.txt is NOT on HuggingFace - it must be generated from bpe.model
HYNT_REPO_ID = "hynt/Zipformer-30M-RNNT-6000h"
HYNT_BASE_URL = f"https://huggingface.co/{HYNT_REPO_ID}/resolve/main"
HYNT_FILES = [
    "encoder-epoch-20-avg-10.int8.onnx",
    "decoder-epoch-20-avg-10.int8.onnx",
    "joiner-epoch-20-avg-10.int8.onnx",
    "bpe.model",
    # tokens.txt will be generated from bpe.model
]

# HKAB Model (GitHub)
HKAB_REPO_URL = "https://github.com/HKAB/vietnamese-rnnt-tutorial.git"

# PhoWhisper Model (VinAI)
PHOWHISPER_MODEL = "vinai/PhoWhisper-small"


# ============================================================================
# Utility Functions
# ============================================================================

def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: str):
    """Print a step indicator."""
    print(f"\n>>> {step}")


def download_file(url: str, dest_path: Path, show_progress: bool = True) -> bool:
    """
    Download a file from URL to destination path.
    
    Args:
        url: Source URL
        dest_path: Destination file path
        show_progress: Whether to show download progress
        
    Returns:
        True if successful, False otherwise
    """
    if dest_path.exists():
        print(f"    [SKIP] Already exists: {dest_path.name}")
        return True
    
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"    [DOWNLOADING] {dest_path.name}...")
        
        # Create request with User-Agent
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ModelSetup/1.0)'}
        )
        
        with urllib.request.urlopen(request, timeout=300) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if show_progress and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r    Progress: {percent:.1f}%", end='', flush=True)
            
            if show_progress:
                print()  # New line after progress
        
        print(f"    [DONE] Downloaded: {dest_path.name}")
        return True
        
    except Exception as e:
        print(f"    [ERROR] Failed to download {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def generate_tokens_from_bpe(bpe_path: Path, tokens_path: Path) -> bool:
    """
    Generate tokens.txt from bpe.model using sentencepiece.
    
    Args:
        bpe_path: Path to bpe.model file
        tokens_path: Path to output tokens.txt
        
    Returns:
        True if successful, False otherwise
    """
    if tokens_path.exists():
        print(f"    [SKIP] Already exists: {tokens_path.name}")
        return True
    
    try:
        import sentencepiece as spm
        
        print(f"    [GENERATING] tokens.txt from bpe.model...")
        sp = spm.SentencePieceProcessor()
        sp.load(str(bpe_path))
        
        with open(tokens_path, "w", encoding="utf-8") as f:
            for i in range(sp.get_piece_size()):
                piece = sp.id_to_piece(i)
                f.write(f"{piece} {i}\n")
        
        print(f"    [DONE] Generated: {tokens_path.name}")
        return True
        
    except ImportError:
        print("    [ERROR] 'sentencepiece' not installed. Run: pip install sentencepiece")
        return False
    except Exception as e:
        print(f"    [ERROR] Failed to generate tokens: {e}")
        return False


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


# ============================================================================
# Model Setup Functions
# ============================================================================

def setup_zipformer() -> bool:
    """
    Setup Zipformer (Hynt) model from HuggingFace.
    Downloads ONNX model files and generates tokens.txt if needed.
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Setting up Zipformer (Hynt)")
    
    model_dir = MODELS_DIR / "zipformer" / "hynt-zipformer-30M-6000h"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Model directory: {model_dir}")
    
    success = True
    
    # Download all model files
    print_step("Downloading model files from HuggingFace...")
    for filename in HYNT_FILES:
        url = f"{HYNT_BASE_URL}/{filename}"
        dest_path = model_dir / filename
        if not download_file(url, dest_path):
            success = False
    
    # Generate tokens.txt from bpe.model if needed
    bpe_path = model_dir / "bpe.model"
    tokens_path = model_dir / "tokens.txt"
    
    if bpe_path.exists() and not tokens_path.exists():
        print_step("Generating tokens.txt from bpe.model...")
        if not generate_tokens_from_bpe(bpe_path, tokens_path):
            success = False
    
    if success:
        print("\n✅ Zipformer setup complete!")
    else:
        print("\n❌ Zipformer setup had errors. Check messages above.")
    
    return success


def setup_faster_whisper() -> bool:
    """
    Setup Faster-Whisper model.
    Uses the faster-whisper library to download the 'small' model.
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Setting up Faster-Whisper")
    
    model_dir = MODELS_DIR / "faster-whisper"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Model directory: {model_dir}")
    
    try:
        print_step("Downloading Faster-Whisper (small) model...")
        print("    This may take a few minutes...")
        
        from faster_whisper import WhisperModel
        
        # The library will download to the specified directory
        model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
            download_root=str(model_dir)
        )
        
        print("\n✅ Faster-Whisper setup complete!")
        return True
        
    except ImportError:
        print("    [ERROR] 'faster-whisper' not installed.")
        print("    Run: pip install faster-whisper")
        return False
    except Exception as e:
        print(f"    [ERROR] Failed to setup Faster-Whisper: {e}")
        return False


def setup_phowhisper() -> bool:
    """
    Setup PhoWhisper (VinAI) model.
    Converts the HuggingFace model to CTranslate2 format.
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Setting up PhoWhisper (VinAI)")
    
    output_dir = MODELS_DIR / "phowhisper-ct2"
    
    # Check if already converted
    if (output_dir / "model.bin").exists():
        print(f"    [SKIP] PhoWhisper already installed at {output_dir}")
        print("\n✅ PhoWhisper setup complete!")
        return True
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Check if ct2-transformers-converter is available
    if not check_command_exists("ct2-transformers-converter"):
        print("    [ERROR] 'ct2-transformers-converter' not found.")
        print("    Install with: pip install ctranslate2 transformers[torch]")
        print("\n    Manual conversion command:")
        print(f"    ct2-transformers-converter --model {PHOWHISPER_MODEL} \\")
        print(f"        --output_dir {output_dir} --quantization int8 \\")
        print("        --copy_files tokenizer.json preprocessor_config.json")
        return False
    
    try:
        print_step(f"Converting {PHOWHISPER_MODEL} to CTranslate2 format...")
        print("    This may take 5-10 minutes and requires ~8GB RAM...")
        
        cmd = [
            "ct2-transformers-converter",
            "--model", PHOWHISPER_MODEL,
            "--output_dir", str(output_dir),
            "--quantization", "int8",
            "--copy_files", "tokenizer.json", "preprocessor_config.json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    [ERROR] Conversion failed: {result.stderr}")
            return False
        
        print("\n✅ PhoWhisper setup complete!")
        return True
        
    except Exception as e:
        print(f"    [ERROR] Failed to setup PhoWhisper: {e}")
        return False


def setup_hkab() -> bool:
    """
    Setup HKAB model by cloning the GitHub repository.
    The repo includes pre-exported ONNX models.
    
    Returns:
        True if successful, False otherwise
    """
    print_header("Setting up HKAB (RNN-Transducer)")
    
    hkab_dir = MODELS_DIR / "hkab"
    
    # Check if already cloned
    if (hkab_dir / "onnx" / "encoder-infer.quant.onnx").exists():
        print(f"    [SKIP] HKAB already installed at {hkab_dir}")
        print("\n✅ HKAB setup complete!")
        return True
    
    # Check if git is available
    if not check_command_exists("git"):
        print("    [ERROR] 'git' not found. Please install git and try again.")
        print(f"    Manual clone: git clone {HKAB_REPO_URL} {hkab_dir}")
        return False
    
    try:
        if hkab_dir.exists():
            print(f"    [INFO] Removing existing directory: {hkab_dir}")
            shutil.rmtree(hkab_dir)
        
        print_step("Cloning HKAB repository...")
        print(f"    From: {HKAB_REPO_URL}")
        print(f"    To: {hkab_dir}")
        
        result = subprocess.run(
            ["git", "clone", "--depth", "1", HKAB_REPO_URL, str(hkab_dir)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"    [ERROR] Clone failed: {result.stderr}")
            return False
        
        # Verify ONNX files exist
        onnx_dir = hkab_dir / "onnx"
        required_files = [
            "encoder-infer.quant.onnx",
            "decoder-infer.quant.onnx",
            "jointer-infer.quant.onnx"
        ]
        
        missing = [f for f in required_files if not (onnx_dir / f).exists()]
        if missing:
            print(f"    [WARNING] Missing ONNX files: {missing}")
            print("    The ONNX export may need to be done manually.")
            print("    See: notebooks/inference.ipynb in the HKAB repo")
        
        print("\n✅ HKAB setup complete!")
        return True
        
    except Exception as e:
        print(f"    [ERROR] Failed to setup HKAB: {e}")
        return False


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup AI models for Vietnamese Speech-to-Text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/setup_models.py              # Setup all models
    python scripts/setup_models.py --zipformer  # Setup only Zipformer
    python scripts/setup_models.py --whisper    # Setup only Faster-Whisper
    python scripts/setup_models.py --phowhisper # Setup only PhoWhisper
    python scripts/setup_models.py --hkab       # Setup only HKAB
        """
    )
    
    parser.add_argument("--zipformer", action="store_true", help="Setup Zipformer model only")
    parser.add_argument("--whisper", action="store_true", help="Setup Faster-Whisper model only")
    parser.add_argument("--phowhisper", action="store_true", help="Setup PhoWhisper model only")
    parser.add_argument("--hkab", action="store_true", help="Setup HKAB model only")
    parser.add_argument("--skip-phowhisper", action="store_true", help="Skip PhoWhisper (requires conversion)")
    
    args = parser.parse_args()
    
    # Determine which models to setup
    specific_model = args.zipformer or args.whisper or args.phowhisper or args.hkab
    
    print_header("Vietnamese Speech-to-Text Model Setup")
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Models Directory: {MODELS_DIR}")
    
    # Ensure models directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Setup selected models
    if not specific_model or args.zipformer:
        results["Zipformer"] = setup_zipformer()
    
    if not specific_model or args.whisper:
        results["Faster-Whisper"] = setup_faster_whisper()
    
    if not specific_model or args.phowhisper:
        if not args.skip_phowhisper:
            results["PhoWhisper"] = setup_phowhisper()
        else:
            print_header("Skipping PhoWhisper (--skip-phowhisper)")
    
    if not specific_model or args.hkab:
        results["HKAB"] = setup_hkab()
    
    # Print summary
    print_header("Setup Summary")
    
    for model, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {model}: {status}")
    
    # Overall status
    all_success = all(results.values())
    
    if all_success:
        print("\n" + "=" * 60)
        print("  🎉 All models setup successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. cd backend")
        print("  2. pip install -r requirements.txt")
        print("  3. python main.py")
        return 0
    else:
        print("\n" + "=" * 60)
        print("  ⚠️  Some models failed to setup. Check errors above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
