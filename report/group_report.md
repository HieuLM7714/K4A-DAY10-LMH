# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | L3A         |
| Tên nhóm         | LMH |
| Repository         | https://github.com/HieuLM7714/K4A-DAY10-LMH |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lê Minh Hiếu | 2A202602848 | Pipeline Lead | Các module: `crossref.py`, `cleaning.py`, `quality.py`, `testset.py`, `corruption.py`, `phase1.py`, `corruption_flow.py` |

---

## 2. Tóm tắt kết quả

Học viên đã hoàn thành độc lập 100% các tiêu chí kỹ thuật của bài thực hành Day 10 theo đúng chuẩn thiết kế MLOps và Data Observability cho hệ thống RAG:

1. **Baseline Pipeline (Phase 1):** Xây dựng thành công quy trình thu thập metadata từ Crossref API (hỗ trợ cơ chế tự động Fallback đọc snapshot local khi mất mạng/429), làm sạch dữ liệu và tạo trường ngữ cảnh `text_for_embedding`. Dựng chốt kiểm định **Great Expectations 1.x** (chuẩn Ephemeral Context với 4 Expectations thiết yếu) và giám sát **Freshness SLA (<25% stale)**. Toàn bộ 24 bài báo vượt qua Quality Gate (`success=True`), được nhúng bằng mô hình `all-MiniLM-L6-v2` và lưu vào ChromaDB collection `papers-baseline`. Kết quả Benchmark đạt **Hit Rate 100.0%** và **Token F1 1.0000**.
2. **Data Corruption & Silent Failure (Phase 2):** Giả lập 6 dạng lỗi thực tế (bỏ rơi bản ghi mới, xóa rỗng tóm tắt, chèn ký tự nhiễu rác, cắt ngắn tiêu đề, làm cũ ngày tháng, nhân bản bản ghi). Data Quality Gate ngay lập tức báo động đỏ (`GX=FAIL`, `Freshness=VIOLATION`). Đồng thời, mô hình RAG bị suy giảm hiệu năng nghiêm trọng: Hit Rate rơi xuống **60.0%** và Token F1 giảm xuống **0.6741**, minh chứng rõ nét cho hiện tượng **Silent Failure** khi không có runtime exception nào phát sinh nhưng AI trả lời sai sự thật.
3. **Idempotent Self-Healing (Phase 3):** Kích hoạt cơ chế tự phục hồi an toàn từ nguồn dữ liệu thô ban đầu `data/raw/crossref_records.json` (bảo toàn Data Lineage). Kết quả sau phục hồi lấy lại trọn vẹn 100% phong độ ban đầu (**Hit Rate 100.0%**, **Token F1 1.0000**, **GX=PASS**), chứng minh tính Idempotent tuyệt đối của pipeline.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref API (hoặc Snapshot Local data/raw/crossref_response.json)
    ├── 1. Ingestion & Raw Preservation -> data/raw/crossref_records.json
    ├── 2. Cleaning & Feature Modeling  -> data/clean/papers_clean.csv (text_for_embedding, age_days)
    ├── 3. Data Observability Gate      -> Great Expectations 1.x + Freshness SLA
    ├── 4. Vector Store Indexing        -> ChromaDB collection 'papers-baseline'
    ├── 5. Evaluation & Benchmarking    -> data/eval/test_set.json -> baseline_metrics.json
    ├── 6. Synthetic Data Corruption    -> 6 kịch bản lỗi -> corruption_log.json
    ├── 7. Re-index & Re-evaluate       -> ChromaDB 'papers-corrupted' -> corrupted_metrics.json
    └── 8. Idempotent Repair & Audit    -> Tái tạo từ Raw -> ChromaDB 'papers-repaired' -> corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / raw JSON | Fetch, retry/backoff, sanitize JATS XML, parse `PaperRecord` | `data/raw/crossref_records.json` | Lê Minh Hiếu |
