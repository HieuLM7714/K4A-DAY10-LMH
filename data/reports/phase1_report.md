# Báo Cáo Nghiệm Thu Pha 1 — Baseline Data Pipeline & Observability

- **Thời điểm sinh báo cáo:** 2026-09-25T09:49:03.255536+00:00
- **Trạng thái tổng thể:** ✅ Baseline Pipeline hoàn thành chuẩn xác

---

## 1. Nguồn Dữ Liệu & Thống Kê Ingestion (Data Lineage)

| Thuộc tính | Giá trị ghi nhận |
| :--- | :--- |
| **Nguồn dữ liệu (Source API)** | Crossref REST API |
| **Truy vấn thu thập (Query)** | `agentic retrieval augmented generation large language model` |
| **Tổng số bản ghi thô (Raw Records)** | 24 |
| **Tổng số bản ghi sạch (Clean Records)** | 24 |
| **Mô hình Embedding** | `sentence-transformers/all-MiniLM-L6-v2` |
| **ChromaDB Collection** | `papers-baseline` |

---

## 2. Kiểm Định Chất Lượng Dữ Liệu (Great Expectations 1.x & Freshness SLA)

### 2.1. Great Expectations 1.x Gate: PASSED
- **Tổng số Expectations kiểm định:** 6
- **Số Expectations đạt (Success):** 6
- **Số Expectations vi phạm (Failed):** 0
- **Tỉ lệ vượt chuẩn:** 100.0%

### 2.2. Freshness SLA Monitoring: FRESH
- **Ngưỡng quá hạn SLA:** `180 ngày`
- **Số bản ghi quá hạn (Stale):** 1 / 24 (4.2%)
- **Bài báo mới nhất (Latest):** 2026-07-22
- **Bài báo cũ nhất (Oldest):** 2026-03-28
- **Tuổi trung bình (Mean Age):** 114.33 ngày

---

## 3. Hiệu Năng RAG Agent Trên Dữ Liệu Sạch (Baseline Benchmarks)

| Chỉ số đánh giá | Điểm số Baseline | Ý nghĩa kỹ thuật |
| :--- | :---: | :--- |
| **Số lượng mẫu kiểm thử (Samples)** | 10 | 10 câu hỏi bao phủ 4 nhóm nghiệp vụ |
| **Retrieval Hit Rate** | **100.0%** | Tỉ lệ tìm trúng tài liệu chứa đáp án chuẩn |
| **Mean Token F1** | **1.0000** | Độ trùng khớp câu từ so với Ground Truth |
| **LLM Judge Accuracy** | **100.0%** | Đánh giá ngữ nghĩa bởi LLM Judge |
| **Mean Judge Score (Thang 1-5)** | **5.00 / 5.0** | Điểm chất lượng trung bình của câu trả lời |

> **Ragas Evaluation:** Skipped (Set RUN_RAGAS=1 to enable the slower Ragas pass.)


---
*Báo cáo được sinh tự động bởi pipeline Phase 1.*
