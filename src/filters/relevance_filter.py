from typing import Any


def is_in_research_scope(
    paper: dict[str, Any],
    required_terms: list[str] | None = None,
    excluded_terms: list[str] | None = None,
) -> bool:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')} {paper.get('reason_for_relevance', '')}".lower()
    required = [term.lower() for term in (required_terms or [])]
    excluded = [term.lower() for term in (excluded_terms or [])]
    has_required = True if not required else any(term in text for term in required)
    has_excluded = any(term in text for term in excluded)
    return has_required and not has_excluded


def simple_relevance_score(paper: dict[str, Any], matched_keywords: list[str]) -> float:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    score = min(5.0, len(set(matched_keywords)) * 0.7)
    title = paper.get("title", "").lower()
    for term in set(keyword.lower() for keyword in matched_keywords):
        if term in text:
            score += 0.2
        if term in title:
            score += 0.4

    return round(min(5.0, score), 1)
