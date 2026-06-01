from typing import Any


def flatten_keywords(config: dict[str, list[str]]) -> list[str]:
    keywords: list[str] = []
    for group, values in config.items():
        if group == "exclude_keywords":
            continue
        keywords.extend(values or [])
    return keywords


def keyword_match(paper: dict[str, Any], keyword_config: dict[str, list[str]]) -> dict[str, Any]:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    matched = []
    for keyword in flatten_keywords(keyword_config):
        if keyword.lower() in text:
            matched.append(keyword)

    excluded = [
        keyword
        for keyword in keyword_config.get("exclude_keywords", [])
        if keyword.lower() in text
    ]
    score = len(set(matched))
    return {
        "is_match": score > 0 and not excluded,
        "keyword_score": score,
        "matched_keywords": sorted(set(matched)),
        "excluded_keywords": sorted(set(excluded)),
    }