| Cleaning          | `PaperRecord` list | Khử trùng lặp, tính `age_days`, tạo `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Lê Minh Hiếu |
| Embedding/index   | Clean DataFrame | SentenceTransformers `all-MiniLM-L6-v2`, ChromaDB PersistentClient | `data/chroma/`, `data/embeddings/` | Lê Minh Hiếu |
| Evaluation        | Clean DataFrame & Index | Sinh 10 câu hỏi đa dạng (4 nhóm), đo Hit Rate, F1, Judge | `data/eval/test_set.json`, `data/results/` | Lê Minh Hiếu |
| Observability     | Clean & Corrupted DataFrame | Ephemeral GX 1.x suite (4 expectations), Freshness SLA check | `data/quality/*.json`, `freshness_report.json` | Lê Minh Hiếu |
| Corruption/repair | Clean DataFrame & Raw records | Tiêm 6 dạng lỗi, log mutation; Re-build clean từ raw snapshot | `data/results/corruption_log.json`, `papers_clean_repaired.csv` | Lê Minh Hiếu |
| Orchestration     | Toàn bộ modules | Điều phối `run_phase1.py` và `run_corruption_flow.py` | `phase1_report.md`, `corruption_report.md` | Lê Minh Hiếu |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hoặc `mock`) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 records |
| Retrieval `top_k`          | 4 |
| Freshness threshold          | 180 ngày (SLA vi phạm nếu > 25% stale) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy thực nghiệm

```bash
# 1. Chạy Pha 1 (Baseline Pipeline):
python script/run_phase1.py

# 2. Chạy Pha 2 (Corruption -> Repair -> Comparison):
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | :---: | :---: | :--- |
| Baseline pipeline | **Thành công (100%)** | 2026-09-25 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | **Thành công (100%)** | 2026-09-25 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API công khai (`https://api.crossref.org/works`) |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:...,has-abstract:true` |
| Cơ chế retry/backoff      | Exponential backoff khi gặp mã `429 Too Many Requests` hoặc `503` |
| Fallback an toàn          | Tự động nạp từ `data/raw/crossref_response.json` khi offline |
| Số lượng records          | 24 records |

### Quy tắc cleaning và Data Modeling

1. **Khử thẻ XML/HTML:** Loại bỏ hoàn toàn các thẻ `<jats:p>`, `</jats:p>` và ký tự điều khiển trong phần tóm tắt (`summary`).
2. **Khử trùng lặp:** Dùng trường duy nhất `paper_id` (DOI) làm unique key để loại bỏ mọi bản ghi trùng.
3. **Tính `age_days`:** `(run_date.date() - published_date).days` để đo lường độ tuổi bản ghi phục vụ Freshness SLA.
4. **Cấu trúc `text_for_embedding`:**
   ```text
   Title: <Tiêu đề bài báo>
   Authors: <Danh sách tác giả>
   Published: <Ngày xuất bản>
   Categories: <Lĩnh vực chuyên môn>
   Summary: <Tóm tắt nội dung>
   ```

---

## 6. Evaluation Setup

- **Quy mô test set:** 10 câu hỏi cố định, phân bổ qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`).
- **Nguyên tắc đối chứng:** Cùng một file `data/eval/test_set.json` được sử dụng xuyên suốt qua cả 3 trạng thái (Baseline, Corrupted, Repaired) để đảm bảo tính khách quan và nhất quán khoa học.
- **Chỉ số đo lường:**
  - `retrieval_hit_rate`: Tỉ lệ tìm trúng tài liệu chứa câu trả lời chuẩn trong top_k.
  - `mean_token_f1`: Độ trùng khớp từ vựng giữa câu trả lời của AI và Ground Truth.
  - `judge_accuracy`: Đánh giá tính đúng đắn ngữ nghĩa.

---

## 7. Kết quả Baseline

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     **100.0%** | Toàn bộ 10/10 câu hỏi truy vấn trúng tài liệu đích |
| `mean_token_f1`      |     **1.0000** | Độ trùng khớp hoàn hảo so với Ground Truth |
| `judge_accuracy`     |     **100.0%** | Câu trả lời đạt độ chính xác nghiệp vụ tuyệt đối |
| `mean_judge_score`   |   **5.00 / 5.0** | Đạt điểm tối đa theo thẩm định chất lượng |

---

## 8. Data Quality và Freshness SLA

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | :---: | :--- |
| Row Count Between | Completeness | 5 đến 5000 dòng | **PASS (24 rows)** | `data/quality/baseline_quality_report.json` |
| Values Not Null | Validity | `paper_id`, `title`, `text_for_embedding` not null | **PASS** | `data/quality/baseline_quality_report.json` |
| Values Unique | Uniqueness | `paper_id` là khóa duy nhất | **PASS (100% unique)** | `data/quality/baseline_quality_report.json` |
| Summary Length | Completeness | Chiều dài `summary` >= 30 ký tự | **PASS** | `data/quality/baseline_quality_report.json` |
| Freshness SLA | Timeliness | Tỉ lệ bài báo quá hạn (>180 ngày) <= 25% | **PASS (4.2% stale)** | `data/quality/freshness_report.json` |

---

## 9. Corruption Scenarios và Phục Hồi Idempotent

| Corruption Scenario | Cách tạo lỗi | Số bản ghi ảnh hưởng | Quality Signal kỳ vọng | Tác động thực tế đến RAG |
| :--- | :--- | :---: | :--- | :--- |
| **1. Drop latest records** | Bỏ 20% các bài mới nhất | 4 bài | Row count giảm | Mất dữ liệu tươi, không tìm thấy bài mới |
| **2. Blank summary** | Xóa rỗng trường tóm tắt | 2 bài | GX Length < 30 FAIL | Mất ngữ cảnh, suy giảm câu trả lời summary |
| **3. Inject noise** | Chèn chuỗi rác vô nghĩa | 3 bài | Nhiễu embedding | Điểm tương đồng giảm, làm loãng kết quả |
| **4. Truncate title** | Cắt ngắn tiêu đề < 8 ký tự | 2 bài | Tiêu đề bị biến dạng | Không tìm được bài qua exact title lookup |
| **5. Stale date** | Lùi ngày xuất bản về 365 ngày | 8 bài | Freshness SLA FAIL (>30%) | Cảnh báo dữ liệu bị mốc meo |
| **6. Duplicate rows** | Nhân đôi bản ghi | 2 bài | GX Uniqueness FAIL | Ô nhiễm Vector Store, loãng ranking |

**Cơ chế Idempotent Repair:**  
Hệ thống không che giấu lỗi bằng cách sửa tay trên file lỗi, mà thực hiện **re-run pipeline từ nguồn thô ban đầu** (`data/raw/crossref_records.json`). Nhờ đó, dù chạy lại bao nhiêu lần, dữ liệu luôn phục hồi về đúng 24 bản ghi sạch ban đầu và loại bỏ hoàn toàn các bản ghi rác.

---

## 10. Bảng đối chiếu định lượng 3 trạng thái

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Thay đổi do corruption | Mức phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tổng số bản ghi** | 24 | 22 | 24 | -2 bản ghi | 100% |
| **Great Expectations Gate** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** | Bị chặn đứng | Phục hồi hoàn toàn |
| **Freshness SLA (<25% stale)** | ✅ **FRESH** (4.2%) | ❌ **VIOLATION** (36.4%) | ✅ **FRESH** (4.2%) | Vi phạm SLA | Trở lại ngưỡng an toàn |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | **Sụt giảm 40.0%** | **Phục hồi về 100.0%** |
| **Mean Token F1** | **1.0000** | **0.6741** | **1.0000** | **Sụt giảm 0.3259** | **Phục hồi về 1.0000** |
| **LLM Judge Accuracy** | **100.0%** | **70.0%** | **100.0%** | **Sụt giảm 30.0%** | **Phục hồi về 100.0%** |
| **Mean Judge Score** | **5.00 / 5.0** | **3.60 / 5.0** | **5.00 / 5.0** | **Giảm 1.40 điểm** | **Phục hồi 5.00 / 5.0** |

**Kết luận nhân quả cốt lõi:**
1. *Dữ liệu bẩn $\rightarrow$ Silent Failure:* Khi dữ liệu bị nhiễm bẩn, phần mềm không hề báo exception, nhưng chất lượng truy xuất sụt giảm nghiêm trọng từ 100% xuống 60%. Nếu không có Great Expectations và Freshness SLA, hệ thống sẽ đưa thông tin sai lệch đến người dùng mà không ai hay biết.
2. *Idempotent Repair $\rightarrow$ Khôi phục toàn diện:* Khi chốt kiểm dịch phát hiện lỗi và kích hoạt tái tạo lại từ Raw snapshot, 100% các chỉ số chất lượng dữ liệu và chất lượng câu trả lời của AI phục hồi nguyên vẹn về mức Baseline ban đầu.

---

## 11. Checklist kiểm tra trước khi nộp bài

- [x] Thông tin nhóm và repository chính xác (`HieuLM7714/K4A-DAY10-LMH`).
- [x] Phân công vai trò khớp với deliverables thực tế trong `docs/TEAM.md`.
- [x] Cả 2 lệnh `run_phase1.py` và `run_corruption_flow.py` đều chạy thành công với Exit code 0.
- [x] Toàn bộ file kết quả trong `data/results/` và `data/reports/` đều được sinh ra từ pipeline thực tế.
- [x] Bảng ma trận so sánh 3 trạng thái hiển thị đầy đủ, số liệu khớp chính xác giữa metrics JSON và báo cáo Markdown.
- [x] Tuyệt đối không commit file `.env` hoặc API Key bí mật lên GitHub (`.gitignore` đã bảo vệ).
