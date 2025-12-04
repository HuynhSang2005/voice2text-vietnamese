# ViSoBERT-HSD (Hate Speech Detection)

## Tổng quan

**ViSoBERT-HSD** là model được fine-tune từ [uitnlp/visobert](https://huggingface.co/uitnlp/visobert) cho bài toán **Hate Speech Detection** tiếng Việt. Model này sẽ được tích hợp vào hệ thống để phát hiện và gắn cờ nội dung độc hại từ kết quả transcription.

- **Source:** `visolex/visobert-hsd`
- **Base Model:** `uitnlp/visobert` (XLM-RoBERTa architecture)
- **Task:** Text Classification (3 classes)
- **License:** Apache-2.0

---

## Thông số Model

### Kích thước & Tài nguyên

| Thuộc tính | Giá trị |
|------------|---------|
| **Parameters** | ~97.6M |
| **Architecture** | XLM-RoBERTa (Encoder-only) |
| **Tensor Type** | FP32 |
| **Model Size (disk)** | ~400MB |
| **Memory (inference)** | ~400-500MB RAM |
| **Max Sequence Length** | 256 tokens |

### Labels (Phân loại 3 mức)

| Label ID | Label Name | Mô tả |
|----------|------------|-------|
| 0 | **CLEAN** | Nội dung bình thường, không có ngôn từ xúc phạm |
| 1 | **OFFENSIVE** | Nội dung có ngôn từ thô tục, xúc phạm nhẹ |
| 2 | **HATE** | Ngôn từ thù địch, kích động bạo lực, phân biệt |

---

## Dataset & Training

### VN-HSD Dataset

Model được train trên **VN-HSD** (Vietnamese Hate Speech Dataset), là bộ dataset thống nhất kết hợp từ nhiều nguồn:

- **ViHSD**: Vietnamese Hate Speech Dataset gốc
- **ViCTSD**: Vietnamese Constructive and Toxic Speech Dataset  
- **ViHOS**: Vietnamese Hate and Offensive Spans

### Hyperparameters

```yaml
batch_size: 32
learning_rate: 3e-5
epochs: 100
max_sequence_length: 256
optimizer: AdamW
framework: HuggingFace Transformers
```

---

## Cách sử dụng

### Basic Usage (PyTorch)

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load model
tokenizer = AutoTokenizer.from_pretrained("visolex/visobert-hsd")
model = AutoModelForSequenceClassification.from_pretrained("visolex/visobert-hsd")

# Classify text
text = "Hắn ta thật kinh tởm!"
inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)

with torch.no_grad():
    logits = model(**inputs).logits
    probabilities = torch.softmax(logits, dim=-1)
    predicted_label = logits.argmax(dim=-1).item()

# Map to label name
label_map = {0: "CLEAN", 1: "OFFENSIVE", 2: "HATE"}
print(f"Predicted: {label_map[predicted_label]}")
print(f"Confidence: {probabilities[0][predicted_label]:.2%}")
```

### Using Pipeline API

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="visolex/visobert-hsd",
    tokenizer="visolex/visobert-hsd"
)

result = classifier("Đừng nói những lời thô tục như vậy!")
print(result)
# [{'label': 'LABEL_1', 'score': 0.89}]
```

---

## So sánh với các Model khác

| Model | Base | Size | Kiến trúc | Ưu điểm | Nhược điểm |
|-------|------|------|-----------|---------|------------|
| **visobert-hsd** ✅ | uitnlp/visobert | 97.6M | XLM-RoBERTa | Nhẹ nhất, dễ ONNX | Ít downloads |
| phobert-hsd | vinai/phobert | 135M | RoBERTa | Phổ biến hơn | Nặng hơn |
| vihate-t5-hsd | VietAI/vit5-base | 220M | T5 Enc-Dec | Accuracy 95.51% | Quá nặng cho real-time |
| bartpho-hsd | vinai/bartpho | 400M | BART | Mạnh nhất | Không phù hợp edge |

### Tại sao chọn ViSoBERT-HSD?

1. **Nhẹ nhất** trong các model có performance tương đương
2. **Encoder-only** architecture phù hợp cho classification (không cần decoder)
3. **Dễ convert ONNX** và quantize cho production
4. **XLM-RoBERTa base** - được train trên 100+ ngôn ngữ, robust hơn
5. **Dataset đa dạng** - VN-HSD kết hợp 3 nguồn data

---

## Ưu điểm & Nhược điểm

| Ưu điểm | Nhược điểm |
|---------|------------|
| **Nhẹ:** Chỉ ~400MB RAM | **Accuracy:** Chưa có benchmark công bố chi tiết |
| **Nhanh:** Latency ~20-50ms/request | **Data bias:** Train chủ yếu từ mạng xã hội |
| **3 mức phân loại:** Chi tiết hơn binary | **False positives:** Có thể với ngữ cảnh đặc biệt |
| **ONNX compatible:** Dễ tối ưu | **Token limit:** Max 256 tokens |

---

## Tích hợp với Hệ thống

### Vị trí trong Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│   Audio     │────▶│  Zipformer   │────▶│  ViSoBERT-HSD   │────▶│  Client  │
│   Stream    │     │  (STT)       │     │  (Detection)    │     │  Result  │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────┘
     16kHz           Transcription          CLEAN/OFFENSIVE/        JSON
                                            HATE label
```

### Output Format (Đề xuất)

```json
{
  "text": "Transcribed text here",
  "is_final": true,
  "model": "zipformer",
  "latency_ms": 45.2,
  "content_moderation": {
    "label": "CLEAN",
    "confidence": 0.95,
    "is_flagged": false
  }
}
```

---

## Files & Storage

### Đề xuất cấu trúc thư mục

```
backend/models_storage/
├── zipformer/
│   └── hynt-zipformer-30M-6000h/
│       ├── encoder-epoch-20-avg-10.int8.onnx
│       ├── decoder-epoch-20-avg-10.int8.onnx
│       ├── joiner-epoch-20-avg-10.int8.onnx
│       └── tokens.txt
│
└── visobert-hsd/                    # NEW
    ├── config.json
    ├── tokenizer.json
    ├── tokenizer_config.json
    ├── special_tokens_map.json
    ├── sentencepiece.bpe.model
    └── model.safetensors            # ~400MB (FP32)
    # Hoặc sau khi optimize:
    └── model.onnx                   # ~100MB (INT8 quantized)
```

---

## References

- **HuggingFace:** https://huggingface.co/visolex/visobert-hsd
- **Base Model:** https://huggingface.co/uitnlp/visobert
- **Collection:** https://huggingface.co/collections/visolex/hate-speech-detection
- **Paper (ViSoBERT):** Vietnamese Social Media Text Processing

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-02 | Initial documentation |
