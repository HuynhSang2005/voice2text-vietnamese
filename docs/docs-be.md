# DOCS-BE: Kiến trúc & Triển khai Backend

### 1. Tư duy thiết kế (Design Philosophy)

Backend này hoạt động như một **"Tổng đài phân phối"**.

- **Main Process (FastAPI):** Chỉ lo việc nghe điện thoại (WebSocket) và ghi chép sổ sách (Database).
- **Worker Processes (AI):** Là các nhân viên chuyên môn ngồi trong phòng kín. Khi Main Process nhận audio, nó ném qua lỗ thông gió (Queue) vào phòng kín. Nhân viên xử lý xong ném giấy kết quả ra ngoài.
- **Lợi ích:** Việc AI tính toán nặng nhọc không bao giờ làm tắc nghẽn việc nhận dữ liệu từ người dùng.

### 2. Cấu trúc thư mục (Project Structure)

Chúng ta chia code theo hướng "Modular" để dễ mở rộng:

```text
backend/
├── app/
│   ├── api/                # Endpoints (WebSocket & HTTP)
│   ├── core/               # Config, DB, Manager
│   ├── models/             # SQLModel Schemas
│   ├── workers/            # AI Logic (Zipformer, Whisper)
│   └── main.py             # Entry point
├── scripts/
│   └── setup_models.py     # [CRITICAL] Script tải model
├── models_storage/         # Nơi chứa file model .bin / .onnx
├── requirements.txt
└── .env
```

### 3. Cài đặt & Cơ sở dữ liệu (Setup & Database)

Xem chi tiết hướng dẫn cài đặt tại **[Hướng dẫn Cài đặt](setup.md)**.

Dùng **SQLModel** để định nghĩa bảng `transcriptions`.

- **Mục đích:** Lưu lại lịch sử để so sánh hiệu năng các model.
- **Lưu ý:** Cần bật chế độ `WAL` (Write-Ahead Logging) cho SQLite để tránh lỗi "Database is locked" khi ghi liên tục.

---
