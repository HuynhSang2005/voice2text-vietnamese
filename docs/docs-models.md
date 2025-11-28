# DOCS-MODELS: Technical Specifications & Configuration

### 1. Comparative Matrix (Bảng thông số so sánh)

| Model              | Architecture          | Engine (Runner)    | Size (Params) | Quantization | RAM Est. | Latency Target |
| :----------------- | :-------------------- | :----------------- | :------------ | :----------- | :------- | :------------- |
| **Zipformer**      | Transducer (RNN-T)    | `sherpa-onnx`      | 30M           | int8         | ~200 MB  | < 500ms        |
| **Faster-Whisper** | Transformer (Enc-Dec) | `faster-whisper`   | Small (~244M) | int8         | ~500 MB  | 800ms - 2.0s   |
| **PhoWhisper**     | Transformer (Enc-Dec) | `faster-whisper`\* | Small (~244M) | int8         | ~1.5 GB  | 800ms - 2.0s   |
| **HKAB**           | RNN-Transducer        | `ONNX Runtime`     | ~30M          | fp32/int8    | ~300 MB  | < 500ms        |

> **\*Lưu ý:** PhoWhisper chạy trên engine `faster-whisper` yêu cầu phải convert model gốc từ HuggingFace sang định dạng CTranslate2.

---

### 2. Detailed Configuration (Cấu hình chi tiết)

#### A. Model 1: Zipformer (The Vietnamese Specialist)

Đây là model chính được tối ưu cho tiếng Việt.

- **Source:** `hynt/Zipformer-30M-RNNT-6000h` (Trained on 6000h Vietnamese)
- **Format:** ONNX (Open Neural Network Exchange).
- **Execution Engine:** `sherpa-onnx` (Python wrapper).
- **Implementation:** Sử dụng `OfflineRecognizer.from_transducer()` với buffered audio chunks (không phải true streaming).
- **Input Requirement:**
  - Audio chunks buffered (16000Hz, float32).
  - Feature extraction: Fbank (được xử lý nội bộ bởi sherpa).
- **Decoding Method:** Greedy Search (nhanh nhất).
- **File Assets cần thiết:**
  - `encoder-epoch-20-avg-10.int8.onnx`
  - `decoder-epoch-20-avg-10.int8.onnx`
  - `joiner-epoch-20-avg-10.int8.onnx`
  - `tokens.txt`, `bpe.model`

> **Note:** Mặc dù sherpa-onnx hỗ trợ `OnlineRecognizer` cho true streaming, implementation hiện tại sử dụng `OfflineRecognizer` với audio buffering.

#### B. Model 2: Faster-Whisper (The Generalist)

Model dùng làm baseline so sánh chuẩn quốc tế.

- **Source:** `SYSTRAN/faster-whisper` (model weights: `small` by default).
- **Execution Engine:** `CTranslate2` (thông qua thư viện `faster-whisper` v1.2.1+).
- **Buffering Strategy (Custom Energy-based VAD):**
  - Do Whisper là model "Buffered" (cần ngữ cảnh), chúng ta không gửi từng chunk nhỏ vào model.
  - **Logic:**
    1. Tích lũy audio vào buffer.
    2. **Min Duration:** 3.0s (Chờ đủ dữ liệu).
    3. **Silence Detection:** Kiểm tra energy của audio (`SILENCE_THRESHOLD = 0.0005`). Nếu lặng -> Transcribe.
    4. **Max Duration:** 15.0s (Force transcribe nếu buffer quá dài).
- **Settings:**
  - `device`: "cpu" (hoặc "cuda").
  - `compute_type`: "int8".
  - `beam_size`: 5.
  - `vad_filter`: False (sử dụng custom energy-based VAD thay vì Silero VAD built-in).

#### C. Model 3: PhoWhisper (The Vietnamese Expert)

Model chuyên dụng cho tiếng Việt từ VinAI.

- **Source:** `vinai/PhoWhisper-small` (~244M params, trained on 844h Vietnamese).
- **Variants:** tiny/base/small/medium/large (project dùng small).
- **Execution Engine:** `faster-whisper` (Load từ thư mục local `models_storage/phowhisper-ct2`).
- **Format:** CTranslate2 converted (gồm `model.bin`, `config.json`, `tokenizer.json`, `vocabulary.json`).
- **Fallback:** Nếu không tìm thấy model local, hệ thống sẽ tự động fallback về `faster-whisper` (small).

#### D. Model 4: HKAB (RNN-Transducer Vietnamese)

Model RNN-T open-source từ cộng đồng Vietnamese.

- **Source:** `HKAB/vietnamese-rnnt-tutorial` (6000h Vietnamese data).
- **Architecture:** RNN-Transducer với Whisper encoder.
- **Format:** ONNX (encoder-infer.onnx, decoder-infer.onnx, jointer-infer.onnx).
- **Quantization:** FP32 và INT8 (quant.onnx).
- **Performance:**
  - WER VIVOS: ~15% (Online ONNX FP32)
  - WER CM17: ~12.4% (Online ONNX FP32)
- **Implementation:** Custom ONNX inference với manual encoder/decoder/joiner loop.

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
        encoder-epoch-20-avg-10.int8.onnx
        decoder-epoch-20-avg-10.int8.onnx
        joiner-epoch-20-avg-10.int8.onnx
        tokens.txt
        bpe.model
    faster-whisper/
      models--Systran--faster-whisper-small/
        ...model files...
    phowhisper-ct2/
      model.bin
      config.json
      tokenizer.json
      vocabulary.json
      preprocessor_config.json
    hkab/
      onnx/
        encoder-infer.onnx
        decoder-infer.onnx
        jointer-infer.onnx
        *.quant.onnx (INT8 versions)
      weights/
      README.md
```

### 4. Hardware Requirements (Yêu cầu phần cứng)

- **CPU:** Tối thiểu 2 Cores. AVX2 support là bắt buộc cho quantization int8.
- **RAM:** Tối thiểu 4GB (cho OS + Docker + Models).
- **GPU (Optional):** Hỗ trợ CUDA nếu muốn chạy Whisper nhanh hơn. Zipformer chạy tốt trên CPU.
