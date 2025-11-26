# Tài liệu & Kiến trúc Frontend

## 1. Công nghệ sử dụng (Technology Stack)

Chúng tôi sử dụng một stack hiện đại, tối ưu hóa hiệu năng cho các ứng dụng thời gian thực.

> **Cài đặt:** Để xem hướng dẫn cài đặt, vui lòng tham khảo **[Hướng dẫn Cài đặt](setup.md)**.

### Core

- **Runtime:** [Bun](https://bun.sh) (Package Manager & Runtime)
- **Framework:** [React 19](https://react.dev) + [Vite](https://vitejs.dev)
- **Ngôn ngữ:** [TypeScript](https://www.typescriptlang.org) (Strict Mode)

### UI & Styling

- **Styling Engine:** [Tailwind CSS v4](https://tailwindcss.com)
- **Thư viện Component:** [Shadcn UI](https://ui.shadcn.com) (Radix Primitives + Tailwind)
- **Icons:** [Lucide React](https://lucide.dev)
- **Tiện ích:** `clsx`, `tailwind-merge`, `class-variance-authority` (CVA)

### Quản lý State & Data

- **Global State:** [Zustand](https://github.com/pmndrs/zustand) (Nhẹ, dùng cho trạng thái WebSocket & Audio stream)
- **Server State:** [TanStack Query](https://tanstack.com/query) (Dùng cho REST API fetching & caching)
- **Routing:** [TanStack Router](https://tanstack.com/router) (Type-safe routing)

### Real-time & Audio

- **WebSocket:** `react-use-websocket` (Quản lý kết nối mạnh mẽ)
- **Xử lý Audio:** Native **AudioWorklet API** (Không dùng thư viện nặng bên ngoài)
- **API Client:** `@hey-api/client-fetch` (Tự động generate từ OpenAPI)

---

## 2. Cấu trúc dự án (Project Structure)

Chúng tôi tuân theo cấu trúc **Feature-based** hoặc **Domain-driven** để đảm bảo khả năng mở rộng.

```
frontend/
├── public/
│   └── pcm-processor.js      # [CRITICAL] AudioWorklet processor
├── src/
│   ├── client/               # Auto-generated API client (Không sửa thủ công)
│   ├── components/
│   │   ├── ui/               # Shadcn UI primitives (Button, Card, etc.)
│   │   └── common/           # Shared components (Header, Footer, Layout)
│   ├── features/             # Feature-specific modules
│   │   ├── dashboard/        # Tính năng Dashboard
│   │   │   ├── components/   # Component riêng của Dashboard
│   │   │   ├── hooks/        # Logic của Dashboard
│   │   │   └── types/        # Types riêng của feature
│   │   └── history/          # Tính năng Lịch sử Transcription
│   ├── hooks/                # Global custom hooks (useAudioRecorder, useSocket)
│   ├── lib/                  # Tiện ích (utils.ts, constants)
│   ├── routes/               # Định nghĩa TanStack Router
│   ├── store/                # Zustand stores (useAppStore)
│   ├── styles/               # Global styles
│   ├── App.tsx
│   └── main.tsx
├── components.json           # Cấu hình Shadcn
├── vite.config.ts
└── tsconfig.json
```

---

## 3. Tiêu chuẩn Code & Best Practices

### A. Clean Code & React

1.  **Tách biệt Logic:** Di chuyển logic phức tạp (effects, biến đổi state) vào **Custom Hooks**. Component chỉ nên tập trung vào việc render.
2.  **Functional Components:** Sử dụng hoàn toàn functional components với TypeScript interfaces cho props.
3.  **Strict Typing:** Không dùng `any`. Định nghĩa interface cho mọi cấu trúc dữ liệu. Dùng `zod` để validate nếu cần.
4.  **Early Returns:** Sử dụng guard clauses để tránh lồng nhau quá sâu (deep nesting).

### B. Sử dụng Shadcn UI

1.  **CN Utility:** Luôn sử dụng hàm `cn()` (clsx + tailwind-merge) khi áp dụng class có điều kiện hoặc cho phép ghi đè class.
    ```tsx
    <div className={cn("bg-red-500", className)}>...</div>
    ```
2.  **Composition:** Xây dựng UI phức tạp bằng cách kết hợp các Shadcn primitives nhỏ (Card, Dialog, ScrollArea).

### C. Mô hình Real-time WebSocket

1.  **Single Connection:** Duy trì một kết nối WebSocket duy nhất trong global context hoặc Zustand store (hoặc top-level hook).
2.  **Event Driven:** Sử dụng `useEffect` để lắng nghe `lastMessage` từ `react-use-websocket` và dispatch action vào store.
3.  **Binary Frames:** Gửi dữ liệu audio dưới dạng `ArrayBuffer` (Int16 PCM). Nhận kết quả transcription dưới dạng JSON text.

---

## 4. Triển khai Audio Pipeline

Để đạt độ trễ < 1.5s, chúng tôi bỏ qua các wrapper cấp cao và sử dụng API cấp thấp của trình duyệt.

### Quy trình (The Pipeline)

1.  **GetUserMedia:** Yêu cầu quyền truy cập microphone (`audio/webm` hoặc raw PCM).
2.  **AudioContext:** Tạo `AudioContext` với `sampleRate: 16000` (nếu hỗ trợ) hoặc downsample thủ công.
3.  **AudioWorklet:**
    - Load `pcm-processor.js`.
    - Processor nhận `Float32Array` audio buffers.
    - **Downsampling (nếu cần):** Nội suy tuyến tính về 16kHz.
    - **Chuyển đổi:** Chuyển `Float32` (-1.0 đến 1.0) sang `Int16` (-32768 đến 32767).
    - **Gửi tin:** Gửi các chunk `Int16Array` về main thread qua `port.postMessage`.
4.  **WebSocket Transport:**
    - Main thread nhận các chunk PCM.
    - Buffer nhẹ (tùy chọn) hoặc gửi ngay lập tức qua WebSocket.

### Tại sao dùng AudioWorklet?

`ScriptProcessorNode` đã lỗi thời và chạy trên main thread (gây giật lag UI). `AudioWorklet` chạy trên một thread riêng biệt, đảm bảo thu âm mượt mà ngay cả khi UI đang xử lý nặng.

---

## 5. Tích hợp API

### REST API

- Sử dụng **TanStack Query** (`useQuery`, `useMutation`) cho mọi tương tác REST.
- Sử dụng client tự động generate từ `src/client`.
- **Ví dụ:**
  ```tsx
  const { data } = useQuery({
    queryKey: ["history"],
    queryFn: () => Client.getHistory(),
  });
  ```

### WebSocket API

- Endpoint: `/ws/transcribe`
- **Client -> Server:**
  - Config (JSON): `{"type": "config", "model": "zipformer"}`
  - Audio (Binary): Raw Int16 PCM bytes.
- **Server -> Client:**
  - Result (JSON): `{"text": "xin chào", "is_final": false}`

---

## 6. Tài liệu liên quan

- **[Hợp đồng API & Quy trình tích hợp](contract-api.md):** Hướng dẫn chi tiết về cách dùng Hey-API, generate clients, và đồng bộ Backend/Frontend.
- **[Design System & UI/UX](design-system.md):** Bảng màu, typography, và hướng dẫn sử dụng component Shadcn.
