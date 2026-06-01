import os
from typing import Any

import requests


def find_open_access_pdf(paper: dict[str, Any], logger) -> dict[str, str]:
    result = {
        "pdf_url": paper.get("pdf_url", "") or "",
        "license": paper.get("license", "") or "",
        "open_access_status": "unknown",
    }

    doi = paper.get("doi")
    email = os.getenv("UNPAYWALL_EMAIL") or os.getenv("CROSSREF_MAILTO")
    if doi and email:
        try:
            response = requests.get(
                f"https://api.unpaywall.org/v2/{doi}",
                params={"email": email},
                timeout=20,
            )
            if response.status_code == 404:
                result["open_access_status"] = "closed_or_not_found"
            else:
                response.raise_for_status()
                data = response.json()
                result["open_access_status"] = "open" if data.get("is_oa") else "closed"
                best = data.get("best_oa_location") or {}
                result["pdf_url"] = best.get("url_for_pdf") or result["pdf_url"]
                result["license"] = best.get("license") or result["license"]
                return result
        except Exception:
            logger.exception("Unpaywall lookup failed for %s", paper.get("title"))

    if result["pdf_url"] and result["license"]:
        result["open_access_status"] = "open"
    return result
