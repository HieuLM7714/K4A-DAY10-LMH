from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build a deterministic evaluation test set across 4 business question types."""
    if len(df) < 4:
        raise ValueError("DataFrame must contain at least 4 papers to build a test set.")

    # 10 questions across 4 distinct question types
    question_sequence = [
        ("summary", "What is the summary of the paper '{title}'?"),
        ("authors", "Who authored the paper '{title}'?"),
        ("date", "When was the paper '{title}' published?"),
        ("categories", "What categories does the paper '{title}' belong to?"),
        ("summary", "What is the summary of the paper '{title}'?"),
        ("authors", "Who authored the paper '{title}'?"),
        ("date", "When was the paper '{title}' published?"),
        ("categories", "What categories does the paper '{title}' belong to?"),
        ("summary", "What is the summary of the paper '{title}'?"),
        ("authors", "Who authored the paper '{title}'?"),
    ]

    records = df.to_dict(orient="records")
    total_records = len(records)
    test_set: list[dict[str, Any]] = []

    for index, (q_type, template) in enumerate(question_sequence):
        row = records[index % total_records]
        title = row["title"]
        paper_id = row["paper_id"]
        question = template.format(title=title)

        if q_type == "summary":
            ground_truth = first_sentence(row["summary"])
        elif q_type == "authors":
            ground_truth = row["authors_joined"]
        elif q_type == "date":
            ground_truth = str(row["published"])
        elif q_type == "categories":
            ground_truth = row["categories_joined"]
        else:
            ground_truth = first_sentence(row["summary"])

        test_set.append(
            {
                "id": f"eval_{index + 1:03d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_set)
    return test_set
