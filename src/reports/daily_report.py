import json
from datetime import date
from pathlib import Path
from typing import Iterable

def generate_daily_report(rows: Iterable, output_dir: str, report_date: date) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{report_date.isoformat()}.md"
    rows = [row for row in rows if row["relevance_score"] >= 3]

    lines = [
        f"# Daily Paper Report - {report_date.isoformat()}",
        "",
        f"Relevant papers: {len(rows)}",
        "",
        "> [!info] Relevance scale",
        "> 0 = unrelated; 1 = broad biomass valorization; 2 = method-related pretreatment/hydrolysis; 3 = directly related to hemicellulose extraction/XOS; 4 = high relevance with experimental/yield/HPLC/fraction data; 5 = directly reusable for experiments or dataset construction.",
        "",
    ]

    if not rows:
        lines.extend(["No relevant papers were found in today's RSS scan.", ""])
    for index, row in enumerate(rows, start=1):
        matched = _json_load(row["matched_keywords"], [])
        experimental = _json_load(row["experimental_info"], {})
        lines.extend(
            [
                f"## {index}. {row['title']}",
                "",
                f"- Journal: {row['journal'] or 'Unknown'}",
                f"- DOI: {row['doi'] or 'Unknown'}",
                f"- Published: {row['published_date'] or 'Unknown'}",
                f"- Relevance: {row['relevance_score']}/5",
                f"- Reason: {row['reason_for_relevance'] or 'Not recorded'}",
                f"- Data worth extracting: {row['data_worth_extracting'] or 'Not recorded'}",
                f"- Matched keywords: {', '.join(matched) if matched else 'None'}",
                f"- URL: {row['url'] or 'Unknown'}",
                f"- PDF URL: {row['pdf_url'] or 'Unknown'}",
                f"- PDF downloaded: {'yes' if row['pdf_downloaded'] else 'no'}",
                f"- Open access status: {row['open_access_status'] or 'unknown'}",
                f"- Processed time: {row['processed_time'] or 'Unknown'}",
                "",
                "### 中文摘要",
                row["summary_zh"] or "No summary.",
                "",
                "### English Summary",
                row["summary_en"] or "No summary.",
                "",
                "### Experimental Signals",
                _format_experimental(experimental),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _json_load(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _format_experimental(info: dict) -> str:
    if not info:
        return "No experimental details detected."
    ordered = [
        "biomass_type",
        "pretreatment_method",
        "acid_enzyme_type",
        "temperature",
        "reaction_time",
        "solid_liquid_ratio",
        "pH",
        "yield",
        "XOS_DP_distribution",
        "monosaccharide_composition",
        "HPLC_column",
        "mobile_phase",
        "flow_rate",
        "detector",
        "separation_method",
    ]
    lines = []
    for key in ordered:
        value = info.get(key)
        if value:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "No experimental details detected."
