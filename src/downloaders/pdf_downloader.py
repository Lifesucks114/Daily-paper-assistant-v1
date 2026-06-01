from pathlib import Path
from typing import Any

import requests


def download_open_access_pdf(paper: dict[str, Any], pdf_dir: str, logger) -> str:
    """Minimal placeholder downloader.

    This version downloads only when metadata already exposes a direct PDF URL and
    an open license URL. It does not scrape publisher pages or bypass paywalls.
    """
    pdf_url = paper.get("pdf_url")
    license_url = paper.get("license")
    if not pdf_url or not license_url:
        return ""

    try:
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)
        doi_or_title = (paper.get("doi") or paper.get("normalized_title") or "paper").replace("/", "_")
        output = Path(pdf_dir) / f"{doi_or_title}.pdf"
        response = requests.get(
            pdf_url,
            timeout=30,
            headers={"User-Agent": "daily-paper-assistant/0.1 (mailto configured via env)"},
            allow_redirects=True,
        )
        if response.status_code in {401, 403, 404}:
            logger.warning(
                "Skipped PDF download for %s: HTTP %s",
                paper.get("title"),
                response.status_code,
            )
            return ""
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            logger.warning("Skipped non-PDF response for %s", paper.get("title"))
            return ""
        output.write_bytes(response.content)
        return str(output)
    except Exception:
        logger.exception("Failed to download OA PDF for %s", paper.get("title"))
        return ""
