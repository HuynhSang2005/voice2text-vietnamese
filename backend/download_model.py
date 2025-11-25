#!/usr/bin/env python3
"""
Script to download Zipformer Vietnamese model for sherpa-onnx
"""
import os
import urllib.request
import zipfile
import sys

MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-int8-2025-04-20.tar.bz2"
MODEL_DIR = "models_storage/zipformer"

def download_model():
    """Download and extract Zipformer Vietnamese model"""
    
    # Create directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Download file
    filename = "zipformer-vietnamese-int8.tar.bz2"
    filepath = os.path.join(MODEL_DIR, filename)
    
    print(f"Downloading Zipformer Vietnamese model from {MODEL_URL}...")
    print(f"This may take a few minutes...")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, filepath)
        print(f"✓ Downloaded to {filepath}")
    except Exception as e:
        print(f"✗ Failed to download: {e}")
        sys.exit(1)
    
    # Extract
    print("Extracting model files...")
    try:
        import tarfile
        with tarfile.open(filepath, 'r:bz2') as tar:
            tar.extractall(MODEL_DIR)
        print(f"✓ Extracted to {MODEL_DIR}")
        
        # Remove tar file
        os.remove(filepath)
        print(f"✓ Cleaned up {filename}")
        
        # List extracted files
        print("\nExtracted files:")
        for root, dirs, files in os.walk(MODEL_DIR):
            for file in files:
                print(f"  - {os.path.join(root, file)}")
                
        print("\n✓ Model download complete!")
        print(f"\nModel files are in: {os.path.abspath(MODEL_DIR)}")
        
    except Exception as e:
        print(f"✗ Failed to extract: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_model()
