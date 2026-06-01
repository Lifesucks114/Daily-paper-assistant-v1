from datetime import datetime, timezone
from typing import Any

import feedparser

from src.utils.text_cleaner import clean_text, normalize_doi, normalize_title


def _entry_date(entry: Any) -> str:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).date().isoformat()
    return ""


def _entry_doi(entry: Any) -> str | None:
    candidates = [
        getattr(entry, "dc_identifier", ""),
        getattr(entry, "prism_doi", ""),
        getattr(entry, "doi", ""),
        getattr(entry, "id", ""),
        getattr(entry, "link", ""),
    ]
    for value in candidates:
        value = clean_text(value)
        if "10." in value:
            doi = value[value.find("10.") :]
            return normalize_doi(doi)
    return None


def fetch_rss_papers(journals: list[dict[str, Any]], logger) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    for journal in journals:
        rss_url = journal.get("rss_url")
        if not rss_url:
            continue
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                logger.warning("RSS parsing warning for %s: %s", journal["name"], feed.bozo_exception)
            for entry in feed.entries:
                title = clean_text(getattr(entry, "title", ""))
                if not title:
                    continue
                papers.append(
                    {
                        "doi": _entry_doi(entry),
                        "normalized_title": normalize_title(title),
                        "title": title,
                        "abstract": clean_text(getattr(entry, "summary", "")),
                        "authors": clean_text(getattr(entry, "author", "")),
                        "journal": journal.get("name", ""),
                        "publisher": journal.get("publisher", ""),
                        "volume": clean_text(getattr(entry, "prism_volume", "") or getattr(entry, "volume", "")),
                        "issue": clean_text(
                            getattr(entry, "prism_number", "")
                            or getattr(entry, "prism_issue", "")
                            or getattr(entry, "issue", "")
                        ),
                        "published_date": _entry_date(entry),
                        "url": getattr(entry, "link", ""),
                        "pdf_url": "",
                        "license": "",
                        "source_feed": rss_url,
                    }
                )
            logger.info("Fetched %s entries from %s", len(feed.entries), journal["name"])
        except Exception:
            logger.exception("Failed to fetch RSS for %s", journal.get("name", rss_url))
    return papers
