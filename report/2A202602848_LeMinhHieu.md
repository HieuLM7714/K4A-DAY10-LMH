# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Minh Hiếu               |
| MSSV               | 2A202602848                |
| Khóa/Lớp         | L3A          |
| Tên nhóm         | LMH |
| Vai trò chính    | Pipeline Lead              |
| Repository         | https://github.com/HieuLM7714/K4A-DAY10-LMH |
| Ngày hoàn thành | 2026-09-25                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu (Solo Owner)

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Ingestion & Lineage** | `src/ingestion/crossref.py` | Crossref REST API / Snapshot local | `data/raw/crossref_records.json` | **Hoàn thành 100%** |
| **Cleaning & Modeling** | `src/ingestion/cleaning.py` | List `PaperRecord` thô | `data/clean/papers_clean.csv` | **Hoàn thành 100%** |
| **Observability (GX 1.x)** | `src/observability/quality.py` | DataFrame dữ liệu | `data/quality/*.json`, `freshness_report.json` | **Hoàn thành 100%** |
| **Vector Store Indexing** | `src/retrieval/index.py` | Cleaned DataFrame | ChromaDB collections (`baseline`, `corrupted`, `repaired`) | **Hoàn thành 100%** |
| **Benchmark Evaluation** | `src/evaluation/testset.py` | Cleaned DataFrame | `data/eval/test_set.json` (10 câu hỏi) | **Hoàn thành 100%** |
| **Data Corruption Suite** | `src/ingestion/corruption.py` | DataFrame sạch | 6 kịch bản lỗi, `corruption_log.json` | **Hoàn thành 100%** |
| **Idempotent Repair Flow** | `src/pipelines/corruption_flow.py` | Raw snapshot | `papers_clean_repaired.csv`, `corruption_report.md` | **Hoàn thành 100%** |

---

## 3. Giải thích phần kỹ thuật đã thực hiện

### 3.1. Thiết kế Ingestion và bảo toàn Raw Lineage
- Bóc tách payload JSON từ Crossref API thành danh sách các đối tượng `PaperRecord`.
- Loại bỏ toàn bộ các thẻ JATS XML rác (`<jats:p>`, `</jats:p>`) trong phần tóm tắt để tránh làm nhiễu không gian vector.
- Xây dựng cơ chế **Offline Fallback**: nếu API trả về mã lỗi `429 Too Many Requests` hoặc mạng chập chờn, hệ thống tự động nạp từ bản sao lưu `data/raw/crossref_response.json`, đảm bảo pipeline luôn hoạt động trơn tru.

### 3.2. Chuẩn hóa Schema và Tính toán Feature cho Vector Store
- Khử trùng lặp bản ghi theo khóa duy nhất `paper_id` (DOI).
- Tính toán trường `age_days = (run_date.date() - published_date).days` để giám sát độ tươi mới của tài liệu theo SLA.
- Ghép nối cấu trúc 5 thành phần hoàn chỉnh cho trường `text_for_embedding`:
  ```text
  Title: <Tiêu đề bài báo>
  Authors: <Danh sách tác giả>
  Published: <Ngày xuất bản>
  Categories: <Lĩnh vực chuyên môn>
  Summary: <Tóm tắt nội dung>
  ```

### 3.3. Xây dựng Data Quality Gate bằng Great Expectations 1.x
- Triển khai chuẩn **Ephemeral Context** mới nhất của GX 1.x (không tạo file cấu hình rác, thực thi cực nhanh trên RAM):
  ```python
  context = gx.get_context(mode="ephemeral")
  data_source = context.data_sources.add_pandas(name="papers_source")
  data_asset = data_source.add_dataframe_asset(name="papers_asset")
  batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
  batch = batch_def.get_batch(batch_parameters={"dataframe": df})
  ```
- Áp dụng 4 Expectations bắt buộc:
  1. `ExpectTableRowCountToBeBetween`: Số lượng dòng hợp lệ từ 5 đến 5000.
  2. `ExpectColumnValuesToNotBeNull`: Các trường `paper_id`, `title`, `text_for_embedding` không được phép null.
  3. `ExpectColumnValuesToBeUnique`: Đảm bảo `paper_id` là duy nhất 100%.
  4. `ExpectColumnValueLengthsToBeBetween`: Trường `summary` phải có độ dài tối thiểu 30 ký tự.
- Giám sát **Freshness SLA**: Báo động đỏ `is_fresh = False` khi tỉ lệ bài báo quá hạn (>180 ngày) vượt quá 25%.

### 3.4. Mô phỏng 6 kịch bản Data Corruption
- Giả lập 6 lỗi dữ liệu thực tế hay gặp trong sản xuất:
  1. *Drop latest:* Bỏ rơi 20% bài báo mới nhất (mô phỏng mất dữ liệu tươi).
  2. *Blank summary:* Xóa trắng tóm tắt ở 2 dòng (kích hoạt lỗi độ dài GX).
  3. *Inject noise:* Chèn chuỗi rác `[CORRUPTED_NOISE_%%%$$$###]` vào tóm tắt (mô phỏng lỗi encoding).
  4. *Truncate title:* Cắt ngắn tiêu đề < 8 ký tự (phá vỡ lookup tiêu đề).
  5. *Stale date:* Lùi ngày xuất bản 365 ngày (kích hoạt vi phạm Freshness SLA: 36.4% stale).
  6. *Duplicate rows:* Nhân đôi 2 dòng (kích hoạt lỗi Unique của GX).

