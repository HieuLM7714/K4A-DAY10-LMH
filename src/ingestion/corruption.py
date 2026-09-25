from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Inject 6 realistic data corruptions into a clean DataFrame."""
    corrupted = df.copy()
    total_initial = len(corrupted)
    log_entries: dict[str, Any] = {
        "timestamp": now_utc().isoformat(),
        "total_initial_records": total_initial,
        "corruptions": {},
    }

    # 1. Drop latest records (simulate missing fresh ingestion, drop 20%)
    drop_count = max(1, int(total_initial * 0.20))
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)
    log_entries["corruptions"]["drop_latest"] = {
        "count": drop_count,
        "dropped_paper_ids": dropped_ids,
    }

    # 2. Blank summary (simulate crawler empty text error on 2 records)
    blank_targets = min(2, len(corrupted))
    blank_ids = []
    for i in range(blank_targets):
        corrupted.loc[i, "summary"] = ""
        blank_ids.append(corrupted.loc[i, "paper_id"])
    log_entries["corruptions"]["blank_summary"] = {
        "count": blank_targets,
        "affected_paper_ids": blank_ids,
    }

    # 3. Inject noise into summary (simulate encoding corruption)
    noise_targets = min(3, len(corrupted))
    noise_ids = []
    for i in range(noise_targets):
        idx = (i + 2) % len(corrupted)
        noise_str = " [CORRUPTED_NOISE_%%%$$$### MALFORMED_TOKEN_STREAM]"
        corrupted.loc[idx, "summary"] = str(corrupted.loc[idx, "summary"]) + noise_str
        noise_ids.append(corrupted.loc[idx, "paper_id"])
    log_entries["corruptions"]["inject_noise"] = {
        "count": noise_targets,
        "affected_paper_ids": noise_ids,
    }

    # 4. Truncate title (< 8 characters, simulate title parsing truncation)
    trunc_targets = min(2, len(corrupted))
    trunc_ids = []
    for i in range(trunc_targets):
        idx = (i + 4) % len(corrupted)
        corrupted.loc[idx, "title"] = "AI" if i == 0 else "Paper"
        trunc_ids.append(corrupted.loc[idx, "paper_id"])
    log_entries["corruptions"]["truncate_title"] = {
        "count": trunc_targets,
        "affected_paper_ids": trunc_ids,
    }

    # 5. Stale date (shift published date back by 365 days on 40% of rows to breach Freshness SLA)
    stale_count = max(2, int(len(corrupted) * 0.40))
    stale_ids = []
    for i in range(stale_count):
        idx = len(corrupted) - 1 - i
        curr_pub = str(corrupted.loc[idx, "published"])
        try:
            old_dt = datetime.fromisoformat(curr_pub) - timedelta(days=365)
            corrupted.loc[idx, "published"] = old_dt.strftime("%Y-%m-%d")
            corrupted.loc[idx, "age_days"] = int(corrupted.loc[idx, "age_days"]) + 365
            stale_ids.append(corrupted.loc[idx, "paper_id"])
        except Exception:
            pass
    log_entries["corruptions"]["stale_date"] = {
        "count": len(stale_ids),
        "affected_paper_ids": stale_ids,
    }

    # 6. Duplicate rows (duplicate 2 rows to break uniqueness)
    dup_count = min(2, len(corrupted))
    dup_rows = corrupted.iloc[:dup_count].copy()
    dup_ids = dup_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries["corruptions"]["duplicate_rows"] = {
        "count": dup_count,
        "duplicated_paper_ids": dup_ids,
    }

    # 7. Rebuild text_for_embedding and summary_chars
    for idx, row in corrupted.iterrows():
        title = str(row["title"])
        authors = str(row["authors_joined"])
        pub = str(row["published"])
        cats = str(row["categories_joined"])
        summary = str(row["summary"])
        corrupted.loc[idx, "summary_chars"] = len(summary)
        corrupted.loc[idx, "text_for_embedding"] = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Published: {pub}\n"
            f"Categories: {cats}\n"
            f"Summary: {summary}"
        )

    log_entries["final_record_count"] = len(corrupted)
    write_json(Path(output_log_path), log_entries)
    return corrupted

