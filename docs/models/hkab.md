# HKAB (Vietnamese RNN-T Tutorial)

## Tổng quan

**HKAB** là một dự án hướng dẫn và model mẫu về Vietnamese RNN-T. Trong dự án này, chúng ta sử dụng nó như một nguồn tham khảo hoặc một model thay thế tiềm năng cho Zipformer.

- **Source:** `https://github.com/HKAB/vietnamese-rnnt-tutorial`
- **Loại:** Source code & Model weights (cần training/export).

---

## Tích hợp vào Dự án

Hiện tại, script `setup_models.py` hỗ trợ việc clone source code của HKAB về thư mục `backend/models_storage/hkab`.

### Mục đích sử dụng

1.  **Tham khảo:** Xem cách implement RNN-T cho tiếng Việt.
2.  **Export ONNX:** Sử dụng các script trong repo này (hoặc script `export_hkab_onnx.py` cũ của chúng ta) để export model sang ONNX nếu muốn chạy với Sherpa.

### Cấu trúc

Sau khi chạy setup, source code sẽ nằm tại:

```text
backend/models_storage/hkab/
```

> **Lưu ý:** Mặc định hệ thống Voice2Text của chúng ta đang dùng **Zipformer** (của Hynt) vì nó đã được đóng gói sẵn ONNX và tối ưu tốt hơn. HKAB chủ yếu dành cho mục đích nghiên cứu và development.
