import os
from datetime import date
from typing import Any

import requests
from requests import RequestException


class ZoteroClient:
    def __init__(self, settings: dict[str, Any], logger):
        self.enabled = os.getenv("ZOTERO_ENABLED", str(settings.get("enabled", False))).lower() == "true"
        self.base_url = os.getenv("ZOTERO_LOCAL_API", settings.get("local_api", "")).rstrip("/")
        self.logger = logger
        self.headers = {
            "Content-Type": "application/json",
            "Zotero-API-Version": "3",
        }
        self.available: bool | None = None

    def import_paper(self, paper: dict[str, Any], pdf_path: str, run_date: date) -> dict[str, str]:
        if not self.enabled:
            return {}
        if not self.is_available():
            return {}
        try:
            collection_key, collection_name = self._ensure_collection(run_date.isoformat())
            item_key = self._create_item(paper, collection_key)
            if pdf_path:
                self._attach_pdf(item_key, pdf_path)
            return {"zotero_collection": collection_name, "zotero_item_key": item_key}
        except RequestException as exc:
            self.logger.warning("Zotero import skipped for %s: %s", paper.get("title"), exc)
            self.available = False
            return {}
        except Exception:
            self.logger.exception("Zotero import failed for %s", paper.get("title"))
            return {}

    def is_available(self) -> bool:
        if self.available is not None:
            return self.available
        try:
            response = requests.get(
                f"{self.base_url}/collections",
                params={"limit": 1},
                headers={"Zotero-API-Version": "3"},
                timeout=3,
            )
            response.raise_for_status()
            self.available = True
        except RequestException as exc:
            self.logger.warning("Zotero local API unavailable; Zotero sync disabled for this run: %s", exc)
            self.available = False
        return self.available

    def _ensure_collection(self, name: str) -> tuple[str, str]:
        response = requests.get(
            f"{self.base_url}/collections",
            params={"limit": 100},
            headers={"Zotero-API-Version": "3"},
            timeout=10,
        )
        response.raise_for_status()
        for collection in response.json():
            if collection.get("data", {}).get("name") == name:
                return collection["key"], name

        response = requests.post(
            f"{self.base_url}/collections",
            json=[{"name": name, "parentCollection": False}],
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        key = next(iter(response.json().get("successful", {}).values()))["key"]
        return key, name

    def _create_item(self, paper: dict[str, Any], collection_key: str) -> str:
        creators = []
        for author in (paper.get("authors") or "").split(","):
            author = author.strip()
            if author:
                creators.append({"creatorType": "author", "name": author})
        item = {
            "itemType": "journalArticle",
            "title": paper.get("title", ""),
            "creators": creators,
            "publicationTitle": paper.get("journal", ""),
            "date": paper.get("published_date", ""),
            "DOI": paper.get("doi", ""),
            "url": paper.get("url", ""),
            "abstractNote": paper.get("abstract", ""),
            "collections": [collection_key],
            "tags": [{"tag": "daily-paper-assistant"}],
        }
        response = requests.post(
            f"{self.base_url}/items",
            json=[item],
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        return next(iter(response.json().get("successful", {}).values()))["key"]

    def _attach_pdf(self, parent_key: str, pdf_path: str) -> None:
        attachment = {
            "itemType": "attachment",
            "parentItem": parent_key,
            "linkMode": "imported_file",
            "title": "Full Text PDF",
            "path": pdf_path,
            "contentType": "application/pdf",
        }
        response = requests.post(
            f"{self.base_url}/items",
            json=[attachment],
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
