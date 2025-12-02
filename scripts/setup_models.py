#!/usr/bin/env python3
"""
Setup Models Script
===================
Downloads and configures the Zipformer AI model for the Vietnamese Speech-to-Text system.

Model:
- Zipformer (Hynt) - RNN-T model from HuggingFace (30M params, trained on 6000h Vietnamese data)

Usage:
    python scripts/setup_models.py              # Setup Zipformer model
    python scripts/setup_models.py --zipformer  # Same as above

Requirements:
    - Python 3.10+
    - Internet connection
    - ~200MB disk space for Zipformer model
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


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup Zipformer model for Vietnamese Speech-to-Text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/setup_models.py              # Setup Zipformer model
    python scripts/setup_models.py --zipformer  # Same as above
        """
    )
    
    parser.add_argument("--zipformer", action="store_true", help="Setup Zipformer model (default)")
    
    args = parser.parse_args()
    
    print_header("Vietnamese Speech-to-Text Model Setup")
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Models Directory: {MODELS_DIR}")
    
    # Ensure models directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Setup Zipformer (the only supported model now)
    results["Zipformer"] = setup_zipformer()
    
    # Print summary
    print_header("Setup Summary")
    
    for model, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {model}: {status}")
    
    # Overall status
    all_success = all(results.values())
    
    if all_success:
        print("\n" + "=" * 60)
        print("  🎉 Model setup successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. cd backend")
        print("  2. pip install -r requirements.txt")
        print("  3. python main.py")
        return 0
    else:
        print("\n" + "=" * 60)
        print("  ⚠️  Model setup failed. Check errors above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
