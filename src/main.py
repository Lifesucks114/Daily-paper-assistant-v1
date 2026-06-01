import argparse
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.analyzers.data_extraction_advisor import infer_experimental_info
from src.analyzers.pdf_parser import extract_pdf_text
from src.analyzers.relevance_scorer import score_relevance
from src.analyzers.summarizer import OpenAISummarizer
from src.downloaders.open_access_finder import find_open_access_pdf
from src.downloaders.pdf_downloader import download_open_access_pdf
from src.fetchers.crossref_fetcher import CrossrefFetcher
from src.fetchers.rss_fetcher import fetch_rss_papers
from src.filters.keyword_filter import keyword_match
from src.filters.relevance_filter import is_xos_production_scope
from src.integrations.obsidian_writer import write_report_to_obsidian
from src.reports.daily_report import generate_daily_report
from src.reports.weekly_report import generate_weekly_report
from src.utils.database import PaperDatabase
from src.utils.logger import setup_logger
from src.utils.text_cleaner import normalize_title


def load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def row_to_paper(row) -> dict[str, Any]:
    return {
        "doi": row["doi"],
        "normalized_title": row["normalized_title"],
        "title": row["title"],
        "abstract": row["abstract"] or "",
        "authors": row["authors"] or "",
        "journal": row["journal"] or "",
        "publisher": row["publisher"] or "",
        "volume": row["volume"] or "",
        "issue": row["issue"] or "",
        "published_date": row["published_date"] or "",
        "url": row["url"] or "",
        "pdf_url": row["pdf_url"] or "",
        "license": row["license"] or "",
        "open_access_status": row["open_access_status"] or "",
    }


