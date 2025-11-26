# DOCS-SOLUTIONS: Core Logic & System Algorithms

### 1\. Dual-Strategy Processing (Chiến lược xử lý kép)

Do tính chất khác biệt của 3 model, Backend sẽ áp dụng **Strategy Pattern** để tách biệt logic xử lý luồng âm thanh.

#### A. Strategy 1: True Streaming (Dành cho Zipformer)

- **Nguyên lý:** Input vào là Output ra ngay lập tức (Frame-in, Token-out).
- **Logic Flow:**
  1.  Nhận Audio Chunk (100-200ms) từ Queue.
  2.  Feed trực tiếp vào `sherpa-onnx` stream decoder.
  3.  Kiểm tra: Decoder có sinh ra token mới không?
  4.  Nếu có $\rightarrow$ Gửi ngay về Client.
  5.  Giữ nguyên Context (State) cho chunk tiếp theo.

#### B. Strategy 2: Buffered & VAD-Triggered (Dành cho Faster/PhoWhisper)

- **Nguyên lý:** Tích lũy âm thanh $\rightarrow$ Tìm điểm ngắt $\rightarrow$ Xử lý 1 cục $\rightarrow$ Trả kết quả.
- **Logic Flow:**
  1.  Nhận Audio Chunk từ Queue.
  2.  **VAD Check:** Chạy qua Silero VAD để xác định xác suất giọng nói.
  3.  **Buffer Accumulation:**
      - Nếu đang nói: Append chunk vào buffer tạm (`temp_buffer`).
      - Nếu khoảng lặng \> ngưỡng (vd: 500ms): Coi như hết câu (`is_final`).
  4.  **Trigger Inference:**
      - Nếu `buffer` \> 3s (hoặc gặp khoảng lặng): Đẩy `buffer` vào model `faster-whisper`.
  5.  **Post-process:** So sánh text mới với text cũ (overlap checking) để tránh lặp từ.
  6.  Gửi kết quả về Client (kèm flag `is_final=True` nếu gặp khoảng lặng).

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

2.  **VAD Filtering (Bộ lọc khoảng lặng):**

    - Không bao giờ gửi khoảng lặng vào model Whisper (tốn tài nguyên vô ích). Nếu VAD báo "Silence", worker bỏ qua chunk đó ngay lập tức.

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
