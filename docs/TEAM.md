# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `LMH`
- **Mã Nhóm / Lớp:** `L3A`
- **Tên Repository Nộp Bài:** `K4A-DAY10-LMH`

---

## 1. Danh sách thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Lê Minh Hiếu | 2A202602848 | minhhieule1171@gmail.com | Pipeline Lead | [2A202602848_LeMinhHieu.md](../report/2A202602848_LeMinhHieu.md) |

---

## 2. Phần tự khai báo đóng góp cá nhân

### Lê Minh Hiếu - 2A202602848
- **Vai trò:** Pipeline Lead
- **Công việc chi tiết đã hoàn thành:**
  - **Pipeline Lead & Integrator:** Thiết lập cấu hình hệ thống `core/config.py`, kết nối toàn bộ luồng `phase1.py` và `corruption_flow.py`, quản lý toàn bộ data lineage.
  - **Data Foundation & Recovery:** Xây dựng module thu thập Crossref API với cơ chế offline fallback trong `crossref.py`, chuẩn hóa dữ liệu và trường `text_for_embedding` trong `cleaning.py`, thiết kế cơ chế Idempotent Repair phục hồi 100% từ raw snapshot.
  - **RAG & Vector Database:** Quản lý mô hình embedding `all-MiniLM-L6-v2`, nạp 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`), xây dựng QA Agent.
  - **Observability & Evaluation:** Triển khai Great Expectations 1.x theo chuẩn Ephemeral Context với 4 expectations bắt buộc, thiết lập Freshness SLA (<25% stale), tạo bộ đề thi 10 câu hỏi chuẩn hóa trong `testset.py` và sinh báo cáo đối chiếu 3 trạng thái `corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Data Observability cho hệ thống RAG thực chiến, phát hiện và ngăn chặn triệt để hiện tượng Silent Failure.
  - Thiết kế và kiểm chứng thành công cơ chế Idempotent Self-Healing đảm bảo tính toàn vẹn dữ liệu trong môi trường sản xuất.
