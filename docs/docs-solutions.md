# DOCS-SOLUTIONS: Core Logic & System Algorithms

### 1\. Dual-Strategy Processing (Chiến lược xử lý kép)

Do tính chất khác biệt của các model, Backend sẽ áp dụng **Strategy Pattern** để tách biệt logic xử lý luồng âm thanh.

#### A. Strategy 1: Buffered Offline (Dành cho Zipformer/HKAB)

> **Lưu ý:** Mặc dù Zipformer/HKAB là RNN-T models có khả năng true streaming, implementation hiện tại sử dụng **OfflineRecognizer** với audio buffering để đơn giản hóa.

- **Nguyên lý:** Accumulate audio chunks → Process full buffer → Return result.
- **Logic Flow:**
  1.  Nhận Audio Chunk từ Queue.
  2.  Buffer audio cho đến khi đủ dữ liệu hoặc gặp silence.
  3.  Feed buffer vào `sherpa-onnx.OfflineRecognizer` (Zipformer) hoặc ONNX Runtime (HKAB).
  4.  Trả về kết quả transcription.
  5.  Clear buffer, repeat.

#### B. Strategy 2: Energy-based VAD Buffered (Dành cho Faster/PhoWhisper)

- **Nguyên lý:** Tích lũy âm thanh $\rightarrow$ Detect silence via energy $\rightarrow$ Xử lý 1 cục $\rightarrow$ Trả kết quả.
- **Logic Flow:**
  1.  Nhận Audio Chunk từ Queue.
  2.  **Energy-based VAD:** Tính RMS energy của audio samples.
  3.  **Buffer Accumulation:**
      - Nếu energy > `SILENCE_THRESHOLD` (0.0005): Append chunk vào buffer.
      - Nếu energy thấp (silence detected): Coi như hết câu (`is_final`).
  4.  **Trigger Inference:**
      - Nếu `buffer` > `MIN_DURATION` (3s) hoặc gặp silence: Đẩy `buffer` vào model `faster-whisper`.
      - Nếu `buffer` > `MAX_DURATION` (15s): Force transcribe.
  5.  **Post-process:** Trả text về Client với flag `is_final`.

---

### 2\. Audio Pipeline Solution (Giải pháp đường ống âm thanh)

#### A. Frontend Pre-processing (Tại Client)

Giảm tải cho Server bằng cách xử lý sơ bộ tại nguồn.

- **AudioWorklet:** Sử dụng Worklet Node để chặn luồng audio `float32` từ microphone.
- **Downsampling:** Thực hiện thuật toán Decimation đơn giản để hạ sample rate từ 44.1/48kHz xuống **16kHz**.
- **Format Conversion:** Convert `Float32` (-1.0 đến 1.0) sang `Int16` PCM (đây là định dạng chuẩn nhất để gửi qua socket, tiết kiệm 50% băng thông so với Float32).

#### B. Protocol Standardization (Giao thức)

Sử dụng giao thức WebSocket với 2 loại bản tin:

1.  **Config Message (JSON - Gửi lần đầu):**
    ```json
    { "type": "config", "model": "zipformer", "sample_rate": 16000 }
    ```
2.  **Data Message (Binary):** Raw PCM bytes (không bọc JSON, không Base64).

---

### 3\. Latency Optimization Techniques (Kỹ thuật giảm trễ)

Để đảm bảo phản hồi \< 1.5s, áp dụng các kỹ thuật sau:

1.  **Multiprocessing Queue:**

    - Thay vì dùng `threading` (bị giới hạn bởi Python GIL), sử dụng `torch.multiprocessing`. Mỗi Model Worker là một Process hệ điều hành riêng biệt.
    - Giao tiếp giữa WebSocket Process và AI Process qua `multiprocessing.Queue`.

2.  **Energy-based VAD (Bộ lọc khoảng lặng):**

    - Không bao giờ gửi khoảng lặng vào model Whisper (tốn tài nguyên vô ích).
    - Sử dụng **energy-based detection** thay vì Silero VAD để giảm overhead.
    - Logic: Tính RMS của samples, so sánh với `SILENCE_THRESHOLD = 0.0005`.

3.  **Keep-Alive Models:**

    - Model Zipformer load rất nhanh, nhưng Whisper/PhoWhisper mất 2-5s để load vào RAM.
    - **Solution:** Khi khởi động server, load sẵn Zipformer (thường trực). Whisper/PhoWhisper load theo cơ chế Lazy Loading (load khi có request đầu tiên) và giữ trong RAM khoảng 5 phút (TTL) nếu không ai dùng mới giải phóng.

---

### 4\. Client-Side Rendering Logic (Giải pháp hiển thị FE)

Để trải nghiệm người dùng mượt mà dù backend xử lý khác nhau:

- **Text Buffer Management:** Frontend duy trì một mảng `transcript_segments`.
- **Handling Updates:**
  - Nếu nhận `is_final: false` $\rightarrow$ Cập nhật phần tử cuối cùng của mảng (hiệu ứng text đang nhảy).
  - Nếu nhận `is_final: true` $\rightarrow$ Chốt phần tử cuối, tạo phần tử rỗng mới để chờ câu tiếp theo.
- **Visual Feedback:** Hiển thị text đang nhận diện (interim) bằng màu xám, text đã chốt (final) bằng màu đen.

---