---

## 4. Quyết định kỹ thuật quan trọng (Key Architectural Decisions)

1. **Sử dụng Ephemeral Context trong Great Expectations 1.x:**  
   *Bối cảnh:* GX 1.x hỗ trợ cả chế độ lưu trữ trên ổ đĩa (file-based) và chế độ tạm thời trên RAM (ephemeral mode).  
   *Quyết định:* Chọn chế độ `mode="ephemeral"` thông qua `gx.get_context(mode="ephemeral")`.  
   *Lý do:* Chế độ này không sinh ra các file cấu hình lộn xộn trong thư mục dự án, tránh xung đột đường dẫn trên máy Windows/Linux của ban giám khảo, đồng thời tối ưu hóa tốc độ thực thi khi kiểm định dữ liệu trong CI/CD pipeline.

2. **Thiết kế Idempotent Pipeline dựa trên Raw Snapshot:**  
   *Bối cảnh:* Khi dữ liệu bị nhiễm bẩn, nhiều kỹ sư có xu hướng viết hàm "vá lỗi" trực tiếp trên tập dữ liệu bẩn.  
   *Quyết định:* Thực hiện cơ chế khôi phục từ bản sao lưu thô ban đầu `data/raw/crossref_records.json` (bảo toàn Data Lineage).  
   *Lý do:* Đảm bảo tính Idempotent tuyệt đối — dù quá trình khôi phục được kích hoạt lại bao nhiêu lần, kết quả đầu ra luôn là 24 bản ghi sạch đồng nhất, không gây ra lỗi trùng lặp hay tích lũy dữ liệu rác.

---

## 5. Xử lý sự cố thực tế (Troubleshooting & Resolution)

- **Sự cố 1 — Mã hóa ký tự tiếng Việt trên Windows Console (CP1252 vs UTF-8):**  
  - *Triệu chứng:* Khi in chuỗi thông báo tiếng Việt có dấu, console Windows báo lỗi `UnicodeEncodeError: 'charmap' codec can't encode character`.  
  - *Nguyên nhân:* Mặc định PowerShell trên Windows sử dụng bảng mã ANSI/CP1252 cho stdout.  
  - *Cách xử lý:* Cấu hình `$env:PYTHONUTF8=1` trước khi chạy script Python để ép runtime sử dụng UTF-8 toàn diện. Kết quả: Toàn bộ console in trơn tru không lỗi font.
- **Sự cố 2 — Khởi tạo thư viện PyTorch trên Windows:**  
  - *Triệu chứng:* Khi import thư viện sentence-transformers xuất hiện lỗi nạp DLL `c10.dll`.  
  - *Cách xử lý:* Cài đặt phiên bản runtime PyTorch ổn định, tương thích với cấu hình CPU và môi trường Windows. Sau khi xử lý, mô hình `all-MiniLM-L6-v2` nạp và nhúng vector đạt tốc độ cao.

---

## 6. Phân tích kết quả thực nghiệm

| Chỉ số kỹ thuật | 1. Baseline (Sạch) | 2. Corrupted (Bẩn) | 3. Repaired (Phục hồi) | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **Tổng số bản ghi** | 24 | 22 | 24 | Khôi phục đúng số lượng ban đầu |
| **Great Expectations Gate** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** | Chặn đứng dữ liệu hỏng kịp thời |
| **Freshness SLA (<25% stale)** | ✅ **FRESH** (4.2%) | ❌ **VIOLATION** (36.4%) | ✅ **FRESH** (4.2%) | Khôi phục độ tươi mới của kho dữ liệu |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | Phục hồi 100% khả năng tìm kiếm |
| **Mean Token F1** | **1.0000** | **0.6741** | **1.0000** | Khắc phục sụt giảm nội dung trả lời |
| **LLM Judge Accuracy** | **100.0%** | **70.0%** | **100.0%** | Loại bỏ hiện tượng Hallucination |
| **Mean Judge Score (1-5)** | **5.00 / 5.0** | **3.60 / 5.0** | **5.00 / 5.0** | AI lấy lại phong độ xuất sắc |

---

## 7. Điều học được và Cam kết

1. **Hiểu sâu sắc về Silent Failure:** Trong các hệ thống AI Agent, lỗi dữ liệu nguy hiểm hơn lỗi phần mềm truyền thống vì hệ thống không báo lỗi đỏ, nhưng thông tin tư vấn cho người dùng hoàn toàn sai lệch.
2. **Tầm quan trọng của Data Observability:** Chốt kiểm dịch Great Expectations và giám sát Freshness SLA là lớp phòng thủ bắt buộc phải có trước khi dữ liệu được nạp vào Vector Store.
3. **Cam kết liêm chính:** Toàn bộ số liệu và kết quả trong báo cáo này đều được đo lường thực tế từ quá trình chạy pipeline `run_phase1.py` và `run_corruption_flow.py`, không chỉnh sửa hay làm đẹp số liệu thủ công.

**Xác nhận:**  
- **Họ và tên:** Lê Minh Hiếu  
- **Ngày hoàn thành:** 2026-09-25  
