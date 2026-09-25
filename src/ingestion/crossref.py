from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        paper_id = item.get("DOI", "").strip()
        if not paper_id:
            continue
        title_list = item.get("title", [])
        title = normalize_whitespace(title_list[0]) if title_list else ""
        raw_abstract = item.get("abstract", "")
        summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", raw_abstract))
        authors: list[str] = []
        for a in item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            full = normalize_whitespace(f"{given} {family}").strip()
            if full:
                authors.append(full)
        categories = [normalize_whitespace(c) for c in item.get("subject", []) if c]
        primary_category = categories[0] if categories else "Uncategorized"

        pub_dict = item.get("published", {})
        date_parts = pub_dict.get("date-parts", [[]])[0] if pub_dict.get("date-parts") else []
        if date_parts and len(date_parts) >= 1:
            year = int(date_parts[0])
            month = int(date_parts[1]) if len(date_parts) > 1 else 1
            day = int(date_parts[2]) if len(date_parts) > 2 else 1
            published_str = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            published_str = (item.get("created", {}).get("date-time", "")[:10]) or "2026-01-01"

        updated_str = published_str
        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published_str,
                updated=updated_str,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source API with offline fallback and persist raw records."""
    payload = None
    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "Day10DataPipeline/1.0 (mailto:student@vinuni.edu.vn)"}
            for attempt in range(3):
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.status_code == 200:
                    payload = resp.json()
                    write_json(settings.paths.raw_api_response, payload)
                    break
                if resp.status_code in {429, 503}:
                    time.sleep(2 ** attempt)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(f"Neither API nor snapshot available at {settings.paths.raw_api_response}")

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into PaperRecord instances."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
