# PhoWhisper (Vietnamese Expert)

## Tổng quan

**PhoWhisper** là phiên bản Whisper được VinAI fine-tune đặc biệt cho tiếng Việt. Nó có khả năng nhận diện các từ vựng đặc thù, tên riêng và ngữ pháp tiếng Việt tốt hơn bản gốc.

- **Source:** `vinai/PhoWhisper-small`
- **Engine:** `faster-whisper` (Yêu cầu convert sang CTranslate2)
- **Độ trễ:** Tương đương Faster-Whisper.

---

## Hướng dẫn Convert (Bắt buộc)

Model gốc trên HuggingFace (`vinai/PhoWhisper-small`) là định dạng PyTorch/HuggingFace. Để chạy nhanh với engine `faster-whisper`, chúng ta **BẮT BUỘC** phải convert nó sang định dạng CTranslate2.

### Bước 1: Cài đặt công cụ

Bạn cần cài đặt thư viện `ctranslate2` và `transformers` trên máy của mình (hoặc trong venv):

```bash
pip install ctranslate2 transformers torch
```

### Bước 2: Chạy lệnh Convert

Chạy lệnh sau từ thư mục gốc của dự án:

```bash
ct2-transformers-converter --model vinai/PhoWhisper-small --output_dir backend/models_storage/phowhisper-ct2 --quantization int8 --copy_files tokenizer.json preprocessor_config.json
```

- `--model`: Tên model trên HuggingFace.
- `--output_dir`: Đường dẫn lưu model đã convert (Backend sẽ đọc từ đây).
- `--quantization int8`: Nén model xuống int8 để chạy nhanh trên CPU.

### Bước 3: Kiểm tra

Sau khi chạy xong, kiểm tra thư mục `backend/models_storage/phowhisper-ct2`, bạn sẽ thấy các file `model.bin`, `config.json`, `vocabulary.json`.

---

## Cấu hình trong Backend

Backend sẽ tự động kiểm tra xem thư mục `backend/models_storage/phowhisper-ct2` có tồn tại hay không.

- **Nếu có:** Load PhoWhisper từ thư mục đó.
- **Nếu không:** Tự động fallback về `faster-whisper` (small) chuẩn và cảnh báo trong log.

```python
# Logic trong whisper.py
if model_name == "phowhisper":
    model_dir = "models_storage/phowhisper-ct2"
    if os.path.exists(model_dir):
        self.model = WhisperModel(model_dir, ...)
    else:
        print("Fallback to standard Whisper...")
        self.model = WhisperModel("small", ...)
```
