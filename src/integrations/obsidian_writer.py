import os
from pathlib import Path


def _normalize_windows_unc(path_value: str) -> str:
    """Repair UNC paths that dotenv/shell parsing reduced to a drive-root path."""
    if path_value.startswith("\\") and not path_value.startswith("\\\\"):
        parts = [part for part in path_value.split("\\") if part]
        if len(parts) >= 2 and "." in parts[0]:
            return "\\" + path_value
    return path_value


def write_report_to_obsidian(report_path: Path, report_type: str, settings: dict, logger) -> Path | None:
    enabled = os.getenv("OBSIDIAN_ENABLED", str(settings.get("enabled", False))).lower() == "true"
    vault = _normalize_windows_unc(os.getenv("OBSIDIAN_VAULT_PATH", ""))
    if not enabled or not vault:
        return None

    report_dir = os.getenv("OBSIDIAN_REPORT_DIR", settings.get("report_dir", "Literature/Daily Paper Assistant"))
    target_dir = Path(vault) / report_dir / report_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / report_path.name

    body = report_path.read_text(encoding="utf-8")
    title = report_path.stem
    content = (
        "---\n"
        f"title: {title}\n"
        f"type: {report_type}-paper-report\n"
        "tags:\n"
        "  - literature\n"
        "  - daily-paper-assistant\n"
        "---\n\n"
        f"[[Daily Paper Assistant]]\n\n{body}"
    )
    target.write_text(content, encoding="utf-8")
    logger.info("Obsidian report written to %s", target)
    return target
