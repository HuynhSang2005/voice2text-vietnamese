# Faster-Whisper (Buffered ASR)

## Tổng quan

**Faster-Whisper** là phiên bản tối ưu hóa của OpenAI Whisper, sử dụng engine **CTranslate2** để tăng tốc độ suy luận (inference) lên gấp 4 lần so với bản gốc. Đây là model "Generalist" với độ chính xác cao nhưng độ trễ lớn hơn Zipformer.

- **Source:** `SYSTRAN/faster-whisper` (Model `small` hoặc `medium`)
- **Engine:** `faster-whisper` (CTranslate2 backend)
- **Độ trễ mục tiêu:** 800ms - 2.0s

---

## Chiến lược Buffering (VAD)

Khác với Zipformer (Streaming), Whisper cần ngữ cảnh (context) để hoạt động chính xác. Do đó, chúng ta không thể gửi từng chunk nhỏ vào model. Chúng ta sử dụng chiến lược **VAD-based Buffering**:

1.  **Tích lũy (Accumulate):** Audio được lưu vào bộ đệm tạm thời (`self.buffer`).
2.  **Kiểm tra độ dài tối thiểu (Min Duration):**
    - Chỉ bắt đầu kiểm tra khi buffer > **2.0 giây**.
3.  **Phát hiện khoảng lặng (Silence Detection):**
    - Kiểm tra năng lượng (Energy) của 0.5 giây cuối cùng.
    - Nếu năng lượng < `SILENCE_THRESHOLD` -> Coi là hết câu -> Gửi vào model.
4.  **Bắt buộc xử lý (Max Duration):**
    - Nếu buffer > **10.0 giây** mà chưa thấy khoảng lặng -> Bắt buộc gửi vào model để tránh trễ quá lâu.

---

## Cấu hình & Sử dụng

### Load Model

```python
from faster_whisper import WhisperModel

model = WhisperModel(
    "small",          # Hoặc đường dẫn local
    device="cpu",     # Hoặc "cuda"
    compute_type="int8" # Tối ưu cho CPU
)
```

### Xử lý (Transcribe)

```python
segments, info = model.transcribe(
    audio_buffer,
    language="vi",
    beam_size=1,      # Beam size 1 để nhanh nhất
    vad_filter=True   # Dùng VAD nội bộ của Whisper để lọc nhiễu
)
```

---

## Ưu điểm & Nhược điểm

| Ưu điểm                                                | Nhược điểm                                |
| :----------------------------------------------------- | :---------------------------------------- |
| **Chính xác cao:** Hiểu ngữ cảnh tốt, tự thêm dấu câu. | **Độ trễ:** Phải chờ đủ câu mới hiện chữ. |
| **Đa năng:** Hỗ trợ nhiều ngôn ngữ (nếu cần).          | **Nặng:** Tốn RAM hơn (~500MB - 1.5GB).   |
| **Cộng đồng lớn:** Dễ tìm support và fine-tune.        |                                           |
