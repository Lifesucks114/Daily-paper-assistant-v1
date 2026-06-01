from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(pdf_path: str, max_pages: int, max_chars: int, logger) -> tuple[str, str]:
    if not pdf_path:
        return "", "not_downloaded"
    try:
        reader = PdfReader(pdf_path)
        chunks = []
        for page in reader.pages[:max_pages]:
            chunks.append(page.extract_text() or "")
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
        text = "\n".join(chunks).strip()[:max_chars]
        return text, "parsed" if text else "empty_text"
    except Exception:
        logger.exception("Failed to parse PDF text from %s", Path(pdf_path).name)
        return "", "parse_failed"
