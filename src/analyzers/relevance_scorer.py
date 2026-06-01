from typing import Any

from src.filters.relevance_filter import simple_relevance_score


def score_relevance(paper: dict[str, Any], matched_keywords: list[str]) -> float:
    return simple_relevance_score(paper, matched_keywords)
