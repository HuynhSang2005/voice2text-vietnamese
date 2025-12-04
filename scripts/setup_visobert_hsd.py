#!/usr/bin/env python3
"""
Setup script for ViSoBERT-HSD model.

This script downloads the ViSoBERT-HSD model from Hugging Face,
converts it to ONNX format, and applies INT8 quantization for optimal inference.

Usage:
    python scripts/setup_visobert_hsd.py

Output:
    models_storage/visobert-hsd/
    ├── onnx/           # ONNX FP32 model
    │   ├── model.onnx
    │   ├── tokenizer_config.json
    │   ├── vocab.txt
    │   └── ...
    └── onnx-int8/      # Quantized INT8 model (recommended)
        ├── model_quantized.onnx
        ├── tokenizer_config.json
        └── ...
"""

import os
import sys
import glob

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_model_paths():
    """Get model storage paths."""
    base_path = os.path.join("models_storage", "visobert-hsd")
    onnx_path = os.path.join(base_path, "onnx")
    int8_path = os.path.join(base_path, "onnx-int8")
    return base_path, onnx_path, int8_path


def download_and_convert_to_onnx(model_name: str, onnx_path: str):
    """Download model from HuggingFace and convert to ONNX."""
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer
    
    print(f"\n📥 Downloading model: {model_name}")
    print("   This may take a few minutes on first run...\n")
    
    # Download tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Export to ONNX (this downloads and converts in one step)
    print("🔄 Converting to ONNX format...")
    os.makedirs(onnx_path, exist_ok=True)
    
    ort_model = ORTModelForSequenceClassification.from_pretrained(
        model_name,
        export=True
    )
    
    # Save ONNX model and tokenizer
    ort_model.save_pretrained(onnx_path)
    tokenizer.save_pretrained(onnx_path)
    
    print(f"   ✅ ONNX model saved to: {onnx_path}")
    return ort_model, tokenizer


def quantize_to_int8(onnx_path: str, int8_path: str):
    """Apply INT8 dynamic quantization to ONNX model."""
    from optimum.onnxruntime import ORTQuantizer
    from optimum.onnxruntime.configuration import AutoQuantizationConfig
    from transformers import AutoTokenizer
    
    print("\n⚡ Quantizing to INT8...")
    os.makedirs(int8_path, exist_ok=True)
    
    # Load quantizer from ONNX model
    quantizer = ORTQuantizer.from_pretrained(onnx_path)
    
    # Configure dynamic quantization for AVX2 (most common desktop/laptop CPUs)
    qconfig = AutoQuantizationConfig.avx2(
        is_static=False,      # Dynamic quantization
        per_channel=False     # Per-tensor quantization
    )
    
    # Apply quantization
    quantizer.quantize(
        save_dir=int8_path,
        quantization_config=qconfig
    )
    
    # Copy tokenizer to quantized model directory
    tokenizer = AutoTokenizer.from_pretrained(onnx_path)
    tokenizer.save_pretrained(int8_path)
    
    print(f"   ✅ INT8 model saved to: {int8_path}")


def verify_models(onnx_path: str, int8_path: str):
    """Verify that models can be loaded and run inference."""
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer
    import numpy as np
    
    print("\n🔍 Verifying models...")
    
    # Test both models
    test_texts = [
        "Xin chào bạn, hôm nay thời tiết đẹp quá!",  # Should be CLEAN
        "Đồ ngu ngốc, mày làm ăn thế à?",            # Should be OFFENSIVE
    ]
    
    for model_path, model_name in [(onnx_path, "ONNX"), (int8_path, "INT8")]:
        if not os.path.exists(model_path):
            print(f"   ⚠️ {model_name} model not found, skipping verification")
            continue
            
        print(f"\n   Testing {model_name} model:")
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = ORTModelForSequenceClassification.from_pretrained(
            model_path,
            provider="CPUExecutionProvider"
        )
        
        label_map = {0: "CLEAN", 1: "OFFENSIVE", 2: "HATE"}
        
        for text in test_texts:
            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256
            )
            
            outputs = model(**inputs)
            logits = outputs.logits
            
            # Get prediction
            import torch
            probs = torch.softmax(logits, dim=-1)
            pred_id = logits.argmax(dim=-1).item()
            confidence = probs[0][pred_id].item()
            
            print(f"      \"{text[:30]}...\"")
            print(f"      → {label_map[pred_id]} (confidence: {confidence:.2%})")
    
    print("\n   ✅ Model verification complete!")


def print_size_comparison(onnx_path: str, int8_path: str):
    """Print model size comparison."""
    def get_dir_size(path):
        total = 0
        for f in glob.glob(os.path.join(path, "**/*"), recursive=True):
            if os.path.isfile(f):
                total += os.path.getsize(f)
        return total
    
    print("\n📊 Size Comparison:")
    
    if os.path.exists(onnx_path):
        onnx_size = get_dir_size(onnx_path)
        print(f"   ONNX FP32: {onnx_size / 1024 / 1024:.1f} MB")
    
    if os.path.exists(int8_path):
        int8_size = get_dir_size(int8_path)
        print(f"   ONNX INT8: {int8_size / 1024 / 1024:.1f} MB")
        
        if os.path.exists(onnx_path):
            reduction = (1 - int8_size / onnx_size) * 100
            print(f"   Reduction: {reduction:.1f}%")


def main():
    """Main entry point."""
    model_name = "visolex/visobert-hsd"
    
    print("=" * 60)
    print("  ViSoBERT-HSD Setup Script")
    print("  Model: visolex/visobert-hsd")
    print("  Output: models_storage/visobert-hsd/")
    print("=" * 60)
    
    base_path, onnx_path, int8_path = get_model_paths()
    
    # Check if already set up
    if os.path.exists(int8_path) and os.listdir(int8_path):
        print(f"\n⚠️ INT8 model already exists at: {int8_path}")
        response = input("   Do you want to re-download and convert? [y/N]: ")
        if response.lower() != 'y':
            print("   Skipping download. Verifying existing model...")
            verify_models(onnx_path, int8_path)
            print_size_comparison(onnx_path, int8_path)
            print("\n✅ Setup complete!")
            return
    
    try:
        # Step 1: Download and convert to ONNX
        ort_model, tokenizer = download_and_convert_to_onnx(model_name, onnx_path)
        
        # Step 2: Quantize to INT8
        quantize_to_int8(onnx_path, int8_path)
        
        # Step 3: Verify models
        verify_models(onnx_path, int8_path)
        
        # Step 4: Print size comparison
        print_size_comparison(onnx_path, int8_path)
        
        print("\n" + "=" * 60)
        print("  ✅ Setup Complete!")
        print("=" * 60)
        print(f"\n  INT8 model (recommended): {int8_path}")
        print(f"  ONNX model (backup):      {onnx_path}")
        print("\n  To use in your code:")
        print('    from app.workers.hate_detector import HateDetectorWorker')
        print("\n")
        
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("   Please install required packages:")
        print("   pip install transformers optimum[onnxruntime] onnxruntime")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
