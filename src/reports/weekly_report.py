from datetime import date
from pathlib import Path
from typing import Iterable

from src.filters.relevance_filter import is_xos_production_scope


def generate_weekly_report(rows: Iterable, output_dir: str, report_date: date) -> Path:
    year, week, _ = report_date.isocalendar()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{year}-{week:02d}.md"
    rows = [row for row in rows if row["relevance_score"] >= 3 and is_xos_production_scope(dict(row))]

    lines = [
        f"# Weekly Paper Report - {year}-W{week:02d}",
        "",
        f"Relevant papers this week: {len(rows)}",
        "",
    ]
    if not rows:
        lines.append("No relevant papers were recorded this week.")
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {index}. {row['title']}",
                "",
                f"- Journal: {row['journal'] or 'Unknown'}",
                f"- DOI: {row['doi'] or 'Unknown'}",
                f"- Relevance: {row['relevance_score']}/5",
                f"- Reason: {row['reason_for_relevance'] or 'Not recorded'}",
                f"- Data worth extracting: {row['data_worth_extracting'] or 'Not recorded'}",
                f"- PDF downloaded: {'yes' if row['pdf_downloaded'] else 'no'}",
                f"- URL: {row['url'] or 'Unknown'}",
                "",
                row["summary_zh"] or row["summary_en"] or "No summary.",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
