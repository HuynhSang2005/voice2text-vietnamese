# DOCS-MODELS: Technical Specifications & Configuration

### 1. Comparative Matrix (Bảng thông số so sánh)

| Model              | Architecture          | Engine (Runner)    | Size (Params) | Quantization | RAM Est. | Latency Target |
| :----------------- | :-------------------- | :----------------- | :------------ | :----------- | :------- | :------------- |
| **Zipformer**      | Transducer (RNN-T)    | `sherpa-onnx`      | 30M           | int8         | ~200 MB  | < 300ms        |
| **Faster-Whisper** | Transformer (Enc-Dec) | `faster-whisper`   | Small         | int8         | ~500 MB  | 800ms - 2.0s   |
| **PhoWhisper**     | Transformer (Enc-Dec) | `faster-whisper`\* | Small/Medium  | int8         | ~1.5 GB  | 800ms - 2.0s   |

> **\*Lưu ý:** PhoWhisper chạy trên engine `faster-whisper` yêu cầu phải convert model gốc từ HuggingFace sang định dạng CTranslate2.

---

### 2. Detailed Configuration (Cấu hình chi tiết)

#### A. Model 1: Zipformer (The Streaming Specialist)

Đây là model chủ lực cho demo "True Real-time".

- **Source:** `hynt/Zipformer-30M-RNNT-6000h`
- **Format:** ONNX (Open Neural Network Exchange).
- **Execution Engine:** `sherpa-onnx` (Python wrapper).
- **Implementation:** Sử dụng `OfflineRecognizer` kết hợp với `create_stream()` để xử lý audio chunk-by-chunk.
- **Input Requirement:**
  - Stream audio liên tục (chunk 16000Hz, int16/float32).
  - Feature extraction: Fbank (được xử lý nội bộ bởi sherpa).
- **Decoding Method:** Greedy Search (nhanh nhất).
- **File Assets cần thiết:**
  - `encoder-epoch-20-avg-10.int8.onnx`
  - `decoder-epoch-20-avg-10.int8.onnx`
  - `joiner-epoch-20-avg-10.int8.onnx`
  - `tokens.txt` (Generated from `bpe.model`)

#### B. Model 2: Faster-Whisper (The Generalist)

Model dùng làm baseline so sánh chuẩn quốc tế.

- **Source:** `SYSTRAN/faster-whisper` (model weights: `small` by default).
- **Execution Engine:** `CTranslate2` (thông qua thư viện `faster-whisper`).
- **Buffering Strategy (Custom VAD):**
  - Do Whisper là model "Buffered" (cần ngữ cảnh), chúng ta không gửi từng chunk nhỏ vào model.
  - **Logic:**
    1. Tích lũy audio vào buffer.
    2. **Min Duration:** 2.0s (Chờ đủ dữ liệu).
    3. **Silence Detection:** Kiểm tra 0.5s cuối xem có lặng không (Energy threshold). Nếu lặng -> Transcribe.
    4. **Max Duration:** 10.0s (Force transcribe nếu buffer quá dài).
- **Settings:**
  - `device`: "cpu" (hoặc "cuda").
  - `compute_type`: "int8".
  - `beam_size`: 1.

#### C. Model 3: PhoWhisper (The Vietnamese Expert)

Model chuyên dụng cho tiếng Việt.

- **Source:** `vinai/PhoWhisper-small` (Converted to CTranslate2).
- **Execution Engine:** `faster-whisper` (Load từ thư mục local `models_storage/phowhisper-ct2`).
- **Fallback:** Nếu không tìm thấy model local, hệ thống sẽ tự động fallback về `faster-whisper` (small).

---

### 3. Directory Structure (Cấu trúc thư mục Model)

Hệ thống sử dụng thư mục `backend/models_storage` để lưu trữ tất cả model. Script `backend/scripts/setup_models.py` sẽ tự động tạo và tải file vào đây.

```text
backend/
  scripts/
    setup_models.py       # Script tải và setup model
  models_storage/
    zipformer/
      hynt-zipformer-30M-6000h/
        ...onnx files...
        tokens.txt
    hkab/                 # Source code HKAB (nếu dùng)
    phowhisper-ct2/       # (Optional) Manual convert
```

### 4. Hardware Requirements (Yêu cầu phần cứng)

- **CPU:** Tối thiểu 2 Cores. AVX2 support là bắt buộc cho quantization int8.
- **RAM:** Tối thiểu 4GB (cho OS + Docker + Models).
- **GPU (Optional):** Hỗ trợ CUDA nếu muốn chạy Whisper nhanh hơn. Zipformer chạy tốt trên CPU.
