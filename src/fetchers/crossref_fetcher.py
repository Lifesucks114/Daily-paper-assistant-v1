from typing import Any

import requests

from src.utils.text_cleaner import clean_text, normalize_doi


class CrossrefFetcher:
    def __init__(self, base_url: str, timeout_seconds: int, mailto: str | None, logger):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.mailto = mailto
        self.logger = logger

    def enrich(self, paper: dict[str, Any]) -> dict[str, Any]:
        try:
            item = self._fetch_by_doi(paper["doi"]) if paper.get("doi") else None
            if not item:
                item = self._fetch_by_title(paper["title"])
            if item:
                return self._merge(paper, item)
        except Exception:
            self.logger.exception("Crossref enrichment failed for %s", paper.get("title"))
        return paper

    def _fetch_by_doi(self, doi: str) -> dict[str, Any] | None:
        response = requests.get(
            f"{self.base_url}/{doi}",
            params=self._params(),
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("message")

    def _fetch_by_title(self, title: str) -> dict[str, Any] | None:
        params = self._params()
        params.update({"query.title": title, "rows": 1})
        response = requests.get(self.base_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        return items[0] if items else None

    def _params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def _merge(self, paper: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        enriched = paper.copy()
        enriched["doi"] = normalize_doi(item.get("DOI")) or paper.get("doi")
        enriched["abstract"] = clean_text(item.get("abstract")) or paper.get("abstract", "")
        enriched["authors"] = self._authors(item) or paper.get("authors", "")
        enriched["journal"] = self._first(item.get("container-title")) or paper.get("journal", "")
        enriched["publisher"] = item.get("publisher") or paper.get("publisher", "")
        enriched["volume"] = str(item.get("volume") or paper.get("volume", "") or "")
        enriched["issue"] = str(item.get("issue") or paper.get("issue", "") or "")
        enriched["published_date"] = self._published_date(item) or paper.get("published_date", "")
        enriched["url"] = item.get("URL") or paper.get("url", "")
        enriched["pdf_url"] = self._pdf_link(item) or paper.get("pdf_url", "")
        enriched["license"] = self._license(item) or paper.get("license", "")
        return enriched

    def _authors(self, item: dict[str, Any]) -> str:
        names = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = " ".join(part for part in [given, family] if part).strip()
            if name:
                names.append(name)
        return ", ".join(names)

    def _published_date(self, item: dict[str, Any]) -> str:
        for key in ("published-print", "published-online", "published", "created"):
            parts = item.get(key, {}).get("date-parts", [])
            if parts and parts[0]:
                year, month, day = (parts[0] + [1, 1])[:3]
                return f"{year:04d}-{month:02d}-{day:02d}"
        return ""

    def _license(self, item: dict[str, Any]) -> str:
        licenses = item.get("license", [])
        if licenses:
            return licenses[0].get("URL", "")
        return ""

    def _pdf_link(self, item: dict[str, Any]) -> str:
        for link in item.get("link", []):
            content_type = (link.get("content-type") or "").lower()
            url = link.get("URL", "")
            if "pdf" in content_type or url.lower().endswith(".pdf"):
                return url
        return ""

    def _first(self, value: Any) -> str:
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, str):
            return value
        return ""
