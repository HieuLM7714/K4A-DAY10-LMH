from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into an embedding-ready and validation-ready DataFrame."""
    rows: list[dict[str, Any]] = []
    run_d = run_date.date() if hasattr(run_date, "date") else run_date

    for record in records:
        paper_id = record.paper_id.strip()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if a]
        categories = [normalize_whitespace(c) for c in record.categories if c]
        primary_category = record.primary_category or (categories[0] if categories else "Uncategorized")
        published = record.published.strip()
        updated = record.updated.strip() or published

        try:
            pub_date = datetime.fromisoformat(published).date()
        except Exception:
            pub_date = run_d

        age_days = max(0, (run_d - pub_date).days)
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df

