from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Great Expectations 1.x quality suite and persist result."""
    context = gx.get_context(mode="ephemeral")
    source_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"
    suite_name = f"papers_suite_{report_name}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=suite_name)
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)
    success = bool(validation_result.success)

    report = {
        "report_name": report_name,
        "success": success,
        "timestamp": now_utc().isoformat(),
        "statistics": {
            "evaluated_expectations": len(validation_result.results),
            "successful_expectations": sum(1 for r in validation_result.results if r.success),
            "unsuccessful_expectations": sum(1 for r in validation_result.results if not r.success),
            "success_percent": (
                (sum(1 for r in validation_result.results if r.success) / len(validation_result.results) * 100.0)
                if validation_result.results
                else 0.0
            ),
        },
        "results": [
            {
                "expectation_type": (
                    r.expectation_config.type
                    if hasattr(r.expectation_config, "type")
                    else str(type(r.expectation_config).__name__)
                ),
                "success": bool(r.success),
                "result": dict(r.result) if hasattr(r, "result") and isinstance(r.result, dict) else {},
            }
            for r in validation_result.results
        ],
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Compute dataset age statistics against the Freshness SLA."""
    total_rows = len(df)
    if total_rows == 0:
        payload = {
            "report_timestamp": now_utc().isoformat(),
            "threshold_days": settings.freshness_threshold_days,
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": False,
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "mean_age_days": 0.0,
        }
    else:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        stale_ratio = float(stale_rows / total_rows)
        is_fresh = stale_ratio <= 0.25
        latest_published = str(df["published"].max()) if "published" in df else "N/A"
        oldest_published = str(df["published"].min()) if "published" in df else "N/A"
        mean_age_days = float(df["age_days"].mean()) if "age_days" in df else 0.0

        payload = {
            "report_timestamp": now_utc().isoformat(),
            "threshold_days": settings.freshness_threshold_days,
            "total_rows": total_rows,
            "stale_rows": stale_rows,
            "stale_ratio": stale_ratio,
            "is_fresh": is_fresh,
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "mean_age_days": round(mean_age_days, 2),
        }

    write_json(Path(report_path), payload)
    return payload
