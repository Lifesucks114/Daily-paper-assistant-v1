import json
import sqlite3
from pathlib import Path
from typing import Any


class PaperDatabase:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT UNIQUE,
                normalized_title TEXT NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,
                journal TEXT,
                publisher TEXT,
                volume TEXT,
                issue TEXT,
                published_date TEXT,
                publication_date TEXT,
                url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,
                pdf_downloaded INTEGER DEFAULT 0,
                pdf_parse_status TEXT,
                open_access_status TEXT,
                license TEXT,
                source_feed TEXT,
                keyword_score INTEGER DEFAULT 0,
                keywords TEXT,
                relevance_score REAL DEFAULT 0,
                matched_keywords TEXT,
                summary_zh TEXT,
                summary_cn TEXT,
                summary_en TEXT,
                experimental_info TEXT,
                experimental_conditions TEXT,
                reason_for_relevance TEXT,
                data_worth_extracting TEXT,
                zotero_collection TEXT,
                zotero_item_key TEXT,
                processed_time TEXT,
                status TEXT DEFAULT 'seen',
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                UNIQUE(normalized_title)
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_baselines (
                source_feed TEXT PRIMARY KEY,
                journal TEXT NOT NULL,
                baseline_volume TEXT,
                baseline_issue TEXT,
                initialized_at TEXT NOT NULL,
                last_seen_volume TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._migrate_schema()
        self.conn.commit()

    def _migrate_schema(self) -> None:
        existing = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(papers)").fetchall()
        }
        columns = {
            "pdf_path": "TEXT",
            "pdf_downloaded": "INTEGER DEFAULT 0",
            "pdf_parse_status": "TEXT",
            "open_access_status": "TEXT",
            "publication_date": "TEXT",
            "volume": "TEXT",
            "issue": "TEXT",
            "keywords": "TEXT",
            "summary_cn": "TEXT",
            "experimental_conditions": "TEXT",
            "reason_for_relevance": "TEXT",
            "data_worth_extracting": "TEXT",
            "zotero_collection": "TEXT",
            "zotero_item_key": "TEXT",
            "processed_time": "TEXT",
        }
        for name, ddl in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE papers ADD COLUMN {name} {ddl}")

    def upsert_paper(self, paper: dict[str, Any]) -> tuple[int, bool]:
        existing = self.find_existing(paper.get("doi"), paper["normalized_title"])
        payload = paper.copy()
        for key in ("authors", "matched_keywords", "experimental_info"):
            if isinstance(payload.get(key), (list, dict)):
                payload[key] = json.dumps(payload[key], ensure_ascii=False)

        if existing:
            paper_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE papers SET
                    doi = COALESCE(?, doi),
                    abstract = COALESCE(NULLIF(?, ''), abstract),
                    authors = COALESCE(NULLIF(?, ''), authors),
                    journal = COALESCE(NULLIF(?, ''), journal),
                    publisher = COALESCE(NULLIF(?, ''), publisher),
                    volume = COALESCE(NULLIF(?, ''), volume),
                    issue = COALESCE(NULLIF(?, ''), issue),
                    published_date = COALESCE(NULLIF(?, ''), published_date),
                    publication_date = COALESCE(NULLIF(?, ''), publication_date),
                    url = COALESCE(NULLIF(?, ''), url),
                    pdf_url = COALESCE(NULLIF(?, ''), pdf_url),
                    pdf_path = COALESCE(NULLIF(?, ''), pdf_path),
                    pdf_downloaded = COALESCE(?, pdf_downloaded),
                    open_access_status = COALESCE(NULLIF(?, ''), open_access_status),
                    license = COALESCE(NULLIF(?, ''), license),
                    source_feed = COALESCE(NULLIF(?, ''), source_feed),
                    last_seen = ?
                WHERE id = ?
                """,
                (
                    payload.get("doi"),
                    payload.get("abstract", ""),
                    payload.get("authors", ""),
                    payload.get("journal", ""),
                    payload.get("publisher", ""),
                    payload.get("volume", ""),
                    payload.get("issue", ""),
                    payload.get("published_date", ""),
                    payload.get("publication_date", payload.get("published_date", "")),
                    payload.get("url", ""),
                    payload.get("pdf_url", ""),
                    payload.get("pdf_path", ""),
                    payload.get("pdf_downloaded"),
                    payload.get("open_access_status", ""),
                    payload.get("license", ""),
                    payload.get("source_feed", ""),
                    payload["last_seen"],
                    paper_id,
                ),
            )
            self.conn.commit()
            return paper_id, False

        cursor = self.conn.execute(
            """
            INSERT INTO papers (
                doi, normalized_title, title, abstract, authors, journal, publisher,
                volume, issue, published_date, publication_date, url, pdf_url, pdf_path, pdf_downloaded, open_access_status,
                license, source_feed, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("doi"),
                payload["normalized_title"],
                payload["title"],
                payload.get("abstract", ""),
                payload.get("authors", ""),
                payload.get("journal", ""),
                payload.get("publisher", ""),
                payload.get("volume", ""),
                payload.get("issue", ""),
                payload.get("published_date", ""),
                payload.get("publication_date", payload.get("published_date", "")),
                payload.get("url", ""),
                payload.get("pdf_url", ""),
                payload.get("pdf_path", ""),
                payload.get("pdf_downloaded", 0),
                payload.get("open_access_status", ""),
                payload.get("license", ""),
                payload.get("source_feed", ""),
                payload["first_seen"],
                payload["last_seen"],
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid), True

    def get_or_create_journal_baseline(
        self,
        source_feed: str,
        journal: str,
        current_volume: str,
        current_issue: str,
        now: str,
    ) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM journal_baselines WHERE source_feed = ?",
            (source_feed,),
        ).fetchone()
        if row:
            self.conn.execute(
                """
                UPDATE journal_baselines
                SET journal = ?, last_seen_volume = ?, updated_at = ?
                WHERE source_feed = ?
                """,
                (journal, current_volume, now, source_feed),
            )
            self.conn.commit()
            return self.conn.execute(
                "SELECT * FROM journal_baselines WHERE source_feed = ?",
                (source_feed,),
            ).fetchone()

        self.conn.execute(
            """
            INSERT INTO journal_baselines (
                source_feed, journal, baseline_volume, baseline_issue,
                initialized_at, last_seen_volume, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_feed, journal, current_volume, current_issue, now, current_volume, now),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM journal_baselines WHERE source_feed = ?",
            (source_feed,),
        ).fetchone()

    def find_existing(self, doi: str | None, normalized_title: str) -> sqlite3.Row | None:
        if doi:
            row = self.conn.execute("SELECT * FROM papers WHERE doi = ?", (doi,)).fetchone()
            if row:
                return row
        return self.conn.execute(
            "SELECT * FROM papers WHERE normalized_title = ?", (normalized_title,)
        ).fetchone()

    def update_analysis(self, paper_id: int, analysis: dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE papers SET
                keyword_score = ?,
                keywords = ?,
                relevance_score = ?,
                matched_keywords = ?,
                summary_zh = ?,
                summary_cn = ?,
                summary_en = ?,
                experimental_info = ?,
                experimental_conditions = ?,
                reason_for_relevance = ?,
                data_worth_extracting = ?,
                pdf_path = COALESCE(NULLIF(?, ''), pdf_path),
                pdf_downloaded = COALESCE(?, pdf_downloaded),
                pdf_parse_status = COALESCE(NULLIF(?, ''), pdf_parse_status),
                open_access_status = COALESCE(NULLIF(?, ''), open_access_status),
                zotero_collection = COALESCE(NULLIF(?, ''), zotero_collection),
                zotero_item_key = COALESCE(NULLIF(?, ''), zotero_item_key),
                processed_time = ?,
                status = ?
            WHERE id = ?
            """,
            (
                analysis.get("keyword_score", 0),
                json.dumps(analysis.get("matched_keywords", []), ensure_ascii=False),
                analysis.get("relevance_score", 0),
                json.dumps(analysis.get("matched_keywords", []), ensure_ascii=False),
                analysis.get("summary_zh", ""),
                analysis.get("summary_zh", ""),
                analysis.get("summary_en", ""),
                json.dumps(analysis.get("experimental_info", {}), ensure_ascii=False),
                json.dumps(analysis.get("experimental_info", {}), ensure_ascii=False),
                analysis.get("reason_for_relevance", ""),
                analysis.get("data_worth_extracting", ""),
                analysis.get("pdf_path", ""),
                analysis.get("pdf_downloaded"),
                analysis.get("pdf_parse_status", ""),
                analysis.get("open_access_status", ""),
                analysis.get("zotero_collection", ""),
                analysis.get("zotero_item_key", ""),
                analysis.get("processed_time", ""),
                analysis.get("status", "seen"),
                paper_id,
            ),
        )
        self.conn.commit()

    def get_papers_seen_on(self, date_prefix: str, relevant_only: bool = True) -> list[sqlite3.Row]:
        sql = "SELECT * FROM papers WHERE first_seen LIKE ?"
        params: list[Any] = [f"{date_prefix}%"]
        if relevant_only:
            sql += " AND status = 'relevant'"
        sql += " ORDER BY relevance_score DESC, published_date DESC"
        return list(self.conn.execute(sql, params).fetchall())

    def get_relevant_papers_needing_summary(self, date_prefix: str, limit: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM papers
                WHERE first_seen LIKE ?
                  AND status = 'relevant'
                  AND (
                    summary_zh IS NULL
                    OR summary_zh = ''
                    OR summary_zh LIKE '未设置 OPENAI_API_KEY%'
                    OR summary_zh LIKE '已达到本次运行的 OpenAI%'
                    OR reason_for_relevance IS NULL
                    OR reason_for_relevance = ''
                    OR reason_for_relevance = 'Heuristic keyword score only.'
                  )
                ORDER BY relevance_score DESC, published_date DESC
                LIMIT ?
                """,
                (f"{date_prefix}%", limit),
            ).fetchall()
        )

    def get_papers_between(self, start_date: str, end_date: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT * FROM papers
                WHERE first_seen >= ? AND first_seen < ? AND status = 'relevant'
                ORDER BY relevance_score DESC, published_date DESC
                """,
                (start_date, end_date),
            ).fetchall()
        )

    def close(self) -> None:
        self.conn.close()