def parse_volume_number(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def select_active_volume_candidates(
    enriched_candidates: list[dict[str, Any]],
    db: PaperDatabase,
    now: str,
    max_total: int,
    logger,
) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for paper in enriched_candidates:
        by_source.setdefault(paper.get("source_feed", "unknown"), []).append(paper)

    selected: list[dict[str, Any]] = []
    for papers in by_source.values():
        volume_numbers = [
            parse_volume_number(paper.get("volume"))
            for paper in papers
            if parse_volume_number(paper.get("volume")) is not None
        ]
        if not volume_numbers:
            logger.info(
                "No volume found for %s; selecting all RSS entries for this journal",
                papers[0].get("journal", "unknown"),
            )
            selected.extend(papers)
            continue

        current_volume_number = max(volume_numbers)
        current_volume = str(current_volume_number)
        current_issue = next((paper.get("issue", "") for paper in papers if parse_volume_number(paper.get("volume")) == current_volume_number), "")
        baseline = db.get_or_create_journal_baseline(
            papers[0].get("source_feed", "unknown"),
            papers[0].get("journal", "unknown"),
            current_volume,
            current_issue,
            now,
        )
        baseline_number = parse_volume_number(baseline["baseline_volume"]) or current_volume_number
        active_papers = [
            paper
            for paper in papers
            if (parse_volume_number(paper.get("volume")) or -1) >= baseline_number
        ]
        logger.info(
            "Selected active volumes for %s: baseline %s, current %s, %s papers",
            papers[0].get("journal", "unknown"),
            baseline["baseline_volume"],
            current_volume,
            len(active_papers),
        )
        selected.extend(active_papers)
        if len(selected) >= max_total:
            break
    return selected[:max_total]


def run_daily(settings: dict[str, Any], journals: dict[str, Any], keywords: dict[str, Any], logger) -> Path:
    db = PaperDatabase(settings["paths"]["database"])
    today = date.today()
    now = datetime.now().isoformat(timespec="seconds")
    min_keyword_score = int(settings["app"].get("min_keyword_score", 1))
    min_relevance_score = float(settings["app"].get("min_relevance_score", 2))
    max_papers = int(settings["app"].get("max_papers_per_run", 100))
    max_openai_summaries = int(settings["app"].get("max_openai_summaries_per_run", 3))
    max_openai_screening_candidates = int(settings["app"].get("max_openai_screening_candidates", max_openai_summaries))
    openai_summaries_used = 0

    crossref = CrossrefFetcher(
        base_url=settings["crossref"]["base_url"],
        timeout_seconds=int(settings["crossref"].get("timeout_seconds", 20)),
        mailto=os.getenv("CROSSREF_MAILTO"),
        logger=logger,
    )
    summarizer = OpenAISummarizer(
        model=settings["openai"]["model"],
        temperature=float(settings["openai"].get("temperature", 0.2)),
        max_output_tokens=int(settings["openai"].get("max_output_tokens", 1200)),
        logger=logger,
    )
    fetched_candidates = fetch_rss_papers(journals.get("journals", []), logger)
    enriched_candidates = []
    for paper in fetched_candidates:
        paper["normalized_title"] = normalize_title(paper["title"])
        paper["first_seen"] = now
        paper["last_seen"] = now
        enriched_candidates.append(crossref.enrich(paper))
    candidates = select_active_volume_candidates(enriched_candidates, db, now, max_papers, logger)
    logger.info("Processing %s candidate papers", len(candidates))

    for enriched in candidates:
        paper_id, is_new = db.upsert_paper(enriched)

        match = keyword_match(enriched, keywords)
        relevance = score_relevance(enriched, match["matched_keywords"]) if match["is_match"] else 0
        is_candidate = match["keyword_score"] >= min_keyword_score and relevance >= min_relevance_score
        in_scope = is_xos_production_scope(enriched)
        status = "candidate" if is_candidate and in_scope else "irrelevant"
        is_candidate = is_candidate and in_scope
        can_ai_screen = (
            is_candidate
            and openai_summaries_used < min(max_openai_summaries, max_openai_screening_candidates)
        )

        if not is_new and not is_candidate:
            logger.info("Skipping already-seen non-relevant paper: %s", enriched["title"])
            continue

        pdf_path = ""
        pdf_text = ""
        pdf_parse_status = "not_relevant"
        if can_ai_screen and settings.get("pdf", {}).get("enabled", True):
            oa = find_open_access_pdf(enriched, logger)
            enriched.update({key: value for key, value in oa.items() if value})
            pdf_path = download_open_access_pdf(enriched, settings["paths"]["pdfs"], logger)
            pdf_text, pdf_parse_status = extract_pdf_text(
                pdf_path,
                int(settings.get("pdf", {}).get("max_pdf_pages", 8)),
                int(settings.get("pdf", {}).get("max_pdf_chars_for_openai", 20000)),
                logger,
            )

        experimental = infer_experimental_info({**enriched, "abstract": f"{enriched.get('abstract', '')} {pdf_text[:4000]}"})
        summaries = {"summary_zh": "", "summary_en": ""}
        reason_for_relevance = "Heuristic keyword score only."
        data_worth_extracting = ""
        if is_candidate:
            if can_ai_screen:
                logger.info(
                    "OpenAI screening candidate %s/%s: %s",
                    openai_summaries_used + 1,
                    min(max_openai_summaries, max_openai_screening_candidates),
                    enriched["title"],
                )
                summaries = summarizer.summarize(enriched, relevance, experimental, pdf_text)
                openai_summaries_used += 1
                relevance = float(summaries.get("relevance_score", relevance))
                experimental = summaries.get("experimental_info", experimental)
                reason_for_relevance = summaries.get("reason_for_relevance", reason_for_relevance)
                data_worth_extracting = summaries.get("data_worth_extracting", "")
                in_scope_after_ai = is_xos_production_scope(
                    {**enriched, "reason_for_relevance": summaries.get("reason_for_relevance", "")}
                )
                status = (
                    "relevant"
                    if relevance >= float(settings["app"].get("min_ai_relevance_score", 2.0)) and in_scope_after_ai
                    else "irrelevant"
                )
            else:
                summaries = {
                    "summary_zh": "已达到本次运行的 OpenAI 摘要数量上限，未生成摘要。",
                    "summary_en": "OpenAI summary limit reached for this run; summary was skipped.",
                }
                reason_for_relevance = "Relevant by keyword heuristic; OpenAI summary limit reached."
                status = "relevant" if relevance >= min_relevance_score and in_scope else "irrelevant"

        db.update_analysis(
            paper_id,
            {
                "keyword_score": match["keyword_score"],
                "relevance_score": relevance,
                "matched_keywords": match["matched_keywords"],
                "summary_zh": summaries["summary_zh"],
                "summary_en": summaries["summary_en"],
                "experimental_info": experimental,
                "reason_for_relevance": reason_for_relevance,
                "data_worth_extracting": data_worth_extracting,
                "pdf_path": pdf_path,
                "pdf_downloaded": 1 if pdf_path else 0,
                "pdf_parse_status": pdf_parse_status,
                "open_access_status": enriched.get("open_access_status", ""),
                "zotero_collection": "",
                "zotero_item_key": "",
                "processed_time": datetime.now().isoformat(timespec="seconds"),
                "status": status,
            },
        )
        logger.info("Stored paper [%s]: %s", status, enriched["title"])

    rows = db.get_papers_seen_on(today.isoformat(), relevant_only=True)
    remaining_openai_budget = max_openai_summaries - openai_summaries_used
    if remaining_openai_budget > 0 and os.getenv("OPENAI_API_KEY"):
        pending_rows = db.get_relevant_papers_needing_summary(today.isoformat(), remaining_openai_budget)
        logger.info("OpenAI backfill candidates for today's relevant papers: %s", len(pending_rows))
        for row in pending_rows:
            paper = row_to_paper(row)
            pdf_path = row["pdf_path"] or ""
            pdf_text, pdf_parse_status = extract_pdf_text(
                pdf_path,
                int(settings.get("pdf", {}).get("max_pdf_pages", 8)),
                int(settings.get("pdf", {}).get("max_pdf_chars_for_openai", 20000)),
                logger,
            )
            experimental = infer_experimental_info({**paper, "abstract": f"{paper.get('abstract', '')} {pdf_text[:4000]}"})
            summaries = summarizer.summarize(paper, float(row["relevance_score"] or 0), experimental, pdf_text)
            db.update_analysis(
                int(row["id"]),
                {
                    "keyword_score": row["keyword_score"] or 0,
                    "relevance_score": float(summaries.get("relevance_score", row["relevance_score"] or 0)),
                    "matched_keywords": [],
                    "summary_zh": summaries["summary_zh"],
                    "summary_en": summaries["summary_en"],
                    "experimental_info": summaries.get("experimental_info", experimental),
                    "reason_for_relevance": summaries.get("reason_for_relevance", ""),
                    "data_worth_extracting": summaries.get("data_worth_extracting", ""),
                    "pdf_path": pdf_path,
                    "pdf_downloaded": row["pdf_downloaded"],
                    "pdf_parse_status": pdf_parse_status,
                    "open_access_status": row["open_access_status"] or "",
                    "zotero_collection": row["zotero_collection"] or "",
                    "zotero_item_key": row["zotero_item_key"] or "",
                    "processed_time": datetime.now().isoformat(timespec="seconds"),
                    "status": "relevant",
                },
            )
            logger.info("OpenAI backfilled summary for: %s", paper["title"])
        rows = db.get_papers_seen_on(today.isoformat(), relevant_only=True)
    report_path = generate_daily_report(rows, settings["paths"]["daily_reports"], today)
    write_report_to_obsidian(report_path, "daily", settings.get("obsidian", {}), logger)
    db.close()
    logger.info("Daily report written to %s", report_path)
    return report_path


def run_weekly(settings: dict[str, Any], logger) -> Path:
    db = PaperDatabase(settings["paths"]["database"])
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=7)
    rows = db.get_papers_between(start.isoformat(), end.isoformat())
    report_path = generate_weekly_report(rows, settings["paths"]["weekly_reports"], today)
    write_report_to_obsidian(report_path, "weekly", settings.get("obsidian", {}), logger)
    db.close()
    logger.info("Weekly report written to %s", report_path)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily literature assistant for biomass/XOS research.")
    parser.add_argument("--mode", choices=["daily", "weekly", "all"], default="daily")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    load_dotenv(project_root / ".env")
    logger = setup_logger()
    logger.info("OpenAI API key loaded: %s", "yes" if os.getenv("OPENAI_API_KEY") else "no")
    settings = load_yaml("config/settings.yaml")
    journals = load_yaml("config/journals.yaml")
    keywords = load_yaml("config/keywords.yaml")

    if args.mode in ("daily", "all"):
        run_daily(settings, journals, keywords, logger)
    if args.mode in ("weekly", "all"):
        run_weekly(settings, logger)


if __name__ == "__main__":
    main()
