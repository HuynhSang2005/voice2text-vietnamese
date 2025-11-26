# Design System & Hướng dẫn UI/UX

## 1. Nguyên tắc cốt lõi (Core Principles)

- **Tối giản & Tập trung:** UI nên ưu tiên nội dung transcription.
- **Phản hồi thời gian thực:** Các tín hiệu trực quan cho đầu vào âm thanh, trạng thái kết nối và trạng thái xử lý.
- **Khả năng truy cập:** Độ tương phản cao, typography rõ ràng và hỗ trợ điều hướng bằng bàn phím.

## 2. Bảng màu (Color Palette - Zinc/Slate)

Chúng ta sử dụng theme `zinc` tiêu chuẩn của Shadcn để có cái nhìn trung tính, chuyên nghiệp.

- **Background:** `bg-background` (Trắng/Xám đậm)
- **Foreground:** `text-foreground` (Đen/Trắng)
- **Primary:** `bg-primary` (Đen/Trắng) cho các hành động chính.
- **Muted:** `text-muted-foreground` cho thông tin phụ (thời gian, độ trễ).
- **Accents:**
  - **Đang ghi âm:** `text-red-500` (Hiệu ứng Pulse)
  - **Đã kết nối:** `text-green-500`
  - **Đang xử lý:** `text-yellow-500`

## 3. Typography

- **Font:** Inter (Font mặc định của Shadcn).
- **Headings:** In đậm, tracking-tight.
- **Transcript:** Monospace hoặc Sans-serif sạch để dễ đọc.

## 4. Sử dụng Component (Shadcn UI)

### A. Bố cục (Layout)

- **Sidebar:** Điều hướng (Dashboard, Lịch sử, Cài đặt).
- **Nội dung chính:**
  - **Header:** Chọn Model, Badge trạng thái kết nối.
  - **Khu vực Transcript:** Vùng cuộn lớn hiển thị văn bản.
  - **Thanh điều khiển:** Cố định ở dưới cùng (Nút Mic, Chuyển đổi ngôn ngữ).

### B. Các Component cụ thể

- **Card:** Container cho Transcript và Thống kê.
- **ScrollArea:** Dùng cho văn bản transcription dài.
- **Badge:** Chỉ báo trạng thái (Online/Offline, Tên Model).
- **Select:** Chuyển đổi model.
- **Button:**
  - `default`: Bắt đầu/Dừng ghi âm.
  - `ghost`: Cài đặt, Lịch sử.
  - `destructive`: Xóa transcript.
- **Skeleton:** Trạng thái loading cho danh sách lịch sử.
- **Toast:** Thông báo lỗi (Mất kết nối, Lỗi API).

## 5. Các mẫu UI (UI Patterns)

### Real-time Transcription

- **Optimistic UI:** Hiển thị kết quả tạm thời ngay lập tức bằng màu xám (`text-muted-foreground`).
- **Kết quả cuối cùng:** Chuyển sang màu đen (`text-foreground`) khi đã xác nhận.
- **Tự động cuộn:** Giữ view ở dưới cùng khi đang ghi âm, nhưng tạm dừng nếu người dùng cuộn lên.

### Trực quan hóa âm thanh (Audio Visualization)

- Waveform đơn giản bằng CSS hoặc vòng tròn pulse quanh nút Mic để báo hiệu có hoạt động.

---

**Xem thêm:** [Tài liệu Frontend](docs-fe.md)
