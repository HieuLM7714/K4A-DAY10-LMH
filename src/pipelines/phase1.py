from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute the end-to-end baseline scholarly paper data pipeline (Phase 1)."""
    settings = load_settings()

    # 1. Ingestion: fetch or load raw records
    raw_records = fetch_source_records(settings)

    # 2. Cleaning & Feature Engineering
    df = build_clean_dataframe(raw_records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    # 3. Vector Store Indexing (ChromaDB)
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)

    # 4. Benchmark Test Set Generation
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)

    # 5. Baseline Evaluation
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 6. Observability: Great Expectations 1.x & Freshness SLA
    quality_report = run_data_quality_checks(df, settings, "baseline")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 7. Generate Phase 1 Markdown Report
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "raw_records_count": len(raw_records),
        "clean_records_count": len(df),
        "embedding_model": settings.embedding_model,
        "collection_name": settings.baseline_collection_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    # 8. Agent Demo (Graceful fallback)
    try:
        agent = build_agent(settings, index)
        demo_q = test_set[0]["question"] if test_set else "What are the latest findings?"
        demo_ans = run_agent_question(agent, demo_q)
        write_json(
            settings.paths.demo_answers,
            [{"question": demo_q, "answer": demo_ans}],
        )
    except Exception as exc:
        write_json(
            settings.paths.demo_answers,
            [{"status": "skipped", "reason": str(exc)}],
        )

    print("=== Baseline Phase 1 Pipeline Completed Successfully ===")
    print(f"Clean Records: {len(df)}")
    print(f"GX Quality Check Success: {quality_report.get('success')}")
    print(f"Retrieval Hit Rate: {eval_bundle.summary.get('retrieval_hit_rate', 0.0) * 100:.1f}%")
    print(f"Mean Token F1: {eval_bundle.summary.get('mean_token_f1', 0.0):.4f}")
    print(f"Report: {settings.paths.baseline_report}")

